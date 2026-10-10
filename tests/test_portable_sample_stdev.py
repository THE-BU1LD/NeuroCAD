"""Exact sample-SD arithmetic and the documented CPython 3.10 reduction path."""

from __future__ import annotations

import math
import statistics
import sys
from decimal import Decimal, localcontext
from fractions import Fraction

import pytest

from core import scientific_kernel as kernel


def decimal_sample_sd(values):
    exact = [Fraction.from_float(value) for value in values]
    mean = sum(exact) / len(exact)
    variance = sum((value - mean) ** 2 for value in exact) / (len(exact) - 1)
    with localcontext() as context:
        context.prec = 200
        return float((Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt())


@pytest.mark.parametrize("values", [
    [-1e308, 1e308, 0.0, 0.0],
    [0.0, math.ulp(0.0), 2 * math.ulp(0.0)],
    [0.0, 1e-200, 2e-200],
    [0.0, 1e-161, 2e-161],
    [1e308, 1e308, 1e308],
])
def test_legacy_variance_then_sqrt_path_cannot_change_public_report(monkeypatch, values):
    # CPython v3.10.21 Lib/statistics.py::stdev converts variance to the
    # floating input type before sqrt. Replay that documented public operation
    # sequence here; this is not execution by an actual Python 3.10 interpreter.
    def legacy_stdev(data):
        return math.sqrt(statistics.variance(data))

    monkeypatch.setattr(kernel.statistics, "stdev", legacy_stdev)
    outputs = iter(values)
    report = kernel.monte_carlo_propagate(
        lambda _draw: next(outputs), (0.0,), ((1.0,),), samples=len(values), seed=43,
    )
    expected = decimal_sample_sd(values)
    assert report["standard_deviation"] == expected
    assert report["standard_error"] == expected / math.sqrt(len(values))
    assert report["schema_version"] == "neurocad-monte-carlo-v1"


@pytest.mark.parametrize("lower,exponent", [
    (2**52, -52), (2**52 + 1, -52), (2**53 - 1, -52),
    (0, -1074), (1, -1074), (2, -1074),
])
def test_exact_square_root_halfway_cases_round_to_even(lower, exponent):
    midpoint = Fraction(2 * lower + 1, 2)
    midpoint *= Fraction(2) ** exponent
    squared = midpoint * midpoint
    expected_integer = lower if lower % 2 == 0 else lower + 1
    expected = math.ldexp(float(expected_integer), exponent)
    actual = kernel._round_sqrt_ratio(squared.numerator, squared.denominator)
    assert actual == expected


@pytest.mark.parametrize("numerator,denominator", [
    (0, 1), (1, 1), (2, 1), (9, 4), (1, 2**2148), (2**2046, 1),
])
def test_square_root_matches_independent_decimal_oracle(numerator, denominator):
    with localcontext() as context:
        context.prec = 200
        expected = float((Decimal(numerator) / Decimal(denominator)).sqrt())
    assert kernel._round_sqrt_ratio(numerator, denominator) == expected


@pytest.mark.parametrize("numerator,denominator", [(-1, 1), (1, 0), (1, -1)])
def test_square_root_rejects_invalid_rational_domain(numerator, denominator):
    with pytest.raises(ValueError, match="nonnegative numerator"):
        kernel._round_sqrt_ratio(numerator, denominator)


@pytest.mark.parametrize("values", [
    [1.0, 2.0, 3.0],
    [1e308, math.nextafter(1e308, 0.0), math.nextafter(1e308, math.inf)],
    [0.0, 1e-300, 2e-300, 3e-300],
    [0.0, 1e-161, 2e-161, 3e-161],
    [-1e100, 1e100, -1e-100, 1e-100],
    [math.ulp(0.0), math.ulp(0.0), 2 * math.ulp(0.0)],
    [-0.0, 0.0, 0.0],
])
def test_integer_sample_variance_matches_exact_centered_oracle(values):
    assert kernel._sample_standard_deviation(values) == decimal_sample_sd(values)


@pytest.mark.parametrize("values", [[], [1.0]])
def test_sample_sd_requires_two_values(values):
    with pytest.raises(ValueError, match="at least two"):
        kernel._sample_standard_deviation(values)


def test_overflow_halfway_is_not_admitted_as_finite():
    maximum = Fraction.from_float(sys.float_info.max)
    midpoint = maximum + Fraction(2) ** 970
    squared = midpoint * midpoint
    with pytest.raises(OverflowError):
        kernel._round_sqrt_ratio(squared.numerator, squared.denominator)
