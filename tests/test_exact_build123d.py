from __future__ import annotations

import math

import pytest

pytest.importorskip("build123d")

from core.exact_build123d import Build123dBackend, Build123dCompileError
from core.feature_ir import EntitySelector, Feature, FeatureProgram


def _program(*features: Feature, output: str) -> FeatureProgram:
    return FeatureProgram(
        title="build123d golden fixture",
        parameters=(),
        features=features,
        outputs=(output,),
        metadata={"fixture": output},
    )


def test_build123d_compiles_exact_box() -> None:
    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [40.0, 30.0, 20.0]}),
        output="body",
    )
    receipt = Build123dBackend().build_receipt(program)
    assert receipt.inspection.valid_brep
    assert receipt.inspection.manifold
    assert receipt.inspection.solid_count == 1
    assert receipt.inspection.extents_mm == pytest.approx((40.0, 30.0, 20.0), abs=1e-8)
    assert receipt.inspection.volume_mm3 == pytest.approx(24000.0, rel=1e-10)


def test_build123d_sketch_extrude_preserves_four_holes() -> None:
    entities = [
        {"kind": "rectangle", "width": 80.0, "height": 60.0, "operation": "add", "center": [0.0, 0.0]},
    ]
    for x in (-30.0, 30.0):
        for y in (-20.0, 20.0):
            entities.append(
                {"kind": "circle", "radius": 2.0, "operation": "subtract", "center": [x, y]}
            )
    program = _program(
        Feature(
            id="plate_sketch",
            kind="sketch",
            parameters={"plane": "XY", "entities": entities, "constraints": []},
        ),
        Feature(
            id="plate",
            kind="extrude",
            inputs=("plate_sketch",),
            parameters={"distance": 6.0, "operation": "new"},
        ),
        output="plate",
    )
    receipt = Build123dBackend().build_receipt(program)
    expected = 80.0 * 60.0 * 6.0 - 4.0 * math.pi * 2.0**2 * 6.0
    assert receipt.inspection.valid_brep
    assert receipt.inspection.solid_count == 1
    assert receipt.inspection.extents_mm == pytest.approx((80.0, 60.0, 6.0), abs=1e-7)
    assert receipt.inspection.volume_mm3 == pytest.approx(expected, rel=1e-7)


def test_build123d_revolve_creates_hollow_cylinder() -> None:
    program = _program(
        Feature(
            id="profile",
            kind="sketch",
            parameters={
                "plane": "XY",
                "entities": [
                    {
                        "kind": "rectangle",
                        "width": 10.0,
                        "height": 20.0,
                        "operation": "add",
                        "center": [10.0, 0.0],
                    }
                ],
                "constraints": [],
            },
        ),
        Feature(
            id="revolved",
            kind="revolve",
            inputs=("profile",),
            parameters={"angle_deg": 360.0, "axis": [0.0, 1.0, 0.0], "operation": "new"},
        ),
        output="revolved",
    )
    receipt = Build123dBackend().build_receipt(program)
    expected = math.pi * (15.0**2 - 5.0**2) * 20.0
    assert receipt.inspection.valid_brep
    assert receipt.inspection.solid_count == 1
    assert receipt.inspection.extents_mm == pytest.approx((30.0, 20.0, 30.0), abs=1e-6)
    assert receipt.inspection.volume_mm3 == pytest.approx(expected, rel=1e-7)


@pytest.mark.parametrize(
    ("kind", "parameters"),
    [
        ("fillet", {"radius": 2.0}),
        ("chamfer", {"distance": 2.0}),
    ],
)
def test_build123d_semantic_edge_operations(kind: str, parameters: dict[str, float]) -> None:
    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [40.0, 30.0, 20.0]}),
        Feature(
            id="finished",
            kind=kind,
            inputs=("body",),
            parameters=parameters,
            selectors=(
                EntitySelector(
                    entity="edge",
                    generated_by="body",
                    predicates=({"kind": "parallel_to", "axis": [0.0, 0.0, 1.0]},),
                    role="vertical_edges",
                    unique=False,
                ),
            ),
        ),
        output="finished",
    )
    receipt = Build123dBackend().build_receipt(program)
    assert receipt.inspection.valid_brep
    assert receipt.inspection.manifold
    assert receipt.inspection.solid_count == 1
    assert receipt.inspection.extents_mm == pytest.approx((40.0, 30.0, 20.0), abs=1e-7)
    assert receipt.inspection.volume_mm3 < 24000.0


def test_build123d_step_roundtrip_retains_geometry(tmp_path) -> None:
    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [32.0, 24.0, 8.0]}),
        output="body",
    )
    receipt = Build123dBackend().export_verified_step(program, tmp_path / "exact-export")
    assert receipt.step_path == "design.step"
    assert receipt.step_sha256
    assert receipt.roundtrip_inspection is not None
    assert receipt.roundtrip_inspection.valid_brep
    assert receipt.roundtrip_inspection.solid_count == receipt.inspection.solid_count
    assert receipt.roundtrip_inspection.extents_mm == pytest.approx(receipt.inspection.extents_mm, abs=1e-6)
    assert receipt.roundtrip_inspection.volume_mm3 == pytest.approx(receipt.inspection.volume_mm3, rel=1e-8)
    assert (tmp_path / "exact-export" / "design.step").is_file()
    assert (tmp_path / "exact-export" / "build-receipt.json").is_file()


def test_build123d_step_roundtrip_fails_closed_on_geometry_drift(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [32.0, 24.0, 8.0]}),
        output="body",
    )
    backend = Build123dBackend()
    monkeypatch.setattr(backend.bd, "import_step", lambda _: backend.bd.Box(33.0, 24.0, 8.0))
    destination = tmp_path / "drifted-export"
    with pytest.raises(Build123dCompileError, match="changed extent"):
        backend.export_verified_step(program, destination)
    assert not destination.exists()


def test_feature_build_cli_writes_verified_step_bundle(tmp_path, capsys) -> None:
    from core.feature_ir import serialize_feature_ir_json
    from neurocad_cli import build_parser

    program = _program(
        Feature(id="body", kind="primitive_box", parameters={"size": [18.0, 12.0, 4.0]}),
        output="body",
    )
    source = tmp_path / "cli-box.ncad2.json"
    source.write_text(serialize_feature_ir_json(program), encoding="utf-8")
    output = tmp_path / "cli-exact"
    args = build_parser().parse_args(
        ["feature", "build", str(source), "--backend", "build123d", "--output-dir", str(output)]
    )
    assert args.func(args) == 0
    payload = __import__("json").loads(capsys.readouterr().out)
    assert payload["backend"] == "build123d"
    assert payload["inspection"]["valid_brep"] is True
    assert payload["roundtrip_inspection"]["valid_brep"] is True
    assert (output / "design.step").is_file()
    assert (output / "build-receipt.json").is_file()
