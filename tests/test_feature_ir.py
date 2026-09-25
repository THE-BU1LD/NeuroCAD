from __future__ import annotations

import pytest

from core.feature_ir import (
    DesignParameter,
    EntitySelector,
    Feature,
    FeatureIRParseError,
    FeatureProgram,
    parse_feature_ir_json,
    serialize_feature_ir_json,
    validate_feature_program,
)


def _box_program() -> FeatureProgram:
    return FeatureProgram(
        title="exact box",
        parameters=(DesignParameter("width", 40.0, lower=1.0, upper=1000.0),),
        features=(
            Feature(
                id="body",
                kind="primitive_box",
                parameters={"size": [40.0, 30.0, 20.0]},
                role="body",
            ),
        ),
        outputs=("body",),
        metadata={"purpose": "feature-ir-smoke"},
    )


def test_feature_ir_accepts_bounded_primitive_program() -> None:
    report = validate_feature_program(_box_program())
    assert report.valid
    assert report.errors == ()


def test_feature_ir_json_round_trip_is_stable() -> None:
    program = _box_program()
    encoded = serialize_feature_ir_json(program)
    decoded = parse_feature_ir_json(encoded)
    assert decoded == program
    assert serialize_feature_ir_json(decoded) == encoded


def test_feature_ir_rejects_forward_feature_references() -> None:
    program = FeatureProgram(
        title="bad order",
        parameters=(),
        features=(
            Feature(
                id="rounded",
                kind="fillet",
                inputs=("body",),
                parameters={"radius": 2.0},
                selectors=(
                    EntitySelector(
                        entity="edge",
                        generated_by="body",
                        predicates=({"kind": "parallel_to", "axis": [0, 0, 1]},),
                    ),
                ),
            ),
            Feature(id="body", kind="primitive_box", parameters={"size": [20.0, 20.0, 10.0]}),
        ),
        outputs=("rounded",),
    )
    report = validate_feature_program(program)
    assert not report.valid
    assert any(issue.code == "forward_or_missing_reference" for issue in report.errors)


def test_feature_ir_rejects_raw_kernel_index_selectors() -> None:
    program = FeatureProgram(
        title="unstable selector",
        parameters=(),
        features=(
            Feature(id="body", kind="primitive_box", parameters={"size": [20.0, 20.0, 10.0]}),
            Feature(
                id="rounded",
                kind="fillet",
                inputs=("body",),
                parameters={"radius": 2.0},
                selectors=(
                    EntitySelector(
                        entity="edge",
                        generated_by="body",
                        predicates=({"kind": "edge_index", "index": 7},),
                    ),
                ),
            ),
        ),
        outputs=("rounded",),
    )
    report = validate_feature_program(program)
    assert not report.valid
    assert any(issue.code == "unstable_selector" for issue in report.errors)


def test_feature_ir_accepts_semantic_edge_selector() -> None:
    program = FeatureProgram(
        title="semantic selector",
        parameters=(),
        features=(
            Feature(id="body", kind="primitive_box", parameters={"size": [20.0, 20.0, 10.0]}),
            Feature(
                id="rounded",
                kind="fillet",
                inputs=("body",),
                parameters={"radius": 2.0},
                selectors=(
                    EntitySelector(
                        entity="edge",
                        generated_by="body",
                        role="outer_vertical_edge",
                        predicates=(
                            {"kind": "parallel_to", "axis": [0, 0, 1]},
                            {"kind": "near_bbox_corner", "corner": "x+y+"},
                        ),
                    ),
                ),
            ),
        ),
        outputs=("rounded",),
    )
    assert validate_feature_program(program).valid


def test_feature_ir_rejects_nonfinite_parameter() -> None:
    program = FeatureProgram(
        title="bad number",
        parameters=(DesignParameter("width", float("nan")),),
        features=(Feature(id="body", kind="primitive_box", parameters={"size": [20.0, 20.0, 10.0]}),),
        outputs=("body",),
    )
    report = validate_feature_program(program)
    assert not report.valid
    assert any(issue.code == "invalid_value" for issue in report.errors)


def test_feature_ir_parse_fails_closed_on_unknown_keys() -> None:
    encoded = serialize_feature_ir_json(_box_program())
    mutated = encoded.replace('"metadata": {', '"unexpected": true,\n  "metadata": {', 1)
    with pytest.raises(FeatureIRParseError, match="unsupported keys"):
        parse_feature_ir_json(mutated)


def test_feature_ir_rejects_missing_output() -> None:
    program = FeatureProgram(
        title="no output",
        parameters=(),
        features=(Feature(id="body", kind="primitive_box", parameters={"size": [20.0, 20.0, 10.0]}),),
        outputs=(),
    )
    report = validate_feature_program(program)
    assert not report.valid
    assert any(issue.code == "missing_output" for issue in report.errors)
