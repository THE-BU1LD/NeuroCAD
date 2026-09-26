from __future__ import annotations

import json

from core.feature_ir import Feature, FeatureProgram, serialize_feature_ir_json
from neurocad_cli import build_parser


def _write_program(tmp_path):
    program = FeatureProgram(
        title="CLI box",
        parameters=(),
        features=(Feature(id="body", kind="primitive_box", parameters={"size": [20.0, 10.0, 5.0]}),),
        outputs=("body",),
        metadata={"test": "feature-cli"},
    )
    path = tmp_path / "box.ncad2.json"
    path.write_text(serialize_feature_ir_json(program), encoding="utf-8")
    return path


def test_feature_validate_cli_reports_feature_contract(tmp_path, capsys) -> None:
    source = _write_program(tmp_path)
    args = build_parser().parse_args(["feature", "validate", str(source)])
    assert args.func(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
    assert payload["version"] == "neurocad-feature-ir-v0alpha1"
    assert payload["feature_count"] == 1
    assert payload["outputs"] == ["body"]


def test_feature_backends_cli_is_discovery_only(capsys) -> None:
    args = build_parser().parse_args(["feature", "backends"])
    assert args.func(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["api"] == "neurocad-feature-backends-v1"
    assert payload["geometry_built"] is False
    assert {item["backend"]["id"] for item in payload["backends"]} == {"build123d", "cadquery"}
