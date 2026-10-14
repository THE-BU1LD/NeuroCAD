"""Independent circular-boundary references, including a formerly false yield pass.

Integrating r**2 and r**4 over an annulus supplies area and inertia. Maximizing
a*sin(theta)+b*cos(theta) analytically supplies the full-boundary stress, without
sampling the production material points. Known-case engineering regression only.
"""

import math

import pytest

from core.complex_shapes import build_complex_shape


@pytest.mark.parametrize("inner_radius", [0, 5])
@pytest.mark.parametrize("mx,my,axial,torque", [
    (5000, 0, 0, 0), (0, 5000, 0, 0), (3000, 4000, 0, 0),
    (-3000, -4000, 0, 0), (3000, 4000, 1000, 0),
    (3000, -4000, -1000, 2000), (0, 0, 0, 0),
])
def test_full_annulus_boundary_and_derived_yield(mx, my, axial, torque, inner_radius):
    radius, length, young, shear, density = 10, 100, 200000, 80000, 7800
    report = build_complex_shape({
        "schema_version": "neurocad-complex-shape-request-v1", "shape": "hollow_shaft",
        "parameters": {"outer_diameter_mm": 2 * radius, "inner_diameter_mm": 2 * inner_radius,
                       "length_mm": length},
        "analysis": {"source": "Independent annulus integration and angular extrema reference.",
                     "bending_moment_x_n_mm": mx, "bending_moment_y_n_mm": my,
                     "axial_force_n": axial, "torque_n_mm": torque,
                     "yield_strength_mpa": 10.5, "elastic_modulus_mpa": young,
                     "shear_modulus_mpa": shear, "density_kg_m3": density},
    }).analysis
    area = math.pi * (radius - inner_radius) * (radius + inner_radius)
    inertia = area * (radius**2 + inner_radius**2) / 4
    mean = axial / area
    amplitude = radius * math.hypot(mx, my) / inertia
    expected_min, expected_max = mean - amplitude, mean + amplitude
    screen = report["structural_screen"]
    assert screen["normal_stress_mpa"] == pytest.approx({
        "minimum": expected_min, "maximum": expected_max,
        "maximum_absolute": abs(mean) + amplitude,
    }, rel=1e-10, abs=1e-10)
    tau = abs(torque) * radius / (2 * inertia)
    mises = math.hypot(abs(mean) + amplitude, math.sqrt(3) * tau)
    assert screen["maximum_von_mises_screen_mpa"] == pytest.approx(mises, rel=1e-10, abs=1e-10)
    assert screen["yield_utilization"] == pytest.approx(mises / 10.5, rel=1e-10, abs=1e-10)
    assert screen["constraint_satisfied"] is (mises <= 10.5)
    assert report["cross_section"]["area_mm2"] == pytest.approx(area, rel=1e-10)
    assert report["cross_section"]["principal_second_moments_mm4"] == pytest.approx([inertia, inertia], rel=1e-10)
    assert report["geometry"]["volume_mm3"] == pytest.approx(area * length, rel=1e-10)
    assert report["mass_properties"]["mass_kg"] == pytest.approx(density * area * length * 1e-9, rel=1e-10)
    assert screen["maximum_torsional_shear_mpa"] == pytest.approx(tau, rel=1e-10, abs=1e-10)
    if torque:
        assert screen["twist_radians"] == pytest.approx(torque * length / (2 * shear * inertia), rel=1e-10)
