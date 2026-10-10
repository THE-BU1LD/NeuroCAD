"""Covariance admission must not change when physical units are rescaled."""

from __future__ import annotations

import numpy as np
import pytest

from core.scientific_kernel import monte_carlo_propagate


@pytest.mark.parametrize("scale", [1e-20, 1.0, 1e20])
@pytest.mark.parametrize("matrix", [((-1.0,),), ((1.0, 2.0), (2.0, 1.0))])
def test_indefinite_covariance_is_rejected_at_every_scale(
    scale: float, matrix: tuple[tuple[float, ...], ...]
) -> None:
    covariance = tuple(tuple(value * scale for value in row) for row in matrix)
    with pytest.raises(ValueError, match="positive semidefinite"):
        monte_carlo_propagate(lambda value: float(value[0]), (0.0,) * len(matrix), covariance, samples=16)


@pytest.mark.parametrize("scale", [1e-20, 1.0, 1e20])
def test_asymmetric_covariance_is_rejected_at_every_scale(scale: float) -> None:
    covariance = ((scale, 0.2 * scale), (0.8 * scale, scale))
    with pytest.raises(ValueError, match="symmetric"):
        monte_carlo_propagate(lambda value: float(value[0]), (0.0, 0.0), covariance, samples=16)


def test_negative_variance_is_invalid_even_below_global_roundoff_tolerance() -> None:
    with pytest.raises(ValueError, match="positive semidefinite"):
        monte_carlo_propagate(lambda value: float(value[0]), (0.0, 0.0), ((-1e-18, 0.0), (0.0, 1.0)), samples=16)


@pytest.mark.parametrize("scale", [1e-20, 1.0, 1e20])
def test_valid_covariance_retains_the_existing_seeded_draws(scale: float) -> None:
    covariance = ((scale, 0.25 * scale), (0.25 * scale, scale))
    result = monte_carlo_propagate(
        lambda value: float(value[0] + value[1]), (0.0, 0.0), covariance, samples=64, seed=17
    )
    draws = np.random.default_rng(17).multivariate_normal((0.0, 0.0), covariance, size=64, check_valid="raise")
    outcomes = draws.sum(axis=1)
    assert result["mean"] == pytest.approx(float(np.mean(outcomes)), rel=1e-14, abs=0.0)
    assert result["standard_deviation"] == pytest.approx(float(np.std(outcomes, ddof=1)), rel=1e-14, abs=0.0)


def test_zero_and_rank_deficient_covariances_are_supported() -> None:
    fixed = monte_carlo_propagate(lambda value: float(value[0]), (2.0,), ((0.0,),), samples=16)
    assert fixed["mean"] == 2.0
    assert fixed["standard_deviation"] == 0.0
    correlated = monte_carlo_propagate(
        lambda value: float(value[0] - value[1]), (0.0, 0.0), ((1.0, 1.0), (1.0, 1.0)), samples=32
    )
    assert correlated["standard_deviation"] < 1e-7
