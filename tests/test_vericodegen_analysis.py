from __future__ import annotations

import pytest

from research.vericodegen.analysis import (
    AnalysisError,
    analyze_rows,
    exact_mcnemar_pvalue,
    pair_rows,
    paired_bootstrap_difference_ci,
    validate_paired_rows,
    validate_row,
)


def _row(
    prompt_id: str,
    seed: int,
    arm: str,
    family: str,
    *,
    hvr: bool,
    compile_success: bool | None = None,
    hard_constraints_passed: bool | None = None,
    failure_modes: list[str] | None = None,
) -> dict:
    return {
        "prompt_id": prompt_id,
        "seed": seed,
        "arm": arm,
        "task_family": family,
        "hvr": hvr,
        "compile_success": hvr if compile_success is None else compile_success,
        "hard_constraints_passed": hvr if hard_constraints_passed is None else hard_constraints_passed,
        "retry_count": 0,
        "generated_tokens": 100,
        "wall_clock_seconds": 1.5,
        "estimated_cost_usd": 0.01,
        "failure_modes": failure_modes or [],
    }


def _pairs() -> list[dict]:
    rows: list[dict] = []
    outcomes = [
        ("VCG-001", "in_distribution", False, True),
        ("VCG-002", "in_distribution", True, True),
        ("VCG-003", "compositional", True, False),
        ("VCG-004", "compositional", False, True),
        ("VCG-005", "ood_constraint_stress", False, False),
        ("VCG-006", "ood_constraint_stress", False, True),
    ]
    for prompt_id, family, direct_hvr, structured_hvr in outcomes:
        rows.append(_row(prompt_id, 7, "direct", family, hvr=direct_hvr))
        rows.append(_row(prompt_id, 7, "structured", family, hvr=structured_hvr))
    return rows


def test_valid_row_passes():
    assert validate_row(_row("VCG-001", 1, "direct", "in_distribution", hvr=True)) == []


def test_hvr_true_requires_compile_and_constraints():
    row = _row(
        "VCG-001",
        1,
        "direct",
        "in_distribution",
        hvr=True,
        compile_success=False,
        hard_constraints_passed=True,
    )
    assert any("hvr=true requires" in error for error in validate_row(row))


def test_unknown_failure_mode_is_rejected():
    row = _row(
        "VCG-001",
        1,
        "direct",
        "in_distribution",
        hvr=False,
        failure_modes=["quietly_delete_bad_trial"],
    )
    assert any("unsupported failure_modes" in error for error in validate_row(row))


def test_pairing_requires_exactly_one_row_per_arm():
    rows = [
        _row("VCG-001", 1, "direct", "in_distribution", hvr=True),
        _row("VCG-001", 1, "direct", "in_distribution", hvr=True),
    ]
    errors = validate_paired_rows(rows)
    assert any("exactly one direct and one structured" in error for error in errors)
    with pytest.raises(AnalysisError, match="paired analysis blocked"):
        pair_rows(rows)


def test_pairing_rejects_family_mismatch():
    rows = [
        _row("VCG-001", 1, "direct", "in_distribution", hvr=True),
        _row("VCG-001", 1, "structured", "compositional", hvr=True),
    ]
    errors = validate_paired_rows(rows)
    assert any("inconsistent task_family" in error for error in errors)


def test_exact_mcnemar_known_cases():
    assert exact_mcnemar_pvalue(0, 0) == 1.0
    assert exact_mcnemar_pvalue(1, 0) == 1.0
    assert exact_mcnemar_pvalue(5, 0) == pytest.approx(0.0625)
    assert exact_mcnemar_pvalue(10, 0) == pytest.approx(0.001953125)
    assert exact_mcnemar_pvalue(4, 4) == 1.0


def test_exact_mcnemar_rejects_negative_counts():
    with pytest.raises(AnalysisError, match="non-negative"):
        exact_mcnemar_pvalue(-1, 3)


def test_paired_bootstrap_is_deterministic():
    differences = [1, 0, -1, 1, 1, 0]
    first = paired_bootstrap_difference_ci(
        differences,
        confidence=0.95,
        replicates=1000,
        seed=20260831,
    )
    second = paired_bootstrap_difference_ci(
        differences,
        confidence=0.95,
        replicates=1000,
        seed=20260831,
    )
    assert first == second
    assert -1 <= first[0] <= first[1] <= 1


def test_analysis_computes_structured_minus_direct_primary_endpoint():
    report = analyze_rows(
        _pairs(),
        bootstrap_replicates=1000,
        bootstrap_seed=20260831,
    )
    primary = report["primary"]
    assert report["paired_units"] == 6
    assert primary["direct_hvr"] == pytest.approx(2 / 6)
    assert primary["structured_hvr"] == pytest.approx(4 / 6)
    assert primary["difference"] == pytest.approx(2 / 6)
    assert primary["discordance"] == {
        "structured_only_pass": 3,
        "direct_only_pass": 1,
        "both_pass": 1,
        "both_fail": 1,
    }
    assert primary["mcnemar_exact_two_sided_p"] == pytest.approx(0.625)
    assert report["arms"]["direct"]["n"] == 6
    assert report["arms"]["structured"]["n"] == 6
    assert set(report["by_task_family"]) == {
        "in_distribution",
        "compositional",
        "ood_constraint_stress",
    }


def test_secondary_failure_taxonomy_is_retained():
    rows = [
        _row(
            "VCG-001",
            1,
            "direct",
            "in_distribution",
            hvr=False,
            compile_success=False,
            hard_constraints_passed=False,
            failure_modes=["syntax_compile_failure"],
        ),
        _row(
            "VCG-001",
            1,
            "structured",
            "in_distribution",
            hvr=False,
            compile_success=True,
            hard_constraints_passed=False,
            failure_modes=["wrong_dimension_unit"],
        ),
    ]
    report = analyze_rows(rows, bootstrap_replicates=200)
    assert report["arms"]["direct"]["failure_modes"] == {"syntax_compile_failure": 1}
    assert report["arms"]["structured"]["failure_modes"] == {"wrong_dimension_unit": 1}


def test_empty_rows_fail_closed():
    with pytest.raises(AnalysisError, match="at least one paired unit"):
        analyze_rows([], bootstrap_replicates=200)
