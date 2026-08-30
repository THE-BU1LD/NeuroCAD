import json
from pathlib import Path

import pytest
import trimesh

from research.vericodegen.verifier import verify_mesh


ROOT = Path(__file__).resolve().parents[1]


def test_known_box_passes_predeclared_hard_constraints():
    box = trimesh.creation.box(extents=(2.0, 4.0, 6.0))

    report = verify_mesh(
        box,
        {
            "watertight": True,
            "max_components": 1,
            "volume": {"min": 47.9, "max": 48.1},
            "extents": {
                "x": {"min": 1.99, "max": 2.01},
                "y": {"min": 3.99, "max": 4.01},
                "z": {"min": 5.99, "max": 6.01},
            },
            "bounds": {
                "min": [-1.01, -2.01, -3.01],
                "max": [1.01, 2.01, 3.01],
            },
        },
    )

    assert report.passed is True
    assert report.failures == ()
    assert report.measurements["component_count"] == 1
    assert report.measurements["volume"] == pytest.approx(48.0)


def test_dimension_violation_fails_closed():
    box = trimesh.creation.box(extents=(2.0, 4.0, 6.0))

    report = verify_mesh(
        box,
        {"extents": {"x": {"min": 2.5}}},
    )

    assert report.passed is False
    assert any("extent.x" in failure for failure in report.failures)


def test_disconnected_fixture_is_rejected_when_one_component_is_required():
    first = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    second = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    second.apply_translation((3.0, 0.0, 0.0))
    disconnected = trimesh.util.concatenate([first, second])

    report = verify_mesh(disconnected, {"max_components": 1})

    assert report.passed is False
    assert report.measurements["component_count"] == 2
    assert any("component_count=2" in failure for failure in report.failures)


def test_unknown_constraint_is_never_silently_ignored():
    box = trimesh.creation.box()

    with pytest.raises(ValueError, match="unsupported hard constraints"):
        verify_mesh(box, {"semantic_quality": {"min": 0.9}})


def test_frozen_benchmark_schema_declares_primary_fields_and_supported_constraints():
    schema = json.loads(
        (ROOT / "research" / "vericodegen" / "benchmark_schema.json").read_text()
    )

    required = set(schema["required"])
    assert {
        "prompt_id",
        "prompt_text",
        "task_family",
        "hard_constraints",
        "semantic_rubric",
    } <= required

    hard_properties = set(schema["properties"]["hard_constraints"]["properties"])
    assert hard_properties == {
        "watertight",
        "max_components",
        "volume",
        "extents",
        "bounds",
    }
    assert schema["properties"]["hard_constraints"]["additionalProperties"] is False
