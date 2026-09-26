"""Count distinct feature-history entries, never repeated binding references."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.feature_ir import Feature, FeatureProgram
from core.requirement_ir import Requirement, RequirementIR, RequirementValue
from core.requirement_verification import (
    ExactRequirementBinding,
    RequirementBindingSet,
    feature_ir_sha256,
    requirement_ir_sha256,
    verify_exact_requirements,
)


@dataclass(frozen=True)
class Inspection:
    valid_brep: bool = True
    solid_count: int = 1
    volume_mm3: float = 24000.0
    extents_mm: tuple[float, float, float] = (40.0, 30.0, 20.0)


@pytest.mark.parametrize(
    ("bound_ids", "expected", "satisfied", "distinct_present"),
    [
        (("body",), 1, True, 1),
        (("body", "tool"), 2, True, 2),
        (("body", "body"), 2, False, 1),
        (("body", "body"), 1, False, 1),
        (("body", "tool", "tool"), 3, False, 2),
        (("body", "missing"), 2, False, 1),
        ((), 0, True, 0),
        ((), 1, False, 0),
    ],
)
def test_feature_history_count_requires_distinct_existing_ids(
    bound_ids: tuple[str, ...],
    expected: int,
    satisfied: bool,
    distinct_present: int,
) -> None:
    source = "Keep the declared feature count."
    program = FeatureProgram(
        title="feature-count contract",
        parameters=(),
        features=(
            Feature(id="body", kind="primitive_box", parameters={"size": [40.0, 30.0, 20.0]}),
            Feature(id="tool", kind="primitive_cylinder", parameters={"radius": 2.0, "height": 20.0}),
        ),
        outputs=("body",),
    )
    document = RequirementIR(
        source=source,
        requirements=(
            Requirement(
                id="count",
                kind="other",
                strength="must",
                target="feature_history",
                source_start=0,
                source_end=len(source),
                source_text=source,
                provenance="explicit",
                verification="feature_count",
                value=RequirementValue(float(expected), "unitless"),
            ),
        ),
    )
    bindings = RequirementBindingSet(
        requirement_ir_sha256=requirement_ir_sha256(document),
        feature_ir_sha256=feature_ir_sha256(program),
        bindings=(
            ExactRequirementBinding(
                "count", bound_ids, "feature_count", {"kind": "feature_count"}
            ),
        ),
    )
    result = verify_exact_requirements(document, program, Inspection(), bindings)
    assert result.errors == ()
    assert result.satisfied_for_all_must is satisfied
    assert len(result.checks) == 1
    assert result.checks[0].actual == distinct_present
    assert result.checks[0].satisfied is satisfied
    assert result.checks[0].basis == "feature_history_count"
