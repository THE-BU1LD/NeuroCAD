from __future__ import annotations

import json
import math

import pytest

from core.calibration import (
    CALIBRATION_LIMITATIONS,
    AxisObservation,
    CalibrationDataset,
    ClearanceObservation,
    HoleObservation,
    apply_calibrated_clearance,
    fit_calibration_profile,
    parse_calibration_dataset,
    parse_calibration_profile,
    plan_calibration_application,
    recommend_clearance,
    serialize_calibration_dataset,
    serialize_calibration_profile,
    validate_calibration_dataset,
)
from core.enclosure import EnclosureSpec, LidSpec
from core.manufacturing import fabrication_preflight
from core.project import EnclosureProject


def _dataset(*, outlier: bool = False) -> CalibrationDataset:
    factors = {"x": 0.98, "y": 1.02, "z": 0.995}
    axes: list[AxisObservation] = []
    for axis, factor in factors.items():
        for index, nominal in enumerate((20.0, 40.0, 80.0), start=1):
            measured = nominal / factor
            if outlier and axis == "x" and index == 3:
                measured = nominal / 0.8
            axes.append(AxisObservation(f"axis-{axis}-{index}", axis, nominal, measured, f"run-{(index % 2) + 1}"))
    holes = (
        HoleObservation("hole-1", "vertical", 3.0, 2.8, "run-1"),
        HoleObservation("hole-2", "vertical", 5.0, 4.8, "run-2"),
        HoleObservation("hole-3", "horizontal", 8.0, 7.8 if not outlier else 6.0, "run-1"),
    )
    clearances = (
        ClearanceObservation("fit-1", 0.10, False, "run-1"),
        ClearanceObservation("fit-2", 0.20, False, "run-2"),
        ClearanceObservation("fit-3", 0.30, True, "run-1"),
        ClearanceObservation("fit-4", 0.40, True, "run-2"),
        ClearanceObservation("fit-5", 0.45, not outlier, "run-1"),
        ClearanceObservation("fit-6", 0.50, True, "run-2"),
    )
    return CalibrationDataset(
        profile_id="mk4-pla-standard",
        printer="Prusa MK4",
        material="PLA lot A",
        process="0.20 mm structural profile",
        nozzle_diameter_mm=0.4,
        measurement_resolution_mm=0.01,
        axis_observations=tuple(axes),
        hole_observations=holes,
        clearance_observations=clearances,
    )


def test_exact_synthetic_scale_and_hole_recovery() -> None:
    profile = fit_calibration_profile(_dataset())
    assert profile.xy_scale.x.value == pytest.approx(0.98)
    assert profile.xy_scale.y.value == pytest.approx(1.02)
    assert profile.xy_scale.combined_xy.value == pytest.approx(1.0)
    assert profile.z_scale.value == pytest.approx(0.995)
    assert profile.hole_diameter_compensation_mm.value == pytest.approx(0.2)
    assert profile.clearance.threshold_mm == pytest.approx(0.25)
    assert profile.clearance.recommended_clearance_mm == pytest.approx(0.30)
    assert profile.clearance.classification_errors == 0
    assert profile.xy_scale.x.evidence_count == 3
    assert profile.xy_scale.x.run_count == 2
    assert profile.xy_scale.x.dispersion >= profile.xy_scale.x.resolution_floor > 0
    assert profile.limitations == CALIBRATION_LIMITATIONS


def test_medians_and_threshold_resist_single_outliers_deterministically() -> None:
    first = fit_calibration_profile(_dataset(outlier=True))
    second = fit_calibration_profile(_dataset(outlier=True))
    assert first == second
    assert first.xy_scale.x.value == pytest.approx(0.98)
    assert first.hole_diameter_compensation_mm.value == pytest.approx(0.2)
    assert first.clearance.threshold_mm == pytest.approx(0.25)
    assert first.clearance.recommended_clearance_mm == pytest.approx(0.30)
    assert first.clearance.classification_errors == 1


def test_insufficient_and_invalid_evidence_fails_closed() -> None:
    base = _dataset()
    insufficient = CalibrationDataset(
        base.profile_id,
        base.printer,
        base.material,
        base.process,
        base.nozzle_diameter_mm,
        base.measurement_resolution_mm,
        base.axis_observations[:-1],
        base.hole_observations,
        base.clearance_observations,
    )
    with pytest.raises(ValueError, match="z-axis observations"):
        validate_calibration_dataset(insufficient)

    duplicate = CalibrationDataset(
        base.profile_id,
        base.printer,
        base.material,
        base.process,
        base.nozzle_diameter_mm,
        base.measurement_resolution_mm,
        base.axis_observations + (base.axis_observations[0],),
        base.hole_observations,
        base.clearance_observations,
    )
    with pytest.raises(ValueError, match="duplicate observation_id"):
        validate_calibration_dataset(duplicate)

    non_finite = CalibrationDataset(
        base.profile_id,
        base.printer,
        base.material,
        base.process,
        math.nan,
        base.measurement_resolution_mm,
        base.axis_observations,
        base.hole_observations,
        base.clearance_observations,
    )
    with pytest.raises(ValueError, match="finite number"):
        validate_calibration_dataset(non_finite)

    only_success = tuple(
        ClearanceObservation(f"s-{index}", index / 10, True, f"run-{(index % 2) + 1}")
        for index in range(1, 5)
    )
    with pytest.raises(ValueError, match="successful and two failed"):
        recommend_clearance(only_success)

    contradictory = tuple(
        ClearanceObservation(
            f"mixed-{index}",
            index / 10,
            index % 2 == 0,
            f"run-{(index % 2) + 1}",
        )
        for index in range(1, 7)
    )
    with pytest.raises(ValueError, match="too contradictory"):
        recommend_clearance(contradictory)


def test_strict_json_roundtrip_recomputes_and_rejects_tampering() -> None:
    dataset_encoded = serialize_calibration_dataset(_dataset(outlier=True))
    assert parse_calibration_dataset(dataset_encoded) == _dataset(outlier=True)
    profile = fit_calibration_profile(_dataset(outlier=True))
    encoded = serialize_calibration_profile(profile)
    assert parse_calibration_profile(encoded) == profile
    assert serialize_calibration_profile(parse_calibration_profile(encoded)) == encoded

    decoded = json.loads(encoded)
    decoded["recommendations"]["z_scale"]["value"] = 123.0
    with pytest.raises(ValueError, match="do not match"):
        parse_calibration_profile(json.dumps(decoded))

    duplicate_key = encoded.replace('"schema_version": "neurocad-calibration-v1"', '"schema_version": "x", "schema_version": "y"')
    with pytest.raises(ValueError, match="duplicate object key"):
        parse_calibration_profile(duplicate_key)


def test_serialized_output_is_order_independent_and_rejects_unknown_fields() -> None:
    base = _dataset(outlier=True)
    reordered = CalibrationDataset(
        base.profile_id,
        base.printer,
        base.material,
        base.process,
        base.nozzle_diameter_mm,
        base.measurement_resolution_mm,
        tuple(reversed(base.axis_observations)),
        tuple(reversed(base.hole_observations)),
        tuple(reversed(base.clearance_observations)),
    )
    first = fit_calibration_profile(base)
    second = fit_calibration_profile(reordered)
    assert first.xy_scale == second.xy_scale
    assert first.z_scale == second.z_scale
    assert first.hole_diameter_compensation_mm == second.hole_diameter_compensation_mm
    assert first.clearance == second.clearance
    assert serialize_calibration_profile(first) == serialize_calibration_profile(second)

    decoded = json.loads(serialize_calibration_profile(first))
    decoded["dataset"]["unvalidated"] = True
    with pytest.raises(ValueError, match="unsupported keys: unvalidated"):
        parse_calibration_profile(json.dumps(decoded))


def test_calibration_application_is_explicit_and_only_edits_clearance() -> None:
    profile = fit_calibration_profile(_dataset())
    project = EnclosureProject(
        "calibrated-case",
        EnclosureSpec(
            outer_size_mm=(80, 60, 30),
            wall_mm=2,
            profile="fdm_standard",
            lid=LidSpec("friction", 2.5, 0.1, lip_height_mm=2),
        ),
    )
    plan = plan_calibration_application(project, profile)
    assert plan.automatically_applied is False
    assert plan.suggested_project_edits == (
        {
            "field": "lid.clearance_mm",
            "before": 0.1,
            "after": 0.3,
            "basis": "smallest observed successful clearance in the bounded coupon evidence",
        },
    )
    assert plan.slicer_scale_recommendations == {"x": pytest.approx(0.98), "y": pytest.approx(1.02), "z": pytest.approx(0.995)}
    edited = apply_calibrated_clearance(project, profile)
    assert edited.spec.lid.clearance_mm == pytest.approx(0.3)
    assert edited.revision == 2
    assert edited.spec.outer_size_mm == project.spec.outer_size_mm
    preflight = fabrication_preflight(project.spec, calibration_profile=profile)
    assert not preflight.valid
    assert "calibrated_lid_clearance" in {finding.code for finding in preflight.findings}
    calibrated_preflight = fabrication_preflight(edited.spec, calibration_profile=profile)
    assert calibrated_preflight.valid
