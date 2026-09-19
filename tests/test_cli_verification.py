from __future__ import annotations

import hashlib
import json

import pytest

from neurocad_cli import build_parser, build_verification_report, main


def test_structural_verification_report_is_bounded_and_deterministic():
    prompt = "a 120 x 80 x 4 mm plate with four 4 mm holes"

    first = build_verification_report(prompt)
    second = build_verification_report(prompt)

    assert first == second
    assert first["schema_version"] == 1
    assert first["status"] == "valid"
    assert first["verification_scope"] == "structural_generation_only"
    assert "does not establish manufacturability" in first["claim_boundary"]
    assert first["design"]["component_count"] > 0
    assert len(first["artifact"]["sha256"]) == 64
    assert all(check["passed"] for check in first["checks"])


def test_verify_command_writes_matching_json_and_scad(tmp_path):
    report_path = tmp_path / "verification.json"
    scad_path = tmp_path / "design.scad"
    parser = build_parser()
    args = parser.parse_args(
        [
            "verify",
            "a",
            "120mm",
            "x",
            "80mm",
            "x",
            "4mm",
            "plate",
            "with",
            "four",
            "4mm",
            "holes",
            "--json-output",
            str(report_path),
            "--scad-output",
            str(scad_path),
        ]
    )

    assert args.func(args) == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    scad = scad_path.read_text(encoding="utf-8")

    assert report["status"] == "valid"
    assert report["artifact"]["sha256"] == hashlib.sha256(scad.encode("utf-8")).hexdigest()
    assert report["artifact"]["character_count"] == len(scad)
    assert report["design"]["component_count"] >= 1


def test_structural_report_rejects_underspecified_prompts():
    report = build_verification_report("a compact box with two holes")
    assert report["status"] == "invalid"
    assert not next(c for c in report["checks"] if c["name"] == "supported_validated_program")["passed"]


def test_verify_refuses_colliding_output_paths(tmp_path):
    import pytest
    path = str(tmp_path / "same.json")
    args = build_parser().parse_args(["verify", "a 10 x 20 x 3 mm plate", "--json-output", path, "--scad-output", path])
    with pytest.raises(ValueError, match="distinct"):
        args.func(args)


def test_invalid_verify_does_not_write_scad(tmp_path):
    path = tmp_path / "invalid.scad"
    args = build_parser().parse_args(["verify", "a compact box", "--scad-output", str(path)])
    assert args.func(args) == 1
    assert not path.exists()


def test_quadratic_tolerance_cli_reports_versioned_nonlinear_model(tmp_path, capsys):
    source = tmp_path / "quadratic-tolerance.json"
    source.write_text(
        json.dumps(
            {
                "model": "quadratic",
                "nominal_clearance_mm": 1.0,
                "contributions": [
                    {"name": "nonlinear axis", "mean_mm": 0.0, "sigma_mm": 2.0, "worst_case_mm": 3.0}
                ],
                "sensitivities": [0.0],
                "hessian_per_mm": [[1.0]],
            }
        ),
        encoding="utf-8",
    )
    args = build_parser().parse_args(["tolerance", str(source)])
    assert args.func(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == "neurocad-tolerance-v2"
    assert report["model"] == "quadratic"
    assert report["probability_model"] == "moment_matched_normal_for_quadratic_form"
    assert report["result"]["mean_clearance_mm"] == 3.0


def test_top_level_nlp_command_prints_auditable_human_analysis(capsys):
    prompt = (
        "Design an enclosure 10 x 7 x 3 cm with walls 2 mm and an FDM standard profile "
        "and an open top and a rectangular cutout 12 x 7 mm on the back face at center"
    )
    args = build_parser().parse_args(["nlp", prompt])
    assert args.func(args) == 0
    output = capsys.readouterr().out
    assert "NeuroCAD language analysis" in output
    assert "Resolved specification" in output
    assert "100 x 70 x 30 mm" in output
    assert "cutout.rectangular" in output


def test_math_beam_command_has_human_and_json_views(capsys):
    arguments = [
        "math",
        "beam",
        "--force",
        "10",
        "--length",
        "50",
        "--width",
        "10",
        "--thickness",
        "4",
        "--modulus",
        "2200",
        "--yield-strength",
        "45",
    ]
    human = build_parser().parse_args(arguments)
    assert human.func(human) == 0
    assert "NeuroCAD beam analysis" in capsys.readouterr().out

    machine = build_parser().parse_args([*arguments, "--json"])
    assert machine.func(machine) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "neurocad-cantilever-v1"
    assert payload["result"]["maximum_stress_mpa"] > 0


def test_main_suggests_close_command_names(capsys):
    with pytest.raises(SystemExit, match="2"):
        main(["valdiate"])
    assert "did you mean 'validate'" in capsys.readouterr().err
