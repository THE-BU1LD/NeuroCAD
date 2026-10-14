"""Finite conversion contract; authored engineering cases, not physical evidence."""
import math

import pytest

from core.scientific_kernel import quantity


@pytest.mark.parametrize("sign", [1.0, -1.0])
@pytest.mark.parametrize("source,target", [("m", "mm"), ("kg", "g"), ("Pa", "Pa*mm/m"), ("m^3", "mL")])
def test_conversion_rejects_nonfinite_result(sign, source, target):
    value = quantity(sign * 1e308, source)
    with pytest.raises(ValueError, match="finite"):
        value.to(target)


@pytest.mark.parametrize("value,source,target,expected", [
    (1.0, "m", "mm", 1000.0),
    (-1.0, "m", "mm", -1000.0),
    (1000.0, "g", "kg", 1.0),
    (2.0, "h", "min", 120.0),
    (1.0, "m^3", "L", 1000.0),
    (1.0, "Pa", "kPa", 0.001),
    (1e308, "m", "km", 1e305),
    (1e308, "kg", "kg", 1e308),
    (0.0, "m", "mm", 0.0),
    (-0.0, "m", "mm", -0.0),
    (math.ulp(0.0), "m", "m", math.ulp(0.0)),
    (math.ulp(0.0), "m", "km", 0.0),
])
def test_finite_conversions_preserve_existing_behavior(value, source, target, expected):
    result = quantity(value, source).to(target)
    assert math.isfinite(result)
    assert result == pytest.approx(expected, rel=1e-15, abs=0.0)
    if expected == 0.0:
        assert math.copysign(1.0, result) == math.copysign(1.0, expected)


@pytest.mark.parametrize("source,target", [("m", "s"), ("kg", "m"), ("Pa", "J")])
def test_dimension_mismatch_remains_rejected(source, target):
    with pytest.raises(ValueError, match="cannot convert"):
        quantity(1.0, source).to(target)
