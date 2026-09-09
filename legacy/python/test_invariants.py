import math
from main import CADPart, Assembly

def assert_finite(x, name="value"):
    assert not math.isnan(x), f"{name} is NaN"
    assert not math.isinf(x), f"{name} is infinite"


def test_volume_invariants():
    parts = [
        CADPart("cube", "cube", size=5),
        CADPart("sphere", "sphere", radius=3),
        CADPart("cyl", "cylinder", radius=2, height=10),
    ]

    for p in parts:
        v = p.volume()
        assert v > 0, f"{p.name} has non-positive volume"
        assert_finite(v, p.name)

    print("✓ Volume invariants hold")


def test_hollow_monotonicity():
    solid = CADPart("solid", "cylinder", radius=3, height=10)
    hollow = CADPart(
        "hollow",
        "cylinder",
        radius=3,
        height=10,
        hollow=True,
        wall_thickness=1.0
    )

    assert hollow.volume() < solid.volume()
    print("✓ Hollow volume monotonicity holds")


def test_assembly_volume_consistency():
    parts = [
        CADPart("a", "cube", size=5),
        CADPart("b", "cube", size=3)
    ]

    a = Assembly("test", parts)
    assert math.isclose(
        a.total_volume(),
        sum(p.volume() for p in parts),
        rel_tol=1e-9
    )

    print("✓ Assembly volume consistency holds")
