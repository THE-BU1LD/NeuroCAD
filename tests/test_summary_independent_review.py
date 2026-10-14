"""Source-bound numerical review with exact rational reference calculations."""
from decimal import Decimal, localcontext
from fractions import Fraction
import math

import pytest

from core.scientific_kernel import _round_sqrt_ratio, _sample_standard_deviation


@pytest.mark.parametrize("scale", [math.ulp(0.0), 1e-310, 1e-200, 1e-20, 1.0, 1e20, 1e200, 1e307])
@pytest.mark.parametrize("pattern", [(0, 1), (-1, 1), (1, 1), (-2, -1, 1, 2), (0, 0, 0, 1)])
def test_sample_sd_matches_high_precision_reference(scale, pattern):
    values = [scale * value for value in pattern]
    fractions = [Fraction.from_float(value) for value in values]
    center = sum(fractions) / len(fractions)
    variance = sum((value - center) ** 2 for value in fractions) / (len(fractions) - 1)
    with localcontext() as context:
        context.prec = 2500
        expected = float((Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt())
    assert _sample_standard_deviation(values) == expected


@pytest.mark.parametrize("lower", [0.0, math.ulp(0.0), math.ldexp(1.0, -1022), 1.0, math.nextafter(1.0, math.inf), math.ldexp(1.0, 1000)])
def test_exact_square_root_midpoint_rounds_to_even(lower):
    upper = math.nextafter(lower, math.inf)
    midpoint = (Fraction.from_float(lower) + Fraction.from_float(upper)) / 2
    squared = midpoint * midpoint
    # Conversion of an exact rational midpoint supplies a separate rounding oracle.
    expected = float(midpoint)
    assert _round_sqrt_ratio(squared.numerator, squared.denominator) == expected


def test_unrepresentable_standard_deviation_is_rejected():
    with pytest.raises(OverflowError):
        _sample_standard_deviation([-1.7e308, 1.7e308])
