# examples.py
"""
Creates three richer example designs, writes SCAD files, and prints estimated mass + diagnostics.

- Example 1: Mounting plate with corner holes and rounded edges (approximated)
- Example 2: Rectangular plate with a center hole (approx mass by subtracting hole volume)
- Example 3: Simple plate (thin)
"""

from schema import CADPart, CADPlan, Assembly, Constraint
from geometry import generate_scad
from physics import mass as compute_mass, volume as compute_volume

EXAMPLES = []


def example_mounting_plate():
    # We'll represent plate as a 'plate' primitive with width, length, thickness
    plate = CADPart(
        name="mounting_plate",
        primitive="plate",
        width=120.0,      # mm
        length=80.0,      # mm
        thickness=4.0,    # mm
        fillet=2.0,
        material="PLA"
    )
    # approximate four corner holes: 4 holes of dia 4mm, depth=thickness
    hole_dia = 4.0
    hole_vol_each = (3.14159 * (hole_dia / 2.0) ** 2) * plate.thickness  # mm^3
    approx_hole_vol = 4 * hole_vol_each

    # create assembly-like object to record holes subtraction for mass estimate
    asm = Assembly(parts=[plate], constraints=[])
    return asm, approx_hole_vol


def example_rect_plate_with_center_hole():
    plate = CADPart(
        name="rect_plate",
        primitive="plate",
        width=100.0,
        length=50.0,
        thickness=5.0,
        fillet=1.2,
        material="PLA"
    )
    center_hole_dia = 12.0
    hole_vol = (3.14159 * (center_hole_dia / 2.0) ** 2) * plate.thickness
    asm = Assembly(parts=[plate], constraints=[])
    return asm, hole_vol


def example_simple_plate():
    plate = CADPart(
        name="simple_plate",
        primitive="plate",
        width=60.0,
        length=40.0,
        thickness=3.0,
        fillet=0.5,
        material="PLA"
    )
    asm = Assembly(parts=[plate], constraints=[])
    return asm, 0.0


def run_and_report():
    examples = [
        ("Mounting plate, rounded corners, 4 corner holes", example_mounting_plate),
        ("Rectangular plate with center hole", example_rect_plate_with_center_hole),
        ("Simple thin plate", example_simple_plate),
    ]

    for i, (title, fn) in enumerate(examples, start=1):
        asm, hole_vol = fn()
        part = asm.parts[0]

        vol_mm3 = compute_volume(part, units="mm")
        mass_g = compute_mass(part)
        # subtract hole volume mass estimate
        hole_mass_g = 0.0
        if hole_vol:
            hole_mass_g = (hole_vol * (1.0 / 1000.0)) * (compute_mass(part) / (vol_mm3 * (1.0 / 1000.0))) if vol_mm3 else 0.0
        est_mass = mass_g - hole_mass_g

        scad = generate_scad(asm)
        filename = f"example_{i}_{part.name}.scad"
        with open(filename, "w") as fh:
            fh.write("// " + title + "\n")
            fh.write(scad)

        print(f"Example {i}: {title}")
        print(f" - part name: {part.name}")
        print(f" - primitive: {part.primitive}")
        print(f" - dims (w x l x t): {getattr(part, 'width', 'NA')} x {getattr(part, 'length', 'NA')} x {getattr(part, 'thickness', 'NA')} mm")
        print(f" - raw volume (mm^3): {vol_mm3:.1f}")
        print(f" - estimated mass (g): {est_mass:.2f} (holes mass subtracted ~{hole_mass_g:.2f} g)")
        print(f" - exported SCAD: {filename}")
        print("")


if __name__ == "__main__":
    run_and_report()