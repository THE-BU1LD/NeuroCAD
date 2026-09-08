from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from core.engineering_math import ToleranceContribution, tolerance_stack
from neurocad_cli import build_parser


def _contributions() -> tuple[ToleranceContribution, ...]:
    return (ToleranceContribution("hole", -0.1, 0.2, 0.4), ToleranceContribution("shaft", -0.05, 0.2, 0.3))


def test_independent_correlated_and_common_mode_cancellation() -> None:
    independent = tolerance_stack(0.5, _contributions())
    correlated = tolerance_stack(0.5, _contributions(), correlations=((1, 1), (1, 1)))
    cancelling = tolerance_stack(0.5, _contributions(), correlations=((1, -1), (-1, 1)))
    assert independent.sigma_mm == pytest.approx(math.sqrt(0.08))
    assert correlated.sigma_mm == pytest.approx(0.4)
    assert cancelling.sigma_mm == 0
    assert cancelling.success_probability == 1
    assert correlated.success_probability < independent.success_probability
    assert correlated.worst_case_low_mm == pytest.approx(-0.35)
    assert correlated.recommended_clearance_mm == pytest.approx(1.35)


@pytest.mark.parametrize("matrix", [((1, 0.2), (0.3, 1)), ((1, 2), (2, 1)), ((2, 0), (0, 1)),
                                    ((True, False), (False, True)), ((True, 0.2), (0.2, 1)), ((1,),), ((1, math.nan), (math.nan, 1))])
def test_invalid_correlation_matrices_are_rejected(matrix: tuple) -> None:
    with pytest.raises(ValueError, match="correlations"):
        tolerance_stack(0.5, _contributions(), correlations=matrix)


def test_pairwise_valid_but_indefinite_matrix_is_rejected() -> None:
    # Every 2x2 minor is plausible; the full covariance is impossible.
    matrix = ((1, -0.9, -0.9), (-0.9, 1, -0.9), (-0.9, -0.9, 1))
    with pytest.raises(ValueError, match="positive semidefinite"):
        tolerance_stack(0.5, _contributions() + (ToleranceContribution("third", 0, 0.2, 0.3),), correlations=matrix)


def test_duplicate_names_boolean_mean_and_numerical_overflow_fail() -> None:
    for contributions in (
        _contributions()[:1] * 2,
        (ToleranceContribution("bad", True, 0.1, 0.2),),
        (ToleranceContribution("huge", 0, 1e308, 0.2),),
    ):
        with pytest.raises(ValueError):
            tolerance_stack(0.5, contributions)


def test_correlated_overflow_cannot_be_clamped_into_false_zero_variance() -> None:
    huge = (ToleranceContribution("one", 0, 1e308, 0), ToleranceContribution("two", 0, 1e308, 0))
    with pytest.raises(ValueError, match="finite numerical"):
        tolerance_stack(0.5, huge, correlations=((1, 1), (1, 1)))


def test_tolerance_cli_real_request_and_non_clobber(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    source, output = tmp_path / "request.json", tmp_path / "report.json"
    source.write_text(json.dumps({
        "nominal_clearance_mm": 0.5,
        "contributions": [{"name": "printer", "mean_mm": -0.1, "sigma_mm": 0.2, "worst_case_mm": 0.3}],
        "correlations": [[1]],
    }))
    args = build_parser().parse_args(["tolerance", str(source), "-o", str(output)])
    assert args.func(args) == 0
    report = json.loads(output.read_text())
    assert report["result"]["sigma_mm"] == 0.2
    assert report["variation_model"] == "joint_normal_correlated"
    with pytest.raises(FileExistsError):
        args.func(args)
