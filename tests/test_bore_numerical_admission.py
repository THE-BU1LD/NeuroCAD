"""Arithmetic admission tests; no native kernel or geometric result is simulated."""
import math

import pytest
from test_final_bore_contract import probe

from core.final_geometry import measure_bore, validate_probe


def shifted(axis, value):
    p = probe()
    p["entry_mm"][axis] = value
    return p


INVALID = [
    shifted(axis, sign * 1e20)
    for axis in range(3) for sign in (-1, 1)
] + [
    {**probe(), "tolerance_mm": 1e-20},
    {**probe(), "radius_mm": 1e200},
    {**probe(), "clearance_mm": 1e200},
    {**probe(), "entry_mm": [0, 0, 1e308], "depth_mm": 1e308},
    {**probe(), "entry_mm": [0, 0, -1e308], "direction": -1, "depth_mm": 1e308},
    # The increment is nonzero, but the position's ULP exceeds tolerance.
    shifted(0, 2**43),
    # Every offset resolves, but computing the squared radius overflows.
    {**probe(), "radius_mm": 1e160, "depth_mm": 1e160,
     "clearance_mm": 1e159, "tolerance_mm": 1e150},
]


@pytest.mark.parametrize("p", INVALID)
def test_nonrepresentable_probe_refused(p):
    with pytest.raises((ValueError, TypeError)):
        validate_probe(p)


@pytest.mark.parametrize("p", INVALID)
def test_rejection_precedes_shape_and_kernel_access(p):
    class Forbidden:
        def __getattr__(self, name):
            raise AssertionError(f"Invalid geometry reached native access: {name}")

    with pytest.raises((ValueError, TypeError)):
        measure_bore(Forbidden(), Forbidden(), p)


@pytest.mark.parametrize("axis", ["x", "y", "z"])
@pytest.mark.parametrize("direction", [-1, 1])
@pytest.mark.parametrize("scale", [0.001, 1, 1000])
def test_supported_scale_and_axis_controls(axis, direction, scale):
    p = {**probe(), "axis": axis, "direction": direction,
         "entry_mm": [125 * scale, -250 * scale, 1000 * scale]}
    for key in ("radius_mm", "depth_mm", "clearance_mm", "tolerance_mm"):
        p[key] *= scale
    p["volume_tolerance_mm3"] *= scale**3
    validate_probe(p)


def test_witnesses_are_actual_float_information_loss():
    assert 1e20 + 8 == 1e20
    assert 3 - 1e-20 == 3 + 1e-20 == 3
    assert math.ulp(2**43) > probe()["tolerance_mm"]
    assert 2**43 + 0.001 != 2**43
