from __future__ import annotations

import json
import math
from itertools import permutations
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


def test_signed_cancellation_is_independent_of_contribution_order() -> None:
    # An exact arithmetic reference, deliberately ill-conditioned. This is a
    # numerical regression, not physically measured manufacturing evidence.
    contributions = tuple(ToleranceContribution(str(i), mean, 0, 0) for i, mean in enumerate((1e16, -1e16, 1)))
    for ordering in permutations(contributions):
        report = tolerance_stack(0.5, ordering)
        assert report.mean_clearance_mm == 1.5
        assert report.worst_case_low_mm == 1.5


@pytest.mark.parametrize("field", ["nominal", "mean", "sigma", "worst", "confidence"])
def test_oversized_integer_inputs_raise_validation_errors_not_conversion_crashes(field: str) -> None:
    values = {"nominal": 0.5, "mean": 0, "sigma": 0.1, "worst": 0.3, "confidence": 3}
    values[field] = 10**1000
    contribution = ToleranceContribution("measurement", values["mean"], values["sigma"], values["worst"])
    with pytest.raises(ValueError, match="finite numerical range"):
        tolerance_stack(values["nominal"], (contribution,), confidence_multiplier=values["confidence"])


def test_correlation_permutation_and_length_scaling_preserve_the_model() -> None:
    import numpy as np

    rng = np.random.default_rng(8709)
    factors = rng.normal(size=(6, 4))
    factors /= np.linalg.norm(factors, axis=1)[:, None]
    matrix = factors @ factors.T
    # Unit diagonal is exact; rows are dependent, so singular PSD is intentional.
    np.fill_diagonal(matrix, 1)
    sigmas = np.arange(1, 7) / 20
    contributions = tuple(ToleranceContribution(str(i), (-1)**i * 0.03, float(sigma), 0.2) for i, sigma in enumerate(sigmas))
    original = tolerance_stack(0.5, contributions, correlations=tuple(map(tuple, matrix)))
    # Independent factor-space reference: ||A^T s||, not the implementation's s^T R s.
    assert original.sigma_mm == pytest.approx(float(np.linalg.norm(factors.T @ sigmas)))
    permutation = [5, 1, 3, 0, 4, 2]
    reordered = tolerance_stack(0.5, tuple(contributions[i] for i in permutation), correlations=tuple(map(tuple, matrix[np.ix_(permutation, permutation)])))
    assert reordered.sigma_mm == pytest.approx(original.sigma_mm)
    assert reordered.success_probability == pytest.approx(original.success_probability)
    for factor in (0.001, 1000):
        scaled = tuple(ToleranceContribution(c.name, c.mean_mm * factor, c.sigma_mm * factor, c.worst_case_mm * factor) for c in contributions)
        report = tolerance_stack(0.5 * factor, scaled, correlations=tuple(map(tuple, matrix)))
        assert report.sigma_mm == pytest.approx(original.sigma_mm * factor)
        assert report.recommended_clearance_mm == pytest.approx(original.recommended_clearance_mm * factor)
        assert report.success_probability == pytest.approx(original.success_probability)
