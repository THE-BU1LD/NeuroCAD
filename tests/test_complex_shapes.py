from __future__ import annotations

import json
import math

import pytest

from core.complex_shapes import build_complex_shape, complex_shape_catalog
from core.ir import validate_program
from core.ir_parser import parse_ir_json
from neurocad_cli import build_parser


def _request(shape: str, parameters: dict[str, object], analysis: dict[str, object] | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "neurocad-complex-shape-request-v1",
        "shape": shape,
        "parameters": parameters,
    }
    if analysis is not None:
        value["analysis"] = analysis
    return value


def test_hollow_shaft_generates_boolean_geometry_and_exact_coupled_analysis() -> None:
    bundle = build_complex_shape(
        _request(
            "hollow_shaft",
            {"outer_diameter_mm": 20, "inner_diameter_mm": 10, "length_mm": 100},
            {
                "source": "Declared unit-test values.",
                "density_kg_m3": 7_800,
                "elastic_modulus_mpa": 200_000,
                "shear_modulus_mpa": 80_000,
                "yield_strength_mpa": 250,
                "safety_factor": 2,
                "axial_force_n": 1_000,
                "tip_force_y_n": 100,
                "torque_n_mm": 10_000,
            },
        )
    )
    assert validate_program(bundle.program).valid
    assert bundle.program.node_map()["hollow_shaft"].composition == "difference"
    report = bundle.analysis
    area = math.pi * (10**2 - 5**2)
    ix = math.pi * (10**4 - 5**4) / 4
    assert report["geometry"]["volume_mm3"] == pytest.approx(area * 100)
    assert report["cross_section"]["second_moment_x_mm4"] == pytest.approx(ix)
    assert report["cross_section"]["polar_second_moment_mm4"] == pytest.approx(2 * ix)
    assert report["mass_properties"]["mass_kg"] == pytest.approx(7_800 * area * 100e-9)
    screen = report["structural_screen"]
    assert screen["root_resultants"]["bending_moment_x_n_mm"] == pytest.approx(10_000)
    assert screen["maximum_torsional_shear_mpa"] == pytest.approx(10_000 * 10 / (2 * ix))
    assert screen["twist_radians"] == pytest.approx(10_000 * 100 / (80_000 * 2 * ix))
    assert screen["constraint_satisfied"] is True
    assert len(report["receipt_sha256"]) == 64


def test_i_beam_reports_exact_section_and_biaxial_cantilever_response() -> None:
    bundle = build_complex_shape(
        _request(
            "i_beam",
            {
                "width_mm": 100,
                "height_mm": 200,
                "flange_thickness_mm": 10,
                "web_thickness_mm": 8,
                "length_mm": 1_000,
            },
            {
                "source": "Declared unit-test values.",
                "density_kg_m3": 7_850,
                "elastic_modulus_mpa": 200_000,
                "yield_strength_mpa": 250,
                "safety_factor": 1.5,
                "tip_force_x_n": 100,
                "tip_force_y_n": 1_000,
            },
        )
    )
    report = bundle.analysis
    area = 2 * 100 * 10 + 8 * 180
    ix = 100 * 200**3 / 12 - 92 * 180**3 / 12
    iy = 2 * 10 * 100**3 / 12 + 180 * 8**3 / 12
    assert report["cross_section"]["area_mm2"] == pytest.approx(area)
    assert report["cross_section"]["second_moment_x_mm4"] == pytest.approx(ix)
    assert report["cross_section"]["second_moment_y_mm4"] == pytest.approx(iy)
    displacement = report["structural_screen"]["cantilever_tip_displacement_mm"]
    assert displacement["x"] == pytest.approx(100 * 1_000**3 / (3 * 200_000 * iy))
    assert displacement["y"] == pytest.approx(1_000 * 1_000**3 / (3 * 200_000 * ix))
    assert len(report["structural_screen"]["ideal_cantilever_bending_frequencies_hz"]) == 2


def test_l_bracket_calculates_unsymmetric_centroid_product_and_principal_inertia() -> None:
    report = build_complex_shape(
        _request(
            "l_bracket",
            {"width_mm": 50, "height_mm": 80, "thickness_mm": 5, "length_mm": 300},
            {
                "source": "Declared unit-test values.",
                "elastic_modulus_mpa": 70_000,
                "tip_force_x_n": 100,
                "tip_force_y_n": 200,
            },
        )
    ).analysis
    centroid = report["cross_section"]["centroid_xy_mm"]
    assert centroid[0] < 0
    assert centroid[1] < 0
    assert report["cross_section"]["product_moment_xy_mm4"] < 0
    principal = report["cross_section"]["principal_second_moments_mm4"]
    assert 0 < principal[0] < principal[1]
    displacement = report["structural_screen"]["cantilever_tip_displacement_mm"]
    assert displacement["x"] != pytest.approx(0)
    assert displacement["y"] != pytest.approx(0)


def test_perforated_plate_generates_every_hole_and_exact_net_properties() -> None:
    bundle = build_complex_shape(
        _request(
            "perforated_plate",
            {
                "width_mm": 120,
                "height_mm": 80,
                "thickness_mm": 4,
                "hole_diameter_mm": 10,
                "columns": 4,
                "rows": 3,
                "edge_margin_mm": 15,
            },
            {"source": "Declared unit-test density.", "density_kg_m3": 2_700},
        )
    )
    report = bundle.analysis
    assert report["geometry"]["hole_count"] == 12
    assert len([node for node in bundle.program.nodes if node.role == "void"]) == 12
    net_area = 120 * 80 - 12 * math.pi * 5**2
    assert report["face_section"]["net_area_mm2"] == pytest.approx(net_area)
    assert report["geometry"]["volume_mm3"] == pytest.approx(net_area * 4)
    assert report["mass_properties"]["mass_kg"] == pytest.approx(2_700 * net_area * 4e-9)
    assert report["structural_screen"] is None


def test_complex_shapes_fail_closed_on_unsupported_or_ambiguous_analysis() -> None:
    with pytest.raises(ValueError, match="smaller"):
        build_complex_shape(_request("hollow_shaft", {"outer_diameter_mm": 10, "inner_diameter_mm": 10, "length_mm": 100}))
    with pytest.raises(ValueError, match="overlaps"):
        build_complex_shape(
            _request(
                "perforated_plate",
                {
                    "width_mm": 40,
                    "height_mm": 40,
                    "thickness_mm": 4,
                    "hole_diameter_mm": 15,
                    "columns": 3,
                    "rows": 3,
                    "edge_margin_mm": 8,
                },
            )
        )
    with pytest.raises(ValueError, match="geometric and mass analysis only"):
        build_complex_shape(
            _request(
                "perforated_plate",
                {
                    "width_mm": 100,
                    "height_mm": 100,
                    "thickness_mm": 4,
                    "hole_diameter_mm": 10,
                    "columns": 2,
                    "rows": 2,
                    "edge_margin_mm": 20,
                },
                {"source": "No boundary condition was supplied.", "tip_force_y_n": 100},
            )
        )
    with pytest.raises(ValueError, match="only hollow_shaft"):
        build_complex_shape(
            _request(
                "i_beam",
                {"width_mm": 100, "height_mm": 200, "flange_thickness_mm": 10, "web_thickness_mm": 8, "length_mm": 500},
                {"source": "Declared torque.", "torque_n_mm": 100},
            )
        )


def test_complex_shape_hashes_are_deterministic_and_catalog_is_complete() -> None:
    request = _request("l_bracket", {"width_mm": 50, "height_mm": 80, "thickness_mm": 5, "length_mm": 300})
    first = build_complex_shape(request)
    second = build_complex_shape(request)
    assert first.program.to_dict() == second.program.to_dict()
    assert first.analysis == second.analysis
    assert {item["name"] for item in complex_shape_catalog()["shapes"]} == {
        "hollow_shaft",
        "i_beam",
        "l_bracket",
        "perforated_plate",
    }


def test_complex_shape_cli_publishes_atomic_reparseable_bundle(tmp_path, capsys) -> None:
    source = tmp_path / "request.json"
    output = tmp_path / "bundle"
    source.write_text(
        json.dumps(
            _request(
                "i_beam",
                {"width_mm": 100, "height_mm": 200, "flange_thickness_mm": 10, "web_thickness_mm": 8, "length_mm": 500},
                {"source": "Declared CLI test values.", "density_kg_m3": 7_850},
            )
        ),
        encoding="utf-8",
    )
    args = build_parser().parse_args(["complex-shape", str(source), "--output-dir", str(output)])
    assert args.func(args) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["shape"] == "i_beam"
    assert {path.name for path in output.iterdir()} == {
        "analysis.json",
        "manifest.json",
        "request.json",
        "shape.ncad.json",
        "shape.scad",
    }
    assert parse_ir_json((output / "shape.ncad.json").read_text(encoding="utf-8")).metadata["shape"] == "i_beam"
    assert "union()" in (output / "shape.scad").read_text(encoding="utf-8")
    assert len(json.loads((output / "manifest.json").read_text(encoding="utf-8"))["manifest_sha256"]) == 64
    with pytest.raises(FileExistsError, match="already exists"):
        args.func(args)


def test_complex_shape_cli_lists_catalog(capsys) -> None:
    args = build_parser().parse_args(["complex-shape", "--list"])
    assert args.func(args) == 0
    assert json.loads(capsys.readouterr().out)["schema_version"] == "neurocad-complex-shape-catalog-v1"
