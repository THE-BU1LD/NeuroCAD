import trimesh

from research.vericodegen.verifier import load_mesh, verify_mesh


def test_exported_stl_preserves_closed_component_semantics(tmp_path):
    path = tmp_path / "box.stl"
    trimesh.creation.box(extents=(2.0, 4.0, 6.0)).export(path)

    mesh = load_mesh(path)
    report = verify_mesh(
        mesh,
        {
            "watertight": True,
            "max_components": 1,
            "volume": {"min": 47.9, "max": 48.1},
            "extents": {
                "x": {"min": 1.99, "max": 2.01},
                "y": {"min": 3.99, "max": 4.01},
                "z": {"min": 5.99, "max": 6.01},
            },
        },
    )

    assert report.passed is True
    assert report.measurements["watertight"] is True
    assert report.measurements["component_count"] == 1
