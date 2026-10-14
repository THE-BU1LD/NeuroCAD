from __future__ import annotations

import json

import pytest

# The frozen study harness requires POSIX resource accounting; product physics
# tests remain portable and run on every supported platform.
pytest.importorskip("resource", reason="Frozen study harness requires POSIX resource accounting")

from research.physics_v2.study import (
    EXPECTED_CONFIRMATORY_CASES,
    analyze,
    canonical_sha256,
    execute_case,
    generate_confirmatory_cases,
    generate_development_cases,
    run_study,
)


def test_confirmatory_generator_is_deterministic_and_matches_frozen_matrix() -> None:
    first = generate_confirmatory_cases()
    second = generate_confirmatory_cases()
    assert len(first) == EXPECTED_CONFIRMATORY_CASES == 216
    assert canonical_sha256(first) == canonical_sha256(second)
    assert len({case["task_id"] for case in first}) == len(first)
    counts = {family: sum(case["family"] == family for case in first) for family in {case["family"] for case in first}}
    assert counts == {
        "geometry_input_contradiction": 24,
        "load_input_contradiction": 24,
        "material_input_contradiction": 24,
        "non_geometric_mutation": 24,
        "post_result_geometry_mutation": 48,
        "stale_expected_hash": 24,
        "valid": 48,
    }


def test_development_matrix_is_separate_and_bounded() -> None:
    development = generate_development_cases()
    confirmatory = generate_confirmatory_cases()
    assert len(development) == 12
    assert all(case["task_id"].startswith("development-") for case in development)
    assert not {case["task_id"] for case in development} & {case["task_id"] for case in confirmatory}


def test_each_mechanism_family_behaves_as_predeclared(tmp_path) -> None:
    cases = generate_confirmatory_cases()
    selected = []
    for family in (
        "valid",
        "geometry_input_contradiction",
        "material_input_contradiction",
        "load_input_contradiction",
        "stale_expected_hash",
        "post_result_geometry_mutation",
        "non_geometric_mutation",
    ):
        selected.append(next(case for case in cases if case["family"] == family))
    records = [execute_case(case, tmp_path) for case in selected]
    by_family = {record["family"]: record for record in records}

    assert by_family["valid"]["arms"]["full"]["accepted"] is True
    assert by_family["valid"]["arms"]["full"]["deterministic"] is True
    for family in ("geometry_input_contradiction", "material_input_contradiction", "load_input_contradiction"):
        assert by_family[family]["arms"]["full"]["detected"] is True
        assert by_family[family]["arms"]["hash_only"]["detected"] is False
        assert by_family[family]["arms"]["unbound"]["detected"] is False
    assert by_family["stale_expected_hash"]["arms"]["full"]["detected"] is True
    assert by_family["stale_expected_hash"]["arms"]["hash_only"]["detected"] is True
    assert by_family["post_result_geometry_mutation"]["arms"]["full"]["detected"] is True
    assert by_family["post_result_geometry_mutation"]["arms"]["hash_only"]["detected"] is True
    assert by_family["post_result_geometry_mutation"]["arms"]["unbound"]["detected"] is False
    assert by_family["non_geometric_mutation"]["arms"]["full"]["current"] is True
    assert by_family["non_geometric_mutation"]["arms"]["hash_only"]["current"] is True


def test_development_run_retains_raw_results_and_metrics(tmp_path) -> None:
    output = tmp_path / "development-run"
    result = run_study(generate_development_cases(), output, phase="development")
    assert result["metrics"]["case_count"] == 12
    assert result["metrics"]["disposition"] == "SUPPORTED_WITHIN_CONTROLLED_CONTRACT"
    assert result["metrics"]["endpoints"]["hash_only_semantic_non_detection"]["rate"] == 1.0
    assert result["metrics"]["endpoints"]["unbound_semantic_non_detection"]["rate"] == 1.0
    assert result["metrics"]["report_size_bytes"]["count"] > 0
    assert (output / "raw_results.jsonl").is_file()
    assert (output / "metrics.json").is_file()
    assert (output / "manifest.json").is_file()
    assert not (output / "work").exists()
    raw = [json.loads(line) for line in (output / "raw_results.jsonl").read_text(encoding="utf-8").splitlines()]
    assert analyze(raw)["disposition"] == "SUPPORTED_WITHIN_CONTROLLED_CONTRACT"
