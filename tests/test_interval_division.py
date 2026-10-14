"""Exact-rational references for finite interval division at floating-point limits."""

from __future__ import annotations

import math
import sys
from fractions import Fraction

import pytest

from core.scientific_kernel import Interval

TINY = math.nextafter(0.0, 1.0)


@pytest.mark.parametrize(
    ("numerator", "denominator"),
    [
        ((1e-310, 1e-310), (1e-310, 1e-310)),
        ((-1e-310, -1e-310), (1e-310, 1e-310)),
        ((1e-310, 1e-310), (-1e-310, -1e-310)),
        ((-1e-310, -1e-310), (-1e-310, -1e-310)),
        ((1e-310, 2e-310), (1e-310, 3e-310)),
        ((-3e-310, -1e-310), (1e-310, 2e-310)),
        ((-1e-310, 2e-310), (1e-310, 3e-310)),
        ((-1e-310, 2e-310), (-3e-310, -1e-310)),
        ((TINY, 2 * TINY), (TINY, 3 * TINY)),
        ((-TINY, TINY), (-2 * TINY, -TINY)),
        ((0.0, 0.0), (TINY, 2 * TINY)),
        ((0.1, 0.3), (0.2, 0.7)),
        ((-9.0, -3.0), (-4.0, -2.0)),
        ((-3.0, 8.0), (2.0, 9.0)),
        ((sys.float_info.min, sys.float_info.min), (1.0, 2.0)),
        ((TINY, TINY), (2.0, 4.0)),
        ((1.0, 2.0), (1e300, 2e300)),
        ((sys.float_info.max / 4, sys.float_info.max / 2), (1.0, 2.0)),
    ],
)
def test_division_encloses_exact_endpoint_ratios(
    numerator: tuple[float, float], denominator: tuple[float, float]
) -> None:
    result = Interval(*numerator) / Interval(*denominator)
    # Fractions represent the actual binary inputs exactly. This does not use
    # rounded floating-point division as the expected result.
    exact_ratios = [Fraction.from_float(left) / Fraction.from_float(right) for left in numerator for right in denominator]
    assert math.isfinite(result.lower) and math.isfinite(result.upper)
    assert Fraction.from_float(result.lower) <= min(exact_ratios)
    assert Fraction.from_float(result.upper) >= max(exact_ratios)


@pytest.mark.parametrize("denominator", [(0.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (-1.0, 1.0)])
def test_zero_containing_divisors_still_fail(denominator: tuple[float, float]) -> None:
    with pytest.raises(ZeroDivisionError, match="contains zero"):
        Interval(1.0, 2.0) / Interval(*denominator)


@pytest.mark.parametrize("sign", [-1.0, 1.0])
def test_unrepresentable_quotients_still_fail(sign: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        Interval(sign, sign) / Interval(TINY, TINY)
