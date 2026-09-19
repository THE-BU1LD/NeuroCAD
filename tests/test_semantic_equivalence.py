from __future__ import annotations

from dataclasses import replace

from core.ir import CADProgram, Constraint, Node, Primitive, Transform
from core.semantic_equivalence import (
    program_semantic_form,
    program_semantic_sha256,
    programs_semantically_equivalent,
)


def _box(identifier: str = "body", *, size: float = 10.0) -> CADProgram:
    return CADProgram(
        "box",
        (Node(identifier, Primitive("box", {"size": [size, size, size]})),),
        (identifier,),
        constraints=(
            Constraint(
                "dimension",
                target=identifier,
                parameters={"parameter": "size", "value": [size, size, size]},
            ),
        ),
    )


def test_semantic_form_ignores_titles_identifiers_and_node_order() -> None:
    first = CADProgram(
        "first title",
        (
            Node("a", Primitive("box", {"size": [20, 20, 20]})),
            Node("b", Primitive("sphere", {"radius": 3}), transform=Transform(translate=(2, 0, 0))),
            Node("root", composition="union", children=("a", "b"), role="composition"),
        ),
        ("root",),
        metadata={"producer": "one"},
    )
    second = CADProgram(
        "other title",
        (
            Node("combined", composition="union", children=("round", "solid"), role="composition"),
            Node("round", Primitive("sphere", {"radius": 3.0}), transform=Transform(translate=(2.0, 0, 0))),
            Node("solid", Primitive("box", {"size": [20.0, 20, 20]})),
        ),
        ("combined",),
        metadata={"producer": "two"},
    )
    assert programs_semantically_equivalent(first, second)
    assert program_semantic_sha256(first) == program_semantic_sha256(second)


def test_semantic_form_rejects_same_extents_with_wrong_feature_structure() -> None:
    solid = _box()
    hollow = CADProgram(
        "same outer extents",
        (
            Node("outer", Primitive("box", {"size": [10, 10, 10]})),
            Node("void", Primitive("box", {"size": [8, 8, 8]})),
            Node("shell", composition="difference", children=("outer", "void"), role="composition"),
        ),
        ("shell",),
    )
    assert not programs_semantically_equivalent(solid, hollow)


def test_semantic_form_includes_transforms_constraints_and_numeric_tolerance() -> None:
    original = _box("original")
    renamed = _box("renamed", size=10.0 + 1e-10)
    moved = CADProgram(
        "box",
        (Node("body", Primitive("box", {"size": [10, 10, 10]}), transform=Transform(translate=(1, 0, 0))),),
        ("body",),
        constraints=(
            Constraint(
                "dimension",
                target="body",
                parameters={"parameter": "size", "value": [10, 10, 10]},
            ),
        ),
    )
    assert programs_semantically_equivalent(original, renamed, tolerance=1e-8)
    assert not programs_semantically_equivalent(original, renamed, tolerance=0)
    assert not programs_semantically_equivalent(original, moved)


def test_semantic_hash_normalizes_signed_zero() -> None:
    positive = _box()
    positive = replace(positive, constraints=(replace(positive.constraints[0], tolerance=0.0),))
    negative = replace(positive, constraints=(replace(positive.constraints[0], tolerance=-0.0),))
    assert programs_semantically_equivalent(positive, negative, tolerance=0)
    assert program_semantic_sha256(positive) == program_semantic_sha256(negative)


def test_semantic_form_rejects_invalid_programs_and_tolerance() -> None:
    invalid = CADProgram("invalid", (), ())
    try:
        program_semantic_form(invalid)
    except ValueError as exc:
        assert "invalid CAD program" in str(exc)
    else:
        raise AssertionError("invalid program unexpectedly produced a semantic form")
    try:
        programs_semantically_equivalent(_box(), _box(), tolerance=-1)
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("negative tolerance unexpectedly accepted")
