from __future__ import annotations

import hashlib
import json
import subprocess

import pytest

from scripts.evaluate_c3d_revision import EXAMPLES, command, evaluate, read_json, rejection_matches


def test_frozen_suite_has_distinct_valid_and_adversarial_cases() -> None:
    manifest = read_json(EXAMPLES / "evaluation-v1.json")
    assert manifest["version"] == "neurocad-c3d-evaluation-v1"
    assert len(manifest["cases"]) == 17
    assert len({case["id"] for case in manifest["cases"]}) == 17
    assert sum(case["expected_accept"] for case in manifest["cases"]) == 5
    assert {"change_frozen_requirement", "stale_binding", "thin_wall_hole_overlap",
            "negative_cavity", "move_cutout", "remove_cutout"} <= {case["id"] for case in manifest["cases"]}
    assert all(case["error_tokens"] for case in manifest["cases"] if not case["expected_accept"])


@pytest.mark.parametrize("code,message,published", [
    (1, "Traceback: integrity", False), (124, "timeout integrity", False),
    (2, "ERROR: backend unavailable", False), (2, "ERROR: integrity", True),
])
def test_crashes_timeouts_capability_failures_and_publication_are_not_rejections(code, message, published) -> None:
    assert not rejection_matches(code, message, ["integrity"], published)


def test_evaluation_runs_real_cli_and_reopens_every_accepted_step(tmp_path) -> None:
    pytest.importorskip("build123d")
    output = tmp_path / "evidence"
    report = evaluate(output)
    assert report["passed"]
    assert report["case_count"] == report["passed_count"] == 17
    assert report["expected_accept_count"] == 5
    assert report["expected_reject_count"] == 12
    assert report["baseline_unchanged"]
    for case in report["cases"]:
        assert case["published"] is case["expected_accept"]
        if case["expected_accept"]:
            assert case["reopened_step"]["requirements"]["satisfied_for_all_must"]
            assert case["reopened_step"]["inspection"]["solid_count"] == 1
        else:
            assert case["returncode"] == 2
    assert report["meshing"]["status"] == "not_run"
    inventory = json.loads((output / "SHA256SUMS.json").read_text(encoding="utf-8"))
    assert all(hashlib.sha256((output / path).read_bytes()).hexdigest() == digest
               for path, digest in inventory.items())
    with pytest.raises(FileExistsError):
        evaluate(output)


def test_timeout_preserves_output_and_cannot_count_as_expected_rejection(tmp_path, monkeypatch) -> None:
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 180, output=b"partial output", stderr=b"partial error")

    monkeypatch.setattr(subprocess, "run", timeout)
    result = command(tmp_path, "timed", "neurocad_cli", ["--help"])
    assert result.returncode == 124
    assert (tmp_path / "timed.stdout.txt").read_text(encoding="utf-8") == "partial output"
    assert "partial error" in (tmp_path / "timed.stderr.txt").read_text(encoding="utf-8")
    assert not rejection_matches(result.returncode, result.stderr, ["error"], False)
