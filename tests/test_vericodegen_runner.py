import json
from pathlib import Path

import trimesh

from research.vericodegen.runner import GenerationAttempt, append_jsonl, run_trial


ROOT = Path(__file__).resolve().parents[1]


def _box_artifact(tmp_path: Path, name: str, extents=(2.0, 4.0, 6.0)) -> Path:
    path = tmp_path / f"{name}.stl"
    trimesh.creation.box(extents=extents).export(path)
    return path


def _task(**constraints):
    return {
        "prompt_id": "VCG-999",
        "prompt_text": "development fixture",
        "hard_constraints": constraints,
    }


def test_successful_trial_records_artifact_hash_and_provenance(tmp_path):
    artifact = _box_artifact(tmp_path, "passing")

    def generator(task, arm, retry_index):
        assert arm == "structured"
        assert retry_index == 0
        return GenerationAttempt(
            compiled=True,
            artifact_path=artifact,
            raw_response='{"shape":"box"}',
            generated_tokens=12,
            latency_s=0.25,
            estimated_cost_usd=0.0,
        )

    result = run_trial(
        _task(
            watertight=True,
            max_components=1,
            volume={"min": 47.9, "max": 48.1},
            extents={"x": {"min": 1.99, "max": 2.01}},
        ),
        arm="structured",
        generator=generator,
        max_attempts=2,
        seed=7,
        provider="fixture-provider",
        model="fixture-model-v1",
        benchmark_manifest_sha256="abc123",
        git_commit="deadbeef",
        prompt_template_sha256="def456",
        verifier_version="fixture-verifier",
    )

    assert result.hvr is True
    assert result.attempts_used == 1
    assert result.attempts[0].compiled is True
    assert result.attempts[0].verifier_passed is True
    assert len(result.attempts[0].artifact_sha256) == 64
    assert result.provenance["provider"] == "fixture-provider"
    assert result.provenance["model"] == "fixture-model-v1"
    assert result.provenance["max_attempts"] == 2


def test_same_retry_budget_retains_failed_attempt_before_success(tmp_path):
    artifact = _box_artifact(tmp_path, "retry-passing")

    def generator(task, arm, retry_index):
        if retry_index == 0:
            return GenerationAttempt(
                compiled=False,
                raw_response="invalid source",
                error="compiler rejected source",
            )
        return GenerationAttempt(compiled=True, artifact_path=artifact, raw_response="fixed")

    result = run_trial(
        _task(watertight=True, max_components=1),
        arm="direct",
        generator=generator,
        max_attempts=2,
    )

    assert result.hvr is True
    assert result.attempts_used == 2
    assert result.attempts[0].hvr is False
    assert "syntax/compile failure" in result.attempts[0].failure_taxonomy
    assert result.attempts[1].hvr is True


def test_shared_verifier_failure_is_not_misreported_as_compile_failure(tmp_path):
    artifact = _box_artifact(tmp_path, "wrong-size", extents=(1.0, 1.0, 1.0))

    def generator(task, arm, retry_index):
        return GenerationAttempt(compiled=True, artifact_path=artifact)

    result = run_trial(
        _task(extents={"x": {"min": 2.0}}),
        arm="structured",
        generator=generator,
        max_attempts=1,
    )

    attempt = result.attempts[0]
    assert result.hvr is False
    assert attempt.compiled is True
    assert attempt.verifier_passed is False
    assert "wrong dimension/unit" in attempt.failure_taxonomy
    assert "syntax/compile failure" not in attempt.failure_taxonomy
    assert "timeout/retry exhaustion" in attempt.failure_taxonomy


def test_compiled_attempt_without_final_artifact_fails_closed():
    def generator(task, arm, retry_index):
        return GenerationAttempt(compiled=True, artifact_path=None)

    result = run_trial(
        _task(watertight=True),
        arm="direct",
        generator=generator,
        max_attempts=1,
    )

    assert result.hvr is False
    assert result.attempts[0].verifier_passed is False
    assert any("did not provide" in item for item in result.attempts[0].failures)


def test_jsonl_writer_retains_attempt_level_record(tmp_path):
    artifact = _box_artifact(tmp_path, "jsonl")

    def generator(task, arm, retry_index):
        return GenerationAttempt(compiled=True, artifact_path=artifact, raw_response="raw")

    result = run_trial(
        _task(watertight=True),
        arm="direct",
        generator=generator,
        max_attempts=1,
    )
    path = tmp_path / "records" / "smoke.jsonl"
    append_jsonl(path, result)

    payload = json.loads(path.read_text(encoding="utf-8").strip())
    assert payload["prompt_id"] == "VCG-999"
    assert payload["attempts"][0]["raw_response"] == "raw"
    assert payload["attempts"][0]["artifact_sha256"]


def test_development_tasks_are_explicitly_non_primary_and_family_balanced():
    tasks = json.loads(
        (ROOT / "research" / "vericodegen" / "development_tasks.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(tasks) == 6
    assert len({task["prompt_id"] for task in tasks}) == 6
    families = [task["task_family"] for task in tasks]
    assert families.count("in_distribution") == 2
    assert families.count("compositional") == 2
    assert families.count("ood_constraint_stress") == 2
    assert all("DEVELOPMENT ONLY" in task["notes"] for task in tasks)
