"""Regression for actual timing names found in the retained compiler result."""
from __future__ import annotations

from copy import deepcopy

from core.research_suite import DETERMINISTIC_RESULTS_VERSION, _deterministic_copy, _timing_measurements


def test_all_edit_and_hierarchy_timings_are_metadata_not_outcomes():
    original = {
        "edit": {"successful_parameter_edits": 200, "mean_edit_validate_export_ms": 1.31},
        "hierarchy": [{"depth": 128, "valid": True, "validate_export_ms": 36.3},
                      {"depth": 129, "valid": False, "validate_export_ms": 3.6}],
    }
    slower = deepcopy(original)
    slower["edit"]["mean_edit_validate_export_ms"] = 9000.0
    for row in slower["hierarchy"]:
        row["validate_export_ms"] *= 1000
    assert _deterministic_copy(original) == _deterministic_copy(slower) == {
        "edit": {"successful_parameter_edits": 200},
        "hierarchy": [{"depth": 128, "valid": True}, {"depth": 129, "valid": False}],
    }
    assert _timing_measurements(original) == {
        "$.edit.mean_edit_validate_export_ms": 1.31,
        "$.hierarchy[0].validate_export_ms": 36.3,
        "$.hierarchy[1].validate_export_ms": 3.6,
    }
    assert _timing_measurements(original) != _timing_measurements(slower)
    assert DETERMINISTIC_RESULTS_VERSION == "neurocad-deterministic-results-v2"
    slower["hierarchy"][0]["valid"] = False
    assert _deterministic_copy(original) != _deterministic_copy(slower)


def test_timing_extraction_preserves_physical_quantities_and_timeout_policy():
    data = {"response_time_ms": 2.0, "openscad_timeout_seconds": 120, "passed": False}
    assert _deterministic_copy(data) == data
    assert _timing_measurements(data) == {}
