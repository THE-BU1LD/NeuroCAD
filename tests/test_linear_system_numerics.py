"""Analytic regressions for residual diagnostics, not solver benchmarks."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from core.scientific_kernel import linear_system_diagnostics


def test_integer_products_cannot_wrap_to_an_exact_solution() -> None:
    result = linear_system_diagnostics(((2**32,),), (0,), (2**32,))
    assert result["residual_norm"] == float(2**64)
    assert result["relative_backward_error"] == pytest.approx(1.0)
    assert result["rank"] == 1


def test_integer_subtraction_cannot_wrap_the_residual() -> None:
    result = linear_system_diagnostics(((1,),), (-(2**62),), (2**62,))
    assert result["residual_norm"] == float(2**63)
    assert result["relative_backward_error"] == pytest.approx(1.0)


@pytest.mark.parametrize("scale", [1e-200, 1.0, 1e200])
def test_backward_error_and_rank_are_invariant_under_equation_scaling(scale: float) -> None:
    result = linear_system_diagnostics(
        ((3.0 * scale, 0.0), (0.0, 4.0 * scale)),
        (0.0, 0.0),
        (1.0, 1.0),
    )
    assert result["residual_norm"] == pytest.approx(5.0 * scale, rel=1e-12, abs=0.0)
    assert result["relative_backward_error"] == pytest.approx(1 / math.sqrt(2))
    assert result["condition_number"] == pytest.approx(4 / 3)
    assert result["rank"] == 2
    json.dumps(result, allow_nan=False)


def test_representable_product_above_the_square_root_of_float_max_is_finite() -> None:
    result = linear_system_diagnostics(((1e200,),), (0.0,), (1e100,))
    assert result["residual_norm"] == pytest.approx(1e300)
    assert result["relative_backward_error"] == pytest.approx(1.0)
    json.dumps(result, allow_nan=False)


def test_large_denominator_cannot_turn_a_material_backward_error_into_zero() -> None:
    result = linear_system_diagnostics(((1e200,),), (5e299,), (1e100,))
    assert result["residual_norm"] == pytest.approx(5e299)
    assert result["relative_backward_error"] == pytest.approx(1 / 3)


def test_residual_in_a_small_coefficient_direction_remains_visible() -> None:
    result = linear_system_diagnostics(((1.0, 1e-200), (1.0, 0.0)), (0.0, 0.0), (0.0, 1.0))
    assert result["residual_norm"] == pytest.approx(1e-200, rel=1e-12, abs=0.0)
    assert result["relative_backward_error"] == pytest.approx(1e-200 / math.sqrt(2), rel=1e-12, abs=0.0)


def test_representable_residual_survives_mixed_dynamic_range() -> None:
    result = linear_system_diagnostics(((1e308, 0.0), (0.0, 1e-308)), (0.0, 0.0), (0.0, 1e308))
    assert result["residual_norm"] == pytest.approx(1.0)
    assert result["relative_backward_error"] == 0.0  # Its exact ratio is below binary64 range.
    assert result["ill_conditioned"]


def test_subnormal_product_still_has_a_scale_free_backward_error() -> None:
    result = linear_system_diagnostics(((1e-200,),), (0.0,), (1e-200,))
    assert result["residual_norm"] == 0.0  # The true 1e-400 norm cannot be represented.
    assert result["relative_backward_error"] == pytest.approx(1.0)


def test_unrepresentable_residual_fails_instead_of_returning_nonfinite_json() -> None:
    with pytest.raises(ValueError, match="residual norm exceeds the finite numerical range"):
        linear_system_diagnostics(((1e308,),), (0.0,), (1e308,))


@pytest.mark.parametrize(
    ("matrix", "rhs", "solution", "error", "rank"),
    [
        (((0.0,),), (0.0,), (0.0,), 0.0, 0),
        (((0.0,),), (2.0,), (0.0,), 1.0, 0),
        (((3.0, 1.0), (1.0, 2.0)), (9.0, 8.0), (2.0, 3.0), 0.0, 2),
        (((1.0, 1.0),), (2.0,), (1.0, 1.0), 0.0, 1),
    ],
)
def test_zero_exact_and_rectangular_systems(
    matrix: tuple[tuple[float, ...], ...],
    rhs: tuple[float, ...],
    solution: tuple[float, ...],
    error: float,
    rank: int,
) -> None:
    result = linear_system_diagnostics(matrix, rhs, solution)
    assert result["relative_backward_error"] == pytest.approx(error)
    assert result["rank"] == rank
    assert np.isfinite(result["residual_norm"])
