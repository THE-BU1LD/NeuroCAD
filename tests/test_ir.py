from __future__ import annotations

import json
import math
import random

import pytest

from core.ir import CADProgram, Constraint, Node, Primitive, Transform, program_bounds, validate_program
from core.ir_adapter import design_graph_to_ir
from core.ir_export import program_to_scad
from core.ir_parser import IRParseError, parse_ir_json, serialize_ir_json
from core.program_evaluation import evaluate_program
from core.prompt_engine import generate_design


def _box_program(*, constraints: tuple[Constraint, ...] = ()) -> CADProgram:
    return CADProgram(
        title="test box",
        nodes=(Node("body", primitive=Primitive("box", {"size": [20.0, 10.0, 4.0]})),),
        roots=("body",),
        constraints=constraints,
        metadata={"fixture": True},
    )


def test_ir_json_round_trip_is_exact_and_deterministic() -> None:
    program = _box_program(constraints=(Constraint("dimension", target="body", parameters={"parameter": "size", "value": [20, 10, 4]}),))
    first = serialize_ir_json(program)
    parsed = parse_ir_json(first)
    second = serialize_ir_json(parsed)
    assert first == second
    assert parsed.to_dict() == program.to_dict()


def test_static_evaluation_is_not_reported_as_kernel_geometric_validity() -> None:
    structural = evaluate_program(_box_program())
    assert structural.structural_validity is True
    assert structural.geometric_validity is None
    assert structural.kernel_validity is None
    assert structural.topology_correct is None

    kernel = evaluate_program(
        _box_program(),
        mesh_measurements={
            "kernel_validity": True,
            "watertight": True,
            "winding_consistent": True,
            "finite_vertices": True,
            "is_volume": True,
            "body_count": 1,
        },
    )
    assert kernel.structural_validity is True
    assert kernel.geometric_validity is True
    assert kernel.kernel_validity is True
    assert kernel.topology_correct is True


def test_compact_serialization_is_stable() -> None:
    program = _box_program()
    assert serialize_ir_json(program, pretty=False) == serialize_ir_json(parse_ir_json(serialize_ir_json(program)), pretty=False)


def test_hierarchical_difference_exports_real_boolean_program() -> None:
    program = CADProgram(
        title="plate with hole",
        nodes=(
            Node("plate", primitive=Primitive("box", {"size": [40, 30, 3]})),
            Node("hole", primitive=Primitive("cylinder", {"radius": 2, "height": 5})),
            Node("cut", composition="difference", children=("plate", "hole"), role="composition"),
        ),
        roots=("cut",),
    )
    report = validate_program(program)
    assert report.valid
    scad = program_to_scad(program)
    assert "difference()" in scad
    assert "cube(size=[40, 30, 3]" in scad
    assert "cylinder(r=2, h=5" in scad


def test_transform_and_bounds_are_computed_for_rotated_geometry() -> None:
    program = CADProgram(
        title="rotated box",
        nodes=(Node("body", primitive=Primitive("box", {"size": [20, 10, 4]}), transform=Transform((5, 0, 0), (0, 0, 90))),),
        roots=("body",),
    )
    minimum, maximum = program_bounds(program)
    assert minimum == pytest.approx((0, -10, -2))
    assert maximum == pytest.approx((10, 10, 2))


def test_constraints_are_evaluated_and_fail_closed() -> None:
    valid = _box_program(constraints=(Constraint("dimension", target="body", parameters={"parameter": "size", "value": [20, 10, 4]}),))
    invalid = _box_program(constraints=(Constraint("dimension", target="body", parameters={"parameter": "size", "value": [21, 10, 4]}),))
    assert validate_program(valid).valid
    report = validate_program(invalid)
    assert not report.valid
    assert report.constraint_results[0]["message"] == "dimension mismatch"


def test_offset_and_child_count_constraints_reference_nodes() -> None:
    program = CADProgram(
        title="references",
        nodes=(
            Node("left", primitive=Primitive("sphere", {"radius": 2})),
            Node("right", primitive=Primitive("sphere", {"radius": 2}), transform=Transform((10, 0, 0))),
            Node("pair", composition="union", children=("left", "right")),
        ),
        roots=("pair",),
        constraints=(
            Constraint("offset", target="right", reference="left", parameters={"vector": [10, 0, 0]}),
            Constraint("child_count", target="pair", parameters={"value": 2}),
        ),
    )
    assert validate_program(program).valid


def test_missing_reference_and_cycle_are_reported() -> None:
    missing = CADProgram("missing", (Node("group", composition="union", children=("absent",)),), ("group",))
    assert "missing_reference" in {error.code for error in validate_program(missing).errors}
    cycle = CADProgram(
        "cycle",
        (
            Node("a", composition="union", children=("b",)),
            Node("b", composition="union", children=("a",)),
        ),
        ("a",),
    )
    assert "cycle" in {error.code for error in validate_program(cycle).errors}


@pytest.mark.parametrize(
    "text, expected",
    [
        ("{", "line 1, column 2"),
        ("[]", "root must be a JSON object"),
        (json.dumps({"version": "wrong"}), "$.version"),
    ],
)
def test_malformed_ir_has_useful_parse_errors(text: str, expected: str) -> None:
    with pytest.raises(IRParseError, match=expected.replace("$", r"\$")):
        parse_ir_json(text)


def test_schema_rejects_unknown_fields() -> None:
    value = _box_program().to_dict()
    value["unexpected"] = True
    with pytest.raises(IRParseError, match="unexpected"):
        parse_ir_json(json.dumps(value))


def test_natural_language_design_round_trips_through_canonical_ir() -> None:
    design = generate_design("a 120 x 80 x 4 mm plate with four 4 mm holes")
    program = design_graph_to_ir(design)
    encoded = serialize_ir_json(program)
    recovered = parse_ir_json(encoded)
    assert recovered.to_dict() == program.to_dict()
    assert recovered.metadata["source"] == "natural_language_design_graph"
    assert "difference()" in program_to_scad(recovered)


def test_non_finite_dimensions_and_metadata_fail_closed() -> None:
    non_finite = CADProgram(
        "not finite",
        (Node("body", primitive=Primitive("box", {"size": [math.nan, 10, 4]})),),
        ("body",),
    )
    metadata = CADProgram(
        "bad metadata",
        (Node("body", primitive=Primitive("box", {"size": [20, 10, 4]})),),
        ("body",),
        metadata={"not_json": {1, 2}},
    )
    assert "invalid_parameter" in {issue.code for issue in validate_program(non_finite).errors}
    assert "invalid_metadata" in {issue.code for issue in validate_program(metadata).errors}


def test_malformed_python_api_values_return_reports_instead_of_crashing() -> None:
    bad_transform = CADProgram(
        "bad transform",
        (Node("body", primitive=Primitive("box", {"size": [20, 10, 4]}), transform=Transform(("bad", 0, 0))),),  # type: ignore[arg-type]
        ("body",),
    )
    bad_tolerance = _box_program(
        constraints=(Constraint("dimension", target="body", parameters={"parameter": "size", "value": [20, 10, 4]}, tolerance="bad"),)  # type: ignore[arg-type]
    )
    bad_offset = CADProgram(
        "bad offset",
        (
            Node("left", primitive=Primitive("sphere", {"radius": 2})),
            Node("right", primitive=Primitive("sphere", {"radius": 2})),
            Node("pair", composition="union", children=("left", "right")),
        ),
        ("pair",),
        constraints=(Constraint("offset", target="right", reference="left", parameters={"vector": ["bad", 0, 0]}),),
    )
    assert not validate_program(bad_transform).valid
    assert not validate_program(bad_tolerance).valid
    assert not validate_program(bad_offset).valid


def test_deep_hierarchy_is_bounded_without_recursion_error() -> None:
    nodes = [Node("leaf", primitive=Primitive("box", {"size": [1, 1, 1]}))]
    child = "leaf"
    for index in range(1000):
        node_id = f"group_{index}"
        nodes.append(Node(node_id, composition="union", children=(child,)))
        child = node_id
    report = validate_program(CADProgram("deep", tuple(nodes), (child,)))
    assert not report.valid
    assert "hierarchy_too_deep" in {issue.code for issue in report.errors}


def test_non_overlapping_intersection_is_geometrically_invalid() -> None:
    program = CADProgram(
        "empty intersection",
        (
            Node("left", primitive=Primitive("box", {"size": [2, 2, 2]}), transform=Transform((-10, 0, 0))),
            Node("right", primitive=Primitive("box", {"size": [2, 2, 2]}), transform=Transform((10, 0, 0))),
            Node("overlap", composition="intersection", children=("left", "right")),
        ),
        ("overlap",),
    )
    report = validate_program(program)
    assert not report.valid
    assert "empty_intersection" in {issue.code for issue in report.errors}


def test_json_rejects_non_standard_nan_constant() -> None:
    text = serialize_ir_json(_box_program()).replace("20.0", "NaN", 1)
    with pytest.raises(IRParseError, match="non-standard numeric constant NaN"):
        parse_ir_json(text)


def test_json_rejects_duplicate_keys_and_excessive_nesting() -> None:
    encoded = serialize_ir_json(_box_program(), pretty=False)
    duplicate = encoded.replace('"title":"test box"', '"title":"first","title":"second"')
    with pytest.raises(IRParseError, match="duplicate object key 'title'"):
        parse_ir_json(duplicate)

    with pytest.raises(IRParseError, match="nesting exceeds"):
        parse_ir_json("[" * 300 + "]" * 300)

    quoted_brackets = serialize_ir_json(_box_program(), pretty=False).replace(
        '"fixture":true',
        '"fixture":"' + "[" * 300 + '"',
    )
    assert parse_ir_json(quoted_brackets).metadata["fixture"] == "[" * 300


def test_direct_ir_rejects_noncanonical_payloads_before_serialization() -> None:
    unexpected_primitive_parameter = CADProgram(
        "unexpected primitive payload",
        (Node("body", primitive=Primitive("sphere", {"radius": 2, "ignored": math.inf})),),
        ("body",),
    )
    non_string_metadata_key = CADProgram(
        "non-string metadata key",
        (Node("body", primitive=Primitive("sphere", {"radius": 2})),),
        ("body",),
        metadata={1: "ambiguous after JSON serialization"},  # type: ignore[dict-item]
    )
    huge_integer = CADProgram(
        "huge integer",
        (Node("body", primitive=Primitive("sphere", {"radius": 10**1000})),),
        ("body",),
    )

    assert "invalid_parameter" in {issue.code for issue in validate_program(unexpected_primitive_parameter).errors}
    assert "invalid_metadata" in {issue.code for issue in validate_program(non_string_metadata_key).errors}
    assert "invalid_parameter" in {issue.code for issue in validate_program(huge_integer).errors}
    for program in (unexpected_primitive_parameter, non_string_metadata_key, huge_integer):
        with pytest.raises(IRParseError):
            serialize_ir_json(program)


@pytest.mark.parametrize(
    "constraint, expected_message",
    [
        (
            Constraint("dimension", target="body", reference="body", parameters={"parameter": "size", "value": [20, 10, 4]}),
            "does not accept a reference",
        ),
        (
            Constraint("dimension", target="body", parameters={"parameter": "size", "value": [20, 10, 4], "ignored": True}),
            "unexpected ignored",
        ),
        (
            Constraint("dimension", target="body", parameters={"parameter": "size", "value": [20, math.inf, 4]}),
            "non-finite",
        ),
        (
            Constraint("bounds", target="body", parameters={"min": [1, 0, 0], "max": [-1, 1, 1]}),
            "min cannot exceed max",
        ),
    ],
)
def test_constraint_payloads_are_exact_finite_and_unambiguous(constraint: Constraint, expected_message: str) -> None:
    report = validate_program(_box_program(constraints=(constraint,)))
    assert not report.valid
    assert expected_message in str(report.constraint_results[0]["message"])


def test_malformed_program_collections_return_a_report() -> None:
    program = CADProgram(
        "malformed collections",
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
    )
    report = validate_program(program)
    assert not report.valid
    assert {"invalid_nodes", "invalid_constraints", "invalid_roots"} <= {issue.code for issue in report.errors}


def test_malformed_primitive_and_empty_intersection_do_not_crash() -> None:
    malformed = CADProgram(
        "malformed primitive",
        (Node("body", primitive="not-a-primitive"),),  # type: ignore[arg-type]
        ("body",),
    )
    empty = CADProgram(
        "empty intersection",
        (Node("empty", composition="intersection", children=()),),
        ("empty",),
    )
    assert not validate_program(malformed).valid
    assert not validate_program(empty).valid


def test_deterministic_malformed_python_ir_fuzz_is_total() -> None:
    rng = random.Random(20260902)
    odd: list[object] = [None, True, -1, 0, 1, math.nan, math.inf, "x", [], {}, [1, 2], [1, 2, 3], (1, 2, 3)]
    parameter_names = ["size", "radius", "height", "r1", "r2", "major_radius", "minor_radius"]
    for _ in range(250):
        parameters = {rng.choice(parameter_names): rng.choice(odd) for _ in range(rng.randrange(1, 5))}
        primitive = Primitive(rng.choice(["box", "rounded_box", "sphere", "cylinder", "cone", "torus", "bad"]), parameters)
        transform = Transform(rng.choice(odd), rng.choice(odd), rng.choice(odd))  # type: ignore[arg-type]
        constraint = Constraint(
            rng.choice(["dimension", "coincident", "offset", "child_count", "bounds", "bad"]),
            target=rng.choice(["body", "missing", None]),
            reference=rng.choice(["body", "missing", None]),
            parameters=rng.choice(odd),  # type: ignore[arg-type]
            tolerance=rng.choice(odd),  # type: ignore[arg-type]
        )
        program = CADProgram(
            rng.choice(["fuzz", "", None, 4]),  # type: ignore[arg-type]
            (Node("body", primitive=primitive, transform=transform),),
            ("body",),
            (constraint,),
        )
        assert isinstance(validate_program(program).valid, bool)
