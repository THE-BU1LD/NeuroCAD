from __future__ import annotations

import hashlib
import json

from neurocad_cli import build_parser, build_verification_report


def test_structural_verification_report_is_bounded_and_deterministic():
    prompt = "a compact box with two holes"

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
            "30mm",
            "box",
            "with",
            "four",
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
