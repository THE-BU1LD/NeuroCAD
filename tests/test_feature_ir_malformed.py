"""Admission regressions for untrusted feature-history data.

These are authored software counterexamples, not external scientific tasks.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

import pytest

from core.feature_ir import (
    DesignParameter,
    EntitySelector,
    Feature,
    FeatureIRParseError,
    FeatureProgram,
    feature_program_from_dict,
    parse_feature_ir_json,
    serialize_feature_ir_json,
    validate_feature_program,
)


def _program() -> FeatureProgram:
    return FeatureProgram(
        title="parameterized box with semantic fillet",
        parameters=(DesignParameter("width", 40.0, lower=10.0, upper=100.0),),
        features=(
            Feature("body", "primitive_box", parameters={"size": [{"parameter": "width"}, 30.0, 20.0]}),
            Feature(
                "rounded",
                "fillet",
                inputs=("body",),
                parameters={"radius": 2.0},
                selectors=(EntitySelector("edge", "body", ({"kind": "parallel_to", "axis": [0, 0, 1]},)),),
            ),
        ),
        outputs=("rounded",),
    )


_STRING_FIELDS = [
    ("parameters", 0, "id"),
    ("parameters", 0, "unit"),
    ("parameters", 0, "role"),
    ("features", 0, "id"),
    ("features", 0, "kind"),
    ("features", 1, "inputs", 0),
    ("features", 1, "selectors", 0, "entity"),
    ("features", 1, "selectors", 0, "generated_by"),
    ("outputs", 0),
]


@pytest.mark.parametrize("path", _STRING_FIELDS)
@pytest.mark.parametrize("value", [[], {}, False, 1, None])
def test_json_nonstrings_fail_with_structured_parse_error(path: tuple[Any, ...], value: Any) -> None:
    raw = _program().to_dict()
    target = raw
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(FeatureIRParseError) as captured:
        parse_feature_ir_json(json.dumps(raw))
    expected_path = "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in path)
    assert any(expected_path in error for error in captured.value.errors)


@pytest.mark.parametrize("value", [[], {}, False, 1, None])
def test_operation_rejects_nonstring_values_without_typeerror(value: Any) -> None:
    raw = FeatureProgram(
        title="extruded sketch",
        parameters=(),
        features=(
            Feature("profile", "sketch", parameters={"plane": "XY", "entities": [], "constraints": []}),
            Feature("body", "extrude", inputs=("profile",), parameters={"distance": 10, "operation": value}),
        ),
        outputs=("body",),
    ).to_dict()
    with pytest.raises(FeatureIRParseError, match=r"parameters\.operation"):
        feature_program_from_dict(raw)


_NULL_CONTRACTS = [
    ("datum_plane", {"origin": [0, 0, 0], "normal": [0, 0, 1], "x_axis": [1, 0, 0]}),
    ("datum_axis", {"origin": [0, 0, 0], "direction": [0, 0, 1]}),
    ("primitive_box", {"size": [40, 30, 20]}),
    ("primitive_cylinder", {"radius": 10, "height": 20}),
    ("sketch", {"plane": "XY", "entities": [], "constraints": []}),
    ("extrude", {"distance": 10, "operation": "new"}),
    ("revolve", {"angle_deg": 180, "operation": "new"}),
    ("fillet", {"radius": 2}),
    ("chamfer", {"distance": 2}),
    ("linear_pattern", {"count": 3, "spacing": 10, "direction": [1, 0, 0]}),
    ("circular_pattern", {"count": 3, "angle_deg": 360, "axis": [0, 0, 1]}),
    ("mirror", {"plane": "XY"}),
]


@pytest.mark.parametrize("kind,parameters", _NULL_CONTRACTS)
def test_required_feature_parameters_never_accept_explicit_null(kind: str, parameters: dict[str, Any]) -> None:
    for name in parameters:
        values = dict(parameters, **{name: None})
        feature = Feature(
            "operation",
            kind,
            inputs=("body",),
            parameters=values,
            selectors=(EntitySelector("edge", "body"),),
        )
        program = replace(_program(), features=(_program().features[0], feature), outputs=("operation",))
        report = validate_feature_program(program)
        assert not report.valid, (kind, name)
        assert any(issue.path == f"$.features[1].parameters.{name}" for issue in report.errors), (kind, name)


@pytest.mark.parametrize(
    "field,value",
    [("parameters", None), ("features", {}), ("outputs", "body"), ("metadata", [])],
)
def test_direct_program_construction_rejects_invalid_container_types(field: str, value: Any) -> None:
    report = validate_feature_program(replace(_program(), **{field: value}))
    assert not report.valid
    assert any(issue.path == f"$.{field}" for issue in report.errors)


@pytest.mark.parametrize("field", ["parameters", "features"])
def test_direct_program_construction_rejects_nonrecord_members(field: str) -> None:
    report = validate_feature_program(replace(_program(), **{field: ({},)}))
    assert not report.valid
    assert any(issue.path == f"$.{field}[0]" for issue in report.errors)


@pytest.mark.parametrize("field,value", [("inputs", None), ("parameters", []), ("selectors", None)])
def test_direct_feature_construction_rejects_invalid_container_types(field: str, value: Any) -> None:
    broken = replace(_program().features[0], **{field: value})
    report = validate_feature_program(replace(_program(), features=(broken,)))
    assert not report.valid
    assert any(issue.path == f"$.features[0].{field}" for issue in report.errors)


def test_direct_selector_construction_rejects_invalid_predicate_container() -> None:
    selector = replace(_program().features[1].selectors[0], predicates=None)
    feature = replace(_program().features[1], selectors=(selector,))
    report = validate_feature_program(replace(_program(), features=(_program().features[0], feature)))
    assert not report.valid
    assert any(issue.path == "$.features[1].selectors[0].predicates" for issue in report.errors)


def test_dict_parser_rejects_nonstring_object_keys() -> None:
    raw = _program().to_dict()
    raw[7] = "unexpected numeric key"
    with pytest.raises(FeatureIRParseError, match="keys must be strings"):
        feature_program_from_dict(raw)


def test_valid_parameter_references_and_optional_nulls_preserve_roundtrip() -> None:
    program = _program()
    # Null selector role and optional parameter bounds are intentional, unlike
    # mandatory operation parameters. Preserve their values without coercion.
    program = replace(program, parameters=(DesignParameter("width", 40.0),))
    encoded = serialize_feature_ir_json(program)
    assert parse_feature_ir_json(encoded) == program
    assert serialize_feature_ir_json(parse_feature_ir_json(encoded)) == encoded
