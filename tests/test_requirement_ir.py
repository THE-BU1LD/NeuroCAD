from __future__ import annotations

from core.requirement_ir import (
    Requirement,
    RequirementBinding,
    RequirementIR,
    RequirementIRParseError,
    RequirementValue,
    parse_requirement_ir_json,
    requirement_coverage,
    serialize_requirement_ir_json,
    validate_requirement_ir,
)


SOURCE = "Make a plate 80 mm wide with four mounting holes and keep it lightweight."


def _req(
    requirement_id: str,
    phrase: str,
    *,
    kind: str,
    target: str,
    strength: str = "must",
    provenance: str = "explicit",
    verification: str,
    value: RequirementValue | None = None,
) -> Requirement:
    start = SOURCE.index(phrase)
    return Requirement(
        id=requirement_id,
        kind=kind,
        strength=strength,
        target=target,
        source_start=start,
        source_end=start + len(phrase),
        source_text=phrase,
        provenance=provenance,
        verification=verification,
        value=value,
    )


def test_requirement_ir_preserves_source_spans_and_build_readiness() -> None:
    document = RequirementIR(
        source=SOURCE,
        requirements=(
            _req(
                "width",
                "80 mm wide",
                kind="dimension",
                target="plate.width",
                verification="exact_dimension",
                value=RequirementValue(80.0, "mm", tolerance=0.01),
            ),
            _req(
                "holes",
                "four mounting holes",
                kind="count",
                target="mounting_holes",
                verification="feature_count",
                value=RequirementValue(4.0, "unitless"),
            ),
            _req(
                "mass_pref",
                "lightweight",
                kind="preference",
                target="mass",
                strength="preference",
                verification="analytical_model",
            ),
        ),
    )
    report = validate_requirement_ir(document)
    assert report.structurally_valid
    assert report.build_ready
    assert report.errors == ()
    assert report.blockers == ()


def test_requirement_ir_blocks_unresolved_must() -> None:
    requirement = _req(
        "material",
        "lightweight",
        kind="material",
        target="material",
        provenance="unresolved",
        verification="human_review",
    )
    report = validate_requirement_ir(RequirementIR(source=SOURCE, requirements=(requirement,)))
    assert report.structurally_valid
    assert not report.build_ready
    assert any(issue.code == "unresolved_must" for issue in report.blockers)


def test_requirement_ir_blocks_unsupported_must_verification() -> None:
    requirement = _req(
        "mass",
        "lightweight",
        kind="performance",
        target="mass",
        verification="unsupported",
    )
    report = validate_requirement_ir(RequirementIR(source=SOURCE, requirements=(requirement,)))
    assert report.structurally_valid
    assert not report.build_ready
    assert any(issue.code == "unsupported_must" for issue in report.blockers)


def test_requirement_ir_rejects_source_span_drift() -> None:
    requirement = Requirement(
        id="width",
        kind="dimension",
        strength="must",
        target="plate.width",
        source_start=SOURCE.index("80 mm wide"),
        source_end=SOURCE.index("80 mm wide") + len("80 mm wide"),
        source_text="81 mm wide",
        provenance="explicit",
        verification="exact_dimension",
        value=RequirementValue(80.0, "mm"),
    )
    report = validate_requirement_ir(RequirementIR(source=SOURCE, requirements=(requirement,)))
    assert not report.structurally_valid
    assert any(issue.code == "source_span_mismatch" for issue in report.errors)


def test_requirement_coverage_requires_every_must() -> None:
    width = _req(
        "width",
        "80 mm wide",
        kind="dimension",
        target="plate.width",
        verification="exact_dimension",
        value=RequirementValue(80.0, "mm"),
    )
    holes = _req(
        "holes",
        "four mounting holes",
        kind="count",
        target="mounting_holes",
        verification="feature_count",
        value=RequirementValue(4.0, "unitless"),
    )
    document = RequirementIR(source=SOURCE, requirements=(width, holes))
    incomplete = requirement_coverage(
        document,
        (RequirementBinding("width", ("plate",), "exact_dimension"),),
        known_feature_ids=("plate", "holes"),
    )
    assert not incomplete.complete_for_must
    assert incomplete.missing_must == ("holes",)

    complete = requirement_coverage(
        document,
        (
            RequirementBinding("width", ("plate",), "exact_dimension"),
            RequirementBinding("holes", ("holes",), "feature_count"),
        ),
        known_feature_ids=("plate", "holes"),
    )
    assert complete.complete_for_must
    assert complete.missing_must == ()


def test_requirement_coverage_rejects_unknown_feature_and_method_drift() -> None:
    width = _req(
        "width",
        "80 mm wide",
        kind="dimension",
        target="plate.width",
        verification="exact_dimension",
        value=RequirementValue(80.0, "mm"),
    )
    document = RequirementIR(source=SOURCE, requirements=(width,))
    report = requirement_coverage(
        document,
        (RequirementBinding("width", ("invented",), "feature_presence"),),
        known_feature_ids=("plate",),
    )
    assert not report.complete_for_must
    assert any(issue.code == "verification_mismatch" for issue in report.invalid_bindings)


def test_requirement_ir_json_roundtrip_is_deterministic() -> None:
    document = RequirementIR(
        source=SOURCE,
        requirements=(
            _req(
                "width",
                "80 mm wide",
                kind="dimension",
                target="plate.width",
                verification="exact_dimension",
                value=RequirementValue(80.0, "mm", tolerance=0.01),
            ),
        ),
        metadata={"domain": "mechanical"},
    )
    encoded = serialize_requirement_ir_json(document)
    decoded = parse_requirement_ir_json(encoded)
    assert decoded == document
    assert serialize_requirement_ir_json(decoded) == encoded


def test_requirement_ir_json_fails_closed_on_unknown_keys() -> None:
    document = RequirementIR(
        source=SOURCE,
        requirements=(
            _req(
                "width",
                "80 mm wide",
                kind="dimension",
                target="plate.width",
                verification="exact_dimension",
                value=RequirementValue(80.0, "mm"),
            ),
        ),
    )
    encoded = serialize_requirement_ir_json(document)
    mutated = encoded.replace('"metadata": {', '"unexpected": true,\n  "metadata": {', 1)
    try:
        parse_requirement_ir_json(mutated)
    except RequirementIRParseError as exc:
        assert "unsupported keys" in str(exc)
    else:
        raise AssertionError("unknown Requirement IR keys must fail closed")


def test_requirement_ir_rejects_nonfinite_metadata() -> None:
    document = RequirementIR(source=SOURCE, requirements=(), metadata={"score": float("nan")})
    report = validate_requirement_ir(document)
    assert not report.structurally_valid
    assert any(issue.code == "invalid_metadata" for issue in report.errors)
