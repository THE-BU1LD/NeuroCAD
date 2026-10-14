"""Exact-rational polygon integrals independently check composite section outputs.

Production splits the I/L profiles into rectangles; these references integrate
the complete oriented boundary using Green's theorem. Structural coefficients
are solved from force/moment balance using rational elimination. These are
authored engineering cases, not physical or independently executed evidence.
"""

import math
from fractions import Fraction as F

import pytest

from core.complex_shapes import build_complex_shape


def polygon_integrals(points):
    edges = list(zip(points, points[1:] + points[:1]))
    terms = [(x, y, u, v, x*v-u*y) for (x, y), (u, v) in edges]
    area = sum(c for x, y, u, v, c in terms) / 2
    cx = sum((x+u)*c for x, y, u, v, c in terms) / (6*area)
    cy = sum((y+v)*c for x, y, u, v, c in terms) / (6*area)
    ix = sum((y*y+y*v+v*v)*c for x, y, u, v, c in terms)/12-area*cy*cy
    iy = sum((x*x+x*u+u*u)*c for x, y, u, v, c in terms)/12-area*cx*cx
    ixy = sum((2*x*y+x*v+u*y+2*u*v)*c for x, y, u, v, c in terms)/24-area*cx*cy
    perimeter = sum(abs(u-x)+abs(v-y) for (x, y), (u, v) in edges)
    return area, cx, cy, ix, iy, ixy, perimeter


def approx(actual, expected):
    assert actual == pytest.approx(float(expected), rel=1e-9, abs=1e-9)


@pytest.mark.parametrize("shape", ["i_beam", "l_bracket"])
@pytest.mark.parametrize("scale", [F(1, 10), F(1), F(10)])
@pytest.mark.parametrize("sign", [-1, 0, 1])
def test_polygon_section_and_structural_balance(shape, scale, sign):
    w, h, t, web, length = [F(n)*scale for n in (40, 60, 4, 3, 200)]
    if shape == "l_bracket":
        points = [(-w/2,-h/2),(w/2,-h/2),(w/2,-h/2+t),(-w/2+t,-h/2+t),
                  (-w/2+t,h/2),(-w/2,h/2)]
        parameters = {"width_mm": w, "height_mm": h, "thickness_mm": t, "length_mm": length}
    else:
        points = [(-w/2,-h/2),(w/2,-h/2),(w/2,-h/2+t),(web/2,-h/2+t),
                  (web/2,h/2-t),(w/2,h/2-t),(w/2,h/2),(-w/2,h/2),
                  (-w/2,h/2-t),(-web/2,h/2-t),(-web/2,-h/2+t),(-w/2,-h/2+t)]
        parameters = {"width_mm": w, "height_mm": h, "flange_thickness_mm": t,
                      "web_thickness_mm": web, "length_mm": length}
    area, cx, cy, ix, iy, ixy, perimeter = polygon_integrals(points)
    axial, fx, fy, mx0, my0 = [F(n*sign) for n in (-100, 7, -11, 31, -23)]
    young, density, safety, yield_strength = F(70000), F(2700), F(2), F(150)
    report = build_complex_shape({
        "schema_version": "neurocad-complex-shape-request-v1", "shape": shape,
        "parameters": {k: float(v) for k, v in parameters.items()},
        "analysis": {"source": "Exact polygon integration and equilibrium reference.",
                     "density_kg_m3": float(density), "elastic_modulus_mpa": float(young),
                     "yield_strength_mpa": float(yield_strength), "safety_factor": float(safety),
                     "effective_length_factor": 2, "axial_force_n": float(axial),
                     "tip_force_x_n": float(fx), "tip_force_y_n": float(fy),
                     "bending_moment_x_n_mm": float(mx0), "bending_moment_y_n_mm": float(my0)},
    }).analysis
    section = report["cross_section"]
    for key, expected in [("area_mm2", area), ("second_moment_x_mm4", ix),
                          ("second_moment_y_mm4", iy), ("product_moment_xy_mm4", ixy)]:
        approx(section[key], expected)
    assert section["centroid_xy_mm"] == pytest.approx([float(cx), float(cy)], rel=1e-9, abs=1e-9)
    approx(report["geometry"]["volume_mm3"], area*length)
    approx(report["geometry"]["surface_area_mm2"], 2*area+perimeter*length)
    mx, my = mx0+fy*length, my0+fx*length
    # Solve integral(sigma*x)=My and integral(sigma*y)=-Mx by elimination.
    b = (-mx-ixy*my/iy)/(ix-ixy*ixy/iy)
    a = (my-ixy*b)/iy
    stresses = [axial/area+a*(x-cx)+b*(y-cy) for x, y in points]
    lo, hi = min(stresses), max(stresses)
    peak = max(abs(lo), abs(hi))
    screen = report["structural_screen"]
    assert screen["normal_stress_mpa"] == pytest.approx({
        "minimum": float(lo), "maximum": float(hi), "maximum_absolute": float(peak),
    }, rel=1e-9, abs=1e-9)
    approx(screen["maximum_von_mises_screen_mpa"], peak)
    approx(screen["yield_utilization"], peak*safety/yield_strength)
    dx = (fx+ixy*fy/ix)/(iy-ixy*ixy/ix)*length**3/(3*young)
    dy = (fy+ixy*fx/iy)/(ix-ixy*ixy/iy)*length**3/(3*young)
    approx(screen["cantilever_tip_displacement_mm"]["x"], dx)
    approx(screen["cantilever_tip_displacement_mm"]["y"], dy)
    eigen_gap = math.sqrt(float((ix-iy)**2+4*ixy**2))
    principal = [(float(ix+iy)-eigen_gap)/2, (float(ix+iy)+eigen_gap)/2]
    assert section["principal_second_moments_mm4"] == pytest.approx(principal, rel=1e-9)
    critical = math.pi**2*float(young)*principal[0]/float(2*length)**2
    approx(screen["euler_buckling"]["minimum_axis_critical_compressive_load_n"], critical)
    utilization = max(0, float(-axial))*float(safety)/critical
    approx(screen["euler_buckling"]["utilization"], utilization)
    assert screen["constraint_satisfied"] is (peak*safety <= yield_strength and utilization <= 1)
    # Obtain the first cantilever eigenvalue independently instead of copying its constant.
    lower, upper = 1.8, 1.9
    for _ in range(60):
        midpoint = (lower+upper)/2
        if math.cos(midpoint)*math.cosh(midpoint)+1 > 0:
            lower = midpoint
        else:
            upper = midpoint
    frequencies = [midpoint**2/(2*math.pi*float(length)**2)
                   * math.sqrt(float(young)*moment*1e12/float(density*area)) for moment in principal]
    assert screen["ideal_cantilever_bending_frequencies_hz"] == pytest.approx(frequencies, rel=1e-9)
    mass = density*area*length/F(10**9)
    approx(report["mass_properties"]["mass_kg"], mass)
    for key, expected in [("about_x", ix/area+length**2/12),
                          ("about_y", iy/area+length**2/12),
                          ("about_z", (ix+iy)/area), ("product_xy", ixy/area)]:
        approx(report["mass_properties"]["centroidal_mass_moments_kg_m2"][key], mass*expected/F(10**6))


@pytest.mark.parametrize("positions", [[(0, 0)], [(-30, -20), (-30, 20), (30, -20), (30, 20)]])
def test_perforated_plate_signed_area_and_mass_integrals(positions):
    count = len(positions)
    area = 8000-count*25*math.pi
    ix = 100*80**3/12-sum(25*math.pi*(y*y+25/4) for x, y in positions)
    iy = 80*100**3/12-sum(25*math.pi*(x*x+25/4) for x, y in positions)
    report = build_complex_shape({
        "schema_version": "neurocad-complex-shape-request-v1", "shape": "perforated_plate",
        "parameters": {"width_mm": 100, "height_mm": 80, "thickness_mm": 4,
                       "hole_diameter_mm": 10, "columns": 1 if count == 1 else 2,
                       "rows": 1 if count == 1 else 2, "edge_margin_mm": 20},
        "analysis": {"source": "Signed rectangle/circle integrals.", "density_kg_m3": 2700},
    }).analysis
    for key, expected in [("net_area_mm2", area), ("second_moment_x_mm4", ix), ("second_moment_y_mm4", iy)]:
        approx(report["face_section"][key], expected)
    approx(report["geometry"]["volume_mm3"], 4*area)
    approx(report["geometry"]["surface_area_mm2"], 2*area+360*4+count*10*math.pi*4)
    mass = 2700*4*area*1e-9
    approx(report["mass_properties"]["mass_kg"], mass)
    for key, expected in [("about_x", ix/area+16/12), ("about_y", iy/area+16/12),
                          ("about_z", (ix+iy)/area), ("product_xy", 0)]:
        approx(report["mass_properties"]["centroidal_mass_moments_kg_m2"][key], mass*expected*1e-6)
    assert report["structural_screen"] is None
