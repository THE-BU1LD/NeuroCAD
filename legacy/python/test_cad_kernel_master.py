"""
Test suite for CADKernel master kernel
Run: python test_cad_kernel_master.py
"""

from cad_master_kernel import CADKernel


def test_basic_primitives():
    core = CADKernel(resolution=96, use_octree=True)

    shapes = [
        ("sphere", {"radius": 0.5}),
        ("box", {"size": [0.6, 0.4, 0.3]}),
        ("torus", {"R": 0.6, "r": 0.2}),
        ("cylinder", {"radius": 0.3, "height": 0.8}),
    ]

    for name, params in shapes:
        mesh = core.build(name, params=params)
        assert len(mesh["verts"]) > 0, f"{name} produced no verts"
        assert len(mesh["faces"]) > 0, f"{name} produced no faces"
        core.export_obj(mesh, f"test_{name}.obj")
        print(f"[OK] {name}:", len(mesh["verts"]), "verts")


def test_boolean_ops():
    core = CADKernel(resolution=96, use_octree=True)

    mesh = core.build(
        "union",
        children=[
            {"type": "sphere", "radius": 0.5},
            {"type": "torus", "R": 0.6, "r": 0.15},
        ],
    )

    assert len(mesh["verts"]) > 0
    core.export_obj(mesh, "test_union.obj")
    print("[OK] union")

    mesh = core.build(
        "difference",
        children=[
            {"type": "box", "size": [0.8, 0.8, 0.8]},
            {"type": "sphere", "radius": 0.5},
        ],
    )

    assert len(mesh["verts"]) > 0
    core.export_obj(mesh, "test_difference.obj")
    print("[OK] difference")


def test_frisbee():
    core = CADKernel(resolution=128, use_octree=True)

    mesh = core.build(
        "frisbee",
        params={"radius": 0.12, "thickness": 0.01},
    )

    assert len(mesh["verts"]) > 0
    core.export_obj(mesh, "test_frisbee.obj")
    print("[OK] frisbee")


if __name__ == "__main__":
    test_basic_primitives()
    test_boolean_ops()
    test_frisbee()
    print("\nALL TESTS PASSED")
