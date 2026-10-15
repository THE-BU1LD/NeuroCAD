"""Fault injection verifies accounting, not CAD performance."""
import json

import pytest

from core.evaluation_ledger import run_scheduled_evaluation

IDENTITIES = {"source_commit": "1" * 40, "dataset_revision": "2" * 40,
              "dataset_manifest_sha256": "3" * 64, "protocol_sha256": "4" * 64}
METRICS = {"passed": True, "requirements_passed": 2, "requirements_total": 2}


def run(path, load=lambda value: value, execute=lambda value: METRICS, ids=("one", "two")):
    return run_scheduled_evaluation(ids, path, identities=IDENTITIES, load=load, execute=execute)


def test_schedule_precedes_loading_and_normal_control(tmp_path):
    path = tmp_path / "run"
    def load(identifier):
        assert json.loads((path / "manifest.json").read_text(encoding="utf-8"))["scheduled_ids"] == ["one", "two"]
        return identifier
    result = run(path, load=load)
    assert result["valid_for_inference"]
    assert result["correct_completion_numerator"] == result["correct_completion_denominator"] == 2
    assert len(result["outcomes"]) == 2
    with pytest.raises(FileExistsError):
        run(path)


def test_load_failure_never_changes_denominator(tmp_path):
    def load(identifier):
        if identifier == "one":
            raise ValueError("missing")
        return identifier
    result = run(tmp_path / "run", load=load)
    assert result["correct_completion_numerator"] == 1
    assert result["correct_completion_denominator"] == 2
    assert [r["status"] for r in result["outcomes"]] == ["load_error", "evaluated"]
    assert not result["valid_for_inference"]


def test_persistence_error_has_one_terminal_record_and_retained_summary(tmp_path, monkeypatch):
    import core.evaluation_ledger as module
    original = module._write
    def broken(path, value):
        if path.name == "one.json":
            raise OSError("disk error")
        return original(path, value)
    monkeypatch.setattr(module, "_write", broken)
    result = run(tmp_path / "run")
    assert [r["id"] for r in result["outcomes"]] == ["one", "two"]
    assert not result["outcomes"][0]["persisted"]
    assert result["status"] == "INCOMPLETE_OR_ERROR"
    assert not result["valid_for_inference"]
    assert (tmp_path / "run" / "summary.json").exists()


@pytest.mark.parametrize("metrics", [None, {}, {**METRICS, "passed": 1},
    {**METRICS, "requirements_passed": 3}, {**METRICS, "requirements_total": 0},
    {"passed": False, "requirements_passed": 0, "requirements_total": 0}])
def test_unavailable_or_invalid_endpoints_visible(tmp_path, metrics):
    result = run(tmp_path / "run", execute=lambda value: metrics)
    assert not result["valid_for_inference"]
    assert result["correct_completion_denominator"] == 2
    assert result["requirement_unavailable_samples"] == 2


def test_timeout_duplicate_and_unsafe_ids(tmp_path):
    def execute(value):
        raise TimeoutError()
    result = run(tmp_path / "timeout", execute=execute)
    assert all(r["status"] == "execution_error" for r in result["outcomes"])
    for ids in [("same", "same"), ("../escape",), ()]:
        with pytest.raises(ValueError):
            run(tmp_path / "bad", ids=ids)
    assert not (tmp_path / "bad").exists()
