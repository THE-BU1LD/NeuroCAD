"""Analytical admission and moment identities for quadratic clearance estimates."""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import numpy as np
import pytest

from core.engineering_math import ToleranceContribution, quadratic_tolerance_stack


def _terms(sigma: float = 0.1) -> tuple[ToleranceContribution, ...]:
    return (
        ToleranceContribution("first", 0.0, sigma, 0.0),
        ToleranceContribution("second", 0.0, sigma, 0.0),
    )


def test_overflowing_correlated_variance_cannot_become_zero_uncertainty() -> None:
    # The exact variance is 1e600: finite inputs must not produce a zero-risk
    # report when intermediate positive/negative matrix products become NaN.
    with pytest.raises(ValueError, match="finite numerical range"):
        quadratic_tolerance_stack(
            0.5, _terms(1e100), sensitivities=(1e200, -1e200),
            hessian_per_mm=((0.0, 0.0), (0.0, 0.0)),
            correlations=((1.0, 0.5), (0.5, 1.0)),
        )


@pytest.mark.parametrize("field", ["sensitivities", "hessian_per_mm", "correlations"])
@pytest.mark.parametrize("boolean", [True, np.bool_(True)])
def test_mixed_boolean_parameters_are_rejected_before_float_coercion(field: str, boolean: object) -> None:
    parameters = {
        "sensitivities": (1.0, 1.0),
        "hessian_per_mm": ((1.0, 0.0), (0.0, 1.0)),
        "correlations": ((1.0, 0.0), (0.0, 1.0)),
    }
    parameters[field] = (boolean, 1.0) if field == "sensitivities" else ((boolean, 0.0), (0.0, 1.0))
    with pytest.raises(ValueError, match=field):
        quadratic_tolerance_stack(0.5, _terms(), **parameters)


@pytest.mark.parametrize("sensitivities", [((1.0, 0.0), (0.0, 1.0)), ((1.0,), (2.0,))])
def test_sensitivity_matrix_is_rejected_as_a_shape_error(sensitivities: tuple) -> None:
    with pytest.raises(ValueError, match="sensitivities"):
        quadratic_tolerance_stack(
            0.5, _terms(), sensitivities=sensitivities,
            hessian_per_mm=((0.0, 0.0), (0.0, 0.0)),
        )


def test_quadratic_moments_match_exact_gaussian_cubature() -> None:
    # Three-point Gauss-Hermite cubature integrates each coordinate's
    # polynomial moments through degree five, including q(X) and q(X)^2.
    # This evaluates the scalar polynomial directly, independently of the
    # implementation's covariance trace formula.
    means = (0.2, -0.3)
    sigmas = (0.3, 0.4)
    rho = 0.5
    nominal = 0.7
    support = ((-math.sqrt(3), 1 / 6), (0.0, 2 / 3), (math.sqrt(3), 1 / 6))
    moments = []
    for (z0, w0), (z1, w1) in itertools.product(support, repeat=2):
        x = means[0] + sigmas[0] * z0
        y = means[1] + sigmas[1] * (rho * z0 + math.sqrt(1 - rho**2) * z1)
        clearance = nominal + 2 * x - y + x*x + x*y - y*y
        moments.append((w0 * w1, clearance))
    expected_mean = math.fsum(weight * value for weight, value in moments)
    expected_variance = math.fsum(weight * (value - expected_mean)**2 for weight, value in moments)
    result = quadratic_tolerance_stack(
        nominal,
        tuple(ToleranceContribution(str(i), mean, sigma, 0.1) for i, (mean, sigma) in enumerate(zip(means, sigmas))),
        sensitivities=(2.0, -1.0), hessian_per_mm=((2.0, 1.0), (1.0, -2.0)),
        correlations=((1.0, rho), (rho, 1.0)),
    )
    assert result.mean_clearance_mm == pytest.approx(expected_mean, rel=1e-13)
    assert result.variance_mm2 == pytest.approx(expected_variance, rel=1e-13)
    assert result.sigma_mm == pytest.approx(math.sqrt(expected_variance), rel=1e-13)


def test_zero_variance_and_singular_correlation_remain_valid() -> None:
    result = quadratic_tolerance_stack(
        0.5, _terms(), sensitivities=(1.0, -1.0),
        hessian_per_mm=((0.0, 0.0), (0.0, 0.0)),
        correlations=((1.0, 1.0), (1.0, 1.0)),
    )
    assert result.variance_mm2 == 0.0
    assert result.moment_matched_success_probability == 1.0
    assert result.mean_clearance_mm == 0.5


def test_overflowing_cli_request_cannot_publish_a_success_report(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    from neurocad_cli import build_parser

    source, output = tmp_path / "input.json", tmp_path / "report.json"
    source.write_text(json.dumps({
        "model": "quadratic", "nominal_clearance_mm": 0.5,
        "contributions": [
            {"name": name, "mean_mm": 0.0, "sigma_mm": 1e100, "worst_case_mm": 0.0}
            for name in ("first", "second")
        ],
        "sensitivities": [1e200, -1e200], "hessian_per_mm": [[0.0, 0.0], [0.0, 0.0]],
        "correlations": [[1.0, 0.5], [0.5, 1.0]],
    }), encoding="utf-8")
    args = build_parser().parse_args(["tolerance", str(source), "-o", str(output)])
    with pytest.raises(ValueError, match="finite numerical range"):
        args.func(args)
    assert not output.exists()
    assert capsys.readouterr().out == ""
