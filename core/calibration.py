"""Evidence-bounded calibration recommendations for additive manufacturing.

The calculations in this module summarize measurements from a printed coupon.
They do not model thermal history, anisotropy, wear, slicer behavior, or changes
between printers, materials, settings, and environments.  A fitted profile is a
recommendation for the explicitly named setup, not a physical guarantee or a
safety certification.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from itertools import pairwise
from statistics import median
from typing import TYPE_CHECKING, Any, Literal

from core.json_io import strict_json_loads

if TYPE_CHECKING:
    from .project import EnclosureProject

CALIBRATION_SCHEMA_VERSION = "neurocad-calibration-v1"
CALIBRATION_METHOD_VERSION = "robust-coupon-fit-v2"
MAX_CALIBRATION_JSON_BYTES = 1_048_576
MIN_AXIS_OBSERVATIONS = 3
MIN_HOLE_OBSERVATIONS = 3
MIN_CLEARANCE_OBSERVATIONS_PER_OUTCOME = 2
CALIBRATION_LIMITATIONS = (
    "Recommendations apply only to the recorded printer, material, nozzle, and process label.",
    "Coupon measurements do not establish structural strength, dimensional stability, or safety.",
    "Recalibration is required after material, hardware, slicer, process, or environmental changes.",
    "Clearance is inferred from observed pass/fail coupons and does not guarantee fit for other geometry.",
    "The hole recommendation pools orientations; inspect its dispersion or calibrate orientation-specific behavior separately.",
    "Reported dispersion is a descriptive MAD-based heuristic with an instrument-resolution floor, not a confidence interval.",
    "Run identifiers expose repeated-run structure but do not prove observations are statistically independent.",
)

Axis = Literal["x", "y", "z"]
HoleOrientation = Literal["vertical", "horizontal"]


def _finite_number(value: object, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be a finite number")
    if not minimum <= converted <= maximum:
        raise ValueError(f"{name} must be between {minimum:g} and {maximum:g}")
    return converted


def _identifier(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError(f"{name} must be a non-empty string of at most 128 characters")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{name} must not contain control characters")
    return value.strip()


def _require_keys(value: object, required: set[str], *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be an object")
    keys = set(value)
    missing = sorted(required - keys)
    extra = sorted(keys - required)
    if missing:
        raise ValueError(f"{context} is missing keys: {', '.join(missing)}")
    if extra:
        raise ValueError(f"{context} has unsupported keys: {', '.join(extra)}")
    return value


@dataclass(frozen=True)
class AxisObservation:
    """One external dimension measured along a named machine axis."""

    observation_id: str
    axis: Axis
    nominal_mm: float
    measured_mm: float
    run_id: str

    def to_dict(self) -> dict[str, str | float]:
        return {
            "observation_id": self.observation_id,
            "axis": self.axis,
            "nominal_mm": self.nominal_mm,
            "measured_mm": self.measured_mm,
            "run_id": self.run_id,
        }


@dataclass(frozen=True)
class HoleObservation:
    """One printed circular-hole diameter measurement."""

    observation_id: str
    orientation: HoleOrientation
    nominal_diameter_mm: float
    measured_diameter_mm: float
    run_id: str

    def to_dict(self) -> dict[str, str | float]:
        return {
            "observation_id": self.observation_id,
            "orientation": self.orientation,
            "nominal_diameter_mm": self.nominal_diameter_mm,
            "measured_diameter_mm": self.measured_diameter_mm,
            "run_id": self.run_id,
        }


@dataclass(frozen=True)
class ClearanceObservation:
    """Pass/fail observation for one diametral or lateral coupon clearance."""

    observation_id: str
    clearance_mm: float
    fit_succeeded: bool
    run_id: str

    def to_dict(self) -> dict[str, str | float | bool]:
        return {
            "observation_id": self.observation_id,
            "clearance_mm": self.clearance_mm,
            "fit_succeeded": self.fit_succeeded,
            "run_id": self.run_id,
        }


@dataclass(frozen=True)
class CalibrationDataset:
    """Immutable observations tied to a specific physical process setup."""

    profile_id: str
    printer: str
    material: str
    process: str
    nozzle_diameter_mm: float
    measurement_resolution_mm: float
    axis_observations: tuple[AxisObservation, ...]
    hole_observations: tuple[HoleObservation, ...]
    clearance_observations: tuple[ClearanceObservation, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "printer": self.printer,
            "material": self.material,
            "process": self.process,
            "nozzle_diameter_mm": self.nozzle_diameter_mm,
            "measurement_resolution_mm": self.measurement_resolution_mm,
            "axis_observations": [item.to_dict() for item in self.axis_observations],
            "hole_observations": [item.to_dict() for item in self.hole_observations],
            "clearance_observations": [item.to_dict() for item in self.clearance_observations],
        }


@dataclass(frozen=True)
class RobustEstimate:
    """Median estimate with descriptive scaled-MAD and resolution floor."""

    value: float
    dispersion: float
    resolution_floor: float
    evidence_count: int
    run_count: int
    observed_min: float
    observed_max: float
    method: str

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "value": self.value,
            "dispersion": self.dispersion,
            "resolution_floor": self.resolution_floor,
            "evidence_count": self.evidence_count,
            "run_count": self.run_count,
            "observed_min": self.observed_min,
            "observed_max": self.observed_max,
            "method": self.method,
        }


@dataclass(frozen=True)
class XYScaleRecommendation:
    x: RobustEstimate
    y: RobustEstimate
    combined_xy: RobustEstimate

    def to_dict(self) -> dict[str, object]:
        return {"x": self.x.to_dict(), "y": self.y.to_dict(), "combined_xy": self.combined_xy.to_dict()}


@dataclass(frozen=True)
class ClearanceRecommendation:
    """Observed transition estimate; recommendation is the successful bracket edge."""

    threshold_mm: float
    recommended_clearance_mm: float
    bracket_half_width_mm: float
    evidence_count: int
    run_count: int
    failure_count: int
    success_count: int
    classification_errors: int
    observed_failure_edge_mm: float
    observed_success_edge_mm: float
    method: str

    def to_dict(self) -> dict[str, float | int | str]:
        return {
            "threshold_mm": self.threshold_mm,
            "recommended_clearance_mm": self.recommended_clearance_mm,
            "bracket_half_width_mm": self.bracket_half_width_mm,
            "evidence_count": self.evidence_count,
            "run_count": self.run_count,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "classification_errors": self.classification_errors,
            "observed_failure_edge_mm": self.observed_failure_edge_mm,
            "observed_success_edge_mm": self.observed_success_edge_mm,
            "method": self.method,
        }


@dataclass(frozen=True)
class CalibrationProfile:
    """Versioned observations plus reproducible derived recommendations."""

    dataset: CalibrationDataset
    xy_scale: XYScaleRecommendation
    z_scale: RobustEstimate
    hole_diameter_compensation_mm: RobustEstimate
    clearance: ClearanceRecommendation
    schema_version: str = CALIBRATION_SCHEMA_VERSION
    method_version: str = CALIBRATION_METHOD_VERSION
    limitations: tuple[str, ...] = CALIBRATION_LIMITATIONS

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "method_version": self.method_version,
            "dataset": self.dataset.to_dict(),
            "recommendations": {
                "xy_scale": self.xy_scale.to_dict(),
                "z_scale": self.z_scale.to_dict(),
                "hole_diameter_compensation_mm": self.hole_diameter_compensation_mm.to_dict(),
                "clearance": self.clearance.to_dict(),
            },
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class CalibrationApplicationPlan:
    """Explicit split between safe CAD edits and external slicer actions."""

    profile_id: str
    project_revision: int
    suggested_project_edits: tuple[dict[str, object], ...]
    slicer_scale_recommendations: dict[str, float]
    modeled_hole_compensation_recommendation_mm: float
    automatically_applied: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "project_revision": self.project_revision,
            "suggested_project_edits": [dict(item) for item in self.suggested_project_edits],
            "slicer_scale_recommendations": dict(self.slicer_scale_recommendations),
            "modeled_hole_compensation_recommendation_mm": self.modeled_hole_compensation_recommendation_mm,
            "automatically_applied": self.automatically_applied,
            "limitations": [
                "XY/Z scale recommendations belong in a reviewed slicer profile and do not mutate nominal CAD dimensions.",
                "Hole compensation is reported but not silently applied to nominal feature dimensions.",
                "Only a friction-lid clearance increase can be applied as an audited project revision.",
            ],
        }


def validate_calibration_dataset(dataset: CalibrationDataset) -> None:
    """Validate bounds, types, uniqueness, and minimum evidence; fail closed."""

    _identifier(dataset.profile_id, "profile_id")
    _identifier(dataset.printer, "printer")
    _identifier(dataset.material, "material")
    _identifier(dataset.process, "process")
    _finite_number(dataset.nozzle_diameter_mm, "nozzle_diameter_mm", 0.1, 2.0)
    _finite_number(dataset.measurement_resolution_mm, "measurement_resolution_mm", 0.001, 1.0)
    if not isinstance(dataset.axis_observations, tuple):
        raise TypeError("axis_observations must be an immutable tuple")
    if not isinstance(dataset.hole_observations, tuple):
        raise TypeError("hole_observations must be an immutable tuple")
    if not isinstance(dataset.clearance_observations, tuple):
        raise TypeError("clearance_observations must be an immutable tuple")

    identifiers: set[str] = set()
    measurement_keys: set[tuple[object, ...]] = set()
    axis_counts = {"x": 0, "y": 0, "z": 0}
    axis_runs: dict[str, set[str]] = {"x": set(), "y": set(), "z": set()}
    for index, axis_observation in enumerate(dataset.axis_observations):
        if not isinstance(axis_observation, AxisObservation):
            raise TypeError(f"axis_observations[{index}] must be an AxisObservation")
        observation_id = _identifier(axis_observation.observation_id, f"axis_observations[{index}].observation_id")
        if observation_id in identifiers:
            raise ValueError(f"duplicate observation_id: {observation_id}")
        identifiers.add(observation_id)
        run_id = _identifier(axis_observation.run_id, f"axis_observations[{index}].run_id")
        if axis_observation.axis not in axis_counts:
            raise ValueError(f"axis_observations[{index}].axis must be x, y, or z")
        nominal = _finite_number(axis_observation.nominal_mm, f"axis_observations[{index}].nominal_mm", 1.0, 1000.0)
        measured = _finite_number(axis_observation.measured_mm, f"axis_observations[{index}].measured_mm", 0.5, 1500.0)
        ratio = measured / nominal
        if not 0.5 <= ratio <= 1.5:
            raise ValueError(f"axis_observations[{index}] measured/nominal ratio must be between 0.5 and 1.5")
        axis_key = ("axis", run_id, axis_observation.axis, nominal, measured)
        if axis_key in measurement_keys:
            raise ValueError("duplicate axis measurement cannot increase evidence count")
        measurement_keys.add(axis_key)
        axis_counts[axis_observation.axis] += 1
        axis_runs[axis_observation.axis].add(run_id)

    for axis, count in axis_counts.items():
        if count < MIN_AXIS_OBSERVATIONS:
            raise ValueError(f"at least {MIN_AXIS_OBSERVATIONS} {axis}-axis observations are required")
        if len(axis_runs[axis]) < 2:
            raise ValueError(f"{axis}-axis observations must span at least two declared coupon runs")

    hole_runs: set[str] = set()
    for index, hole_observation in enumerate(dataset.hole_observations):
        if not isinstance(hole_observation, HoleObservation):
            raise TypeError(f"hole_observations[{index}] must be a HoleObservation")
        observation_id = _identifier(hole_observation.observation_id, f"hole_observations[{index}].observation_id")
        if observation_id in identifiers:
            raise ValueError(f"duplicate observation_id: {observation_id}")
        identifiers.add(observation_id)
        hole_runs.add(_identifier(hole_observation.run_id, f"hole_observations[{index}].run_id"))
        if hole_observation.orientation not in {"vertical", "horizontal"}:
            raise ValueError(f"hole_observations[{index}].orientation must be vertical or horizontal")
        nominal = _finite_number(
            hole_observation.nominal_diameter_mm,
            f"hole_observations[{index}].nominal_diameter_mm",
            0.2,
            100.0,
        )
        measured = _finite_number(
            hole_observation.measured_diameter_mm,
            f"hole_observations[{index}].measured_diameter_mm",
            0.1,
            150.0,
        )
        if not 0.25 <= measured / nominal <= 2.0:
            raise ValueError(f"hole_observations[{index}] measured/nominal ratio must be between 0.25 and 2")
        hole_key = ("hole", hole_observation.run_id, hole_observation.orientation, nominal, measured)
        if hole_key in measurement_keys:
            raise ValueError("duplicate hole measurement cannot increase evidence count")
        measurement_keys.add(hole_key)
    if len(dataset.hole_observations) < MIN_HOLE_OBSERVATIONS:
        raise ValueError(f"at least {MIN_HOLE_OBSERVATIONS} hole observations are required")
    if len(hole_runs) < 2:
        raise ValueError("hole observations must span at least two declared coupon runs")

    clearance_values: set[tuple[str, float]] = set()
    outcome_counts = {False: 0, True: 0}
    clearance_runs: set[str] = set()
    for index, clearance_observation in enumerate(dataset.clearance_observations):
        if not isinstance(clearance_observation, ClearanceObservation):
            raise TypeError(f"clearance_observations[{index}] must be a ClearanceObservation")
        observation_id = _identifier(
            clearance_observation.observation_id,
            f"clearance_observations[{index}].observation_id",
        )
        if observation_id in identifiers:
            raise ValueError(f"duplicate observation_id: {observation_id}")
        identifiers.add(observation_id)
        clearance_runs.add(
            _identifier(clearance_observation.run_id, f"clearance_observations[{index}].run_id")
        )
        clearance = _finite_number(
            clearance_observation.clearance_mm,
            f"clearance_observations[{index}].clearance_mm",
            0.0,
            5.0,
        )
        if not isinstance(clearance_observation.fit_succeeded, bool):
            raise TypeError(f"clearance_observations[{index}].fit_succeeded must be a boolean")
        clearance_key = (clearance_observation.run_id, clearance)
        if clearance_key in clearance_values:
            raise ValueError("a coupon run cannot repeat the same clearance value")
        clearance_values.add(clearance_key)
        outcome_counts[clearance_observation.fit_succeeded] += 1
    for outcome, label in ((False, "failed"), (True, "successful")):
        if outcome_counts[outcome] < MIN_CLEARANCE_OBSERVATIONS_PER_OUTCOME:
            raise ValueError(
                f"at least {MIN_CLEARANCE_OBSERVATIONS_PER_OUTCOME} {label} clearance observations are required"
            )
    if len(clearance_runs) < 2:
        raise ValueError("clearance observations must span at least two declared coupon runs")


def _robust_estimate(
    values: tuple[float, ...],
    run_ids: tuple[str, ...],
    resolution_floor: float,
    method: str,
) -> RobustEstimate:
    center = float(median(values))
    absolute_deviations = tuple(abs(value - center) for value in values)
    scaled_mad = 1.4826 * float(median(absolute_deviations))
    dispersion = max(scaled_mad, resolution_floor)
    return RobustEstimate(
        center,
        dispersion,
        resolution_floor,
        len(values),
        len(set(run_ids)),
        min(values),
        max(values),
        method,
    )


def _validated_axis_corrections(
    observations: tuple[AxisObservation, ...],
) -> dict[str, tuple[tuple[float, str, float], ...]]:
    if not isinstance(observations, tuple):
        raise TypeError("axis observations must be an immutable tuple")
    values: dict[str, list[tuple[float, str, float]]] = {"x": [], "y": [], "z": []}
    identifiers: set[str] = set()
    measurements: set[tuple[str, str, float, float]] = set()
    for index, observation in enumerate(observations):
        if not isinstance(observation, AxisObservation):
            raise TypeError(f"axis observation {index} must be an AxisObservation")
        observation_id = _identifier(observation.observation_id, f"axis observation {index} id")
        if observation_id in identifiers:
            raise ValueError(f"duplicate observation_id: {observation_id}")
        identifiers.add(observation_id)
        run_id = _identifier(observation.run_id, f"axis observation {index} run_id")
        if observation.axis not in values:
            raise ValueError(f"axis observation {index} axis must be x, y, or z")
        nominal = _finite_number(observation.nominal_mm, f"axis observation {index} nominal_mm", 1.0, 1000.0)
        measured = _finite_number(observation.measured_mm, f"axis observation {index} measured_mm", 0.5, 1500.0)
        if not 0.5 <= measured / nominal <= 1.5:
            raise ValueError(f"axis observation {index} measured/nominal ratio must be between 0.5 and 1.5")
        measurement = (run_id, observation.axis, nominal, measured)
        if measurement in measurements:
            raise ValueError("duplicate axis measurement cannot increase evidence count")
        measurements.add(measurement)
        values[observation.axis].append((nominal / measured, run_id, measured))
    return {axis: tuple(axis_values) for axis, axis_values in values.items()}


def recommend_xy_scale(
    observations: tuple[AxisObservation, ...],
    *,
    measurement_resolution_mm: float,
) -> XYScaleRecommendation:
    """Recommend multiplicative X/Y model scale from nominal/measured ratios."""

    corrections = _validated_axis_corrections(observations)
    resolution = _finite_number(measurement_resolution_mm, "measurement_resolution_mm", 0.001, 1.0)
    x_rows = corrections["x"]
    y_rows = corrections["y"]
    x_values = tuple(row[0] for row in x_rows)
    y_values = tuple(row[0] for row in y_rows)
    if len(x_values) < MIN_AXIS_OBSERVATIONS or len(y_values) < MIN_AXIS_OBSERVATIONS:
        raise ValueError(f"X and Y each require at least {MIN_AXIS_OBSERVATIONS} observations")
    if len({row[1] for row in x_rows}) < 2 or len({row[1] for row in y_rows}) < 2:
        raise ValueError("X and Y observations must each span at least two declared coupon runs")
    method = "median(nominal/measured); dispersion=max(1.4826*MAD, instrument-resolution ratio); descriptive only"
    return XYScaleRecommendation(
        _robust_estimate(
            x_values,
            tuple(row[1] for row in x_rows),
            resolution / float(median(row[2] for row in x_rows)),
            method,
        ),
        _robust_estimate(
            y_values,
            tuple(row[1] for row in y_rows),
            resolution / float(median(row[2] for row in y_rows)),
            method,
        ),
        _robust_estimate(
            x_values + y_values,
            tuple(row[1] for row in x_rows + y_rows),
            resolution / float(median(row[2] for row in x_rows + y_rows)),
            method,
        ),
    )


def recommend_z_scale(
    observations: tuple[AxisObservation, ...],
    *,
    measurement_resolution_mm: float,
) -> RobustEstimate:
    """Recommend multiplicative Z model scale from nominal/measured ratios."""

    rows = _validated_axis_corrections(observations)["z"]
    if len(rows) < MIN_AXIS_OBSERVATIONS:
        raise ValueError(f"Z requires at least {MIN_AXIS_OBSERVATIONS} observations")
    if len({row[1] for row in rows}) < 2:
        raise ValueError("Z observations must span at least two declared coupon runs")
    resolution = _finite_number(measurement_resolution_mm, "measurement_resolution_mm", 0.001, 1.0)
    values = tuple(row[0] for row in rows)
    return _robust_estimate(
        values,
        tuple(row[1] for row in rows),
        resolution / float(median(row[2] for row in rows)),
        "median(nominal/measured); dispersion=max(1.4826*MAD, instrument-resolution ratio); descriptive only",
    )


def recommend_hole_compensation(
    observations: tuple[HoleObservation, ...],
    *,
    measurement_resolution_mm: float,
) -> RobustEstimate:
    """Recommend diameter added to modeled holes; negative values reduce them."""

    if not isinstance(observations, tuple):
        raise TypeError("hole observations must be an immutable tuple")
    if len(observations) < MIN_HOLE_OBSERVATIONS:
        raise ValueError(f"hole compensation requires at least {MIN_HOLE_OBSERVATIONS} observations")
    identifiers: set[str] = set()
    measurements: set[tuple[str, str, float, float]] = set()
    corrections: list[float] = []
    run_ids: list[str] = []
    for index, observation in enumerate(observations):
        if not isinstance(observation, HoleObservation):
            raise TypeError(f"hole observation {index} must be a HoleObservation")
        observation_id = _identifier(observation.observation_id, f"hole observation {index} id")
        if observation_id in identifiers:
            raise ValueError(f"duplicate observation_id: {observation_id}")
        identifiers.add(observation_id)
        run_id = _identifier(observation.run_id, f"hole observation {index} run_id")
        if observation.orientation not in {"vertical", "horizontal"}:
            raise ValueError(f"hole observation {index} orientation must be vertical or horizontal")
        nominal = _finite_number(observation.nominal_diameter_mm, f"hole observation {index} nominal", 0.2, 100.0)
        measured = _finite_number(observation.measured_diameter_mm, f"hole observation {index} measured", 0.1, 150.0)
        if not 0.25 <= measured / nominal <= 2.0:
            raise ValueError(f"hole observation {index} measured/nominal ratio must be between 0.25 and 2")
        measurement = (run_id, observation.orientation, nominal, measured)
        if measurement in measurements:
            raise ValueError("duplicate hole measurement cannot increase evidence count")
        measurements.add(measurement)
        corrections.append(nominal - measured)
        run_ids.append(run_id)
    values = tuple(corrections)
    if len(set(run_ids)) < 2:
        raise ValueError("hole observations must span at least two declared coupon runs")
    resolution = _finite_number(measurement_resolution_mm, "measurement_resolution_mm", 0.001, 1.0)
    return _robust_estimate(
        values,
        tuple(run_ids),
        resolution,
        "median(nominal-measured diameter); dispersion=max(1.4826*MAD, instrument resolution); descriptive only",
    )


def recommend_clearance(observations: tuple[ClearanceObservation, ...]) -> ClearanceRecommendation:
    """Fit a monotonic pass threshold robust to a minority of flipped outcomes."""

    if not isinstance(observations, tuple):
        raise TypeError("clearance observations must be an immutable tuple")
    identifiers: set[str] = set()
    clearance_values: set[tuple[str, float]] = set()
    run_ids: set[str] = set()
    for index, observation in enumerate(observations):
        if not isinstance(observation, ClearanceObservation):
            raise TypeError(f"clearance observation {index} must be a ClearanceObservation")
        observation_id = _identifier(observation.observation_id, f"clearance observation {index} id")
        if observation_id in identifiers:
            raise ValueError(f"duplicate observation_id: {observation_id}")
        identifiers.add(observation_id)
        run_id = _identifier(observation.run_id, f"clearance observation {index} run_id")
        run_ids.add(run_id)
        clearance = _finite_number(observation.clearance_mm, f"clearance observation {index} value", 0.0, 5.0)
        if not isinstance(observation.fit_succeeded, bool):
            raise TypeError(f"clearance observation {index} fit_succeeded must be a boolean")
        clearance_key = (run_id, clearance)
        if clearance_key in clearance_values:
            raise ValueError("a coupon run cannot repeat the same clearance value")
        clearance_values.add(clearance_key)
    failures = tuple(item for item in observations if not item.fit_succeeded)
    successes = tuple(item for item in observations if item.fit_succeeded)
    if len(failures) < MIN_CLEARANCE_OBSERVATIONS_PER_OUTCOME or len(successes) < MIN_CLEARANCE_OBSERVATIONS_PER_OUTCOME:
        raise ValueError("clearance fitting requires at least two successful and two failed observations")
    if len(run_ids) < 2:
        raise ValueError("clearance fitting requires at least two declared coupon runs")
    ordered = tuple(sorted(observations, key=lambda item: (item.clearance_mm, item.observation_id)))
    values = tuple(sorted({item.clearance_mm for item in ordered}))
    candidates = tuple((left + right) / 2.0 for left, right in pairwise(values))
    if not candidates:
        raise ValueError("clearance fitting requires distinct coupon values")

    def error_count(threshold: float) -> int:
        return sum(item.fit_succeeded != (item.clearance_mm >= threshold) for item in ordered)

    # Higher threshold wins exact ties: it is the more conservative fit claim.
    threshold = min(candidates, key=lambda candidate: (error_count(candidate), -candidate))
    errors = error_count(threshold)
    if errors * 4 > len(ordered):
        raise ValueError("clearance outcomes are too contradictory for a bounded monotonic recommendation")
    correctly_failed = tuple(item.clearance_mm for item in ordered if item.clearance_mm < threshold and not item.fit_succeeded)
    correctly_succeeded = tuple(item.clearance_mm for item in ordered if item.clearance_mm >= threshold and item.fit_succeeded)
    if not correctly_failed or not correctly_succeeded:
        raise ValueError("clearance evidence does not bracket a usable pass/fail transition")
    failure_edge = max(correctly_failed)
    success_edge = min(correctly_succeeded)
    uncertainty = (success_edge - failure_edge) / 2.0
    return ClearanceRecommendation(
        threshold_mm=(failure_edge + success_edge) / 2.0,
        recommended_clearance_mm=success_edge,
        bracket_half_width_mm=uncertainty,
        evidence_count=len(ordered),
        run_count=len(run_ids),
        failure_count=len(failures),
        success_count=len(successes),
        classification_errors=errors,
        observed_failure_edge_mm=failure_edge,
        observed_success_edge_mm=success_edge,
        method="minimum-error monotonic threshold; conservative tie break; recommendation=observed successful edge",
    )


def fit_calibration_profile(dataset: CalibrationDataset) -> CalibrationProfile:
    """Validate all evidence and return deterministic, reproducible recommendations."""

    validate_calibration_dataset(dataset)
    normalized = CalibrationDataset(
        profile_id=dataset.profile_id.strip(),
        printer=dataset.printer.strip(),
        material=dataset.material.strip(),
        process=dataset.process.strip(),
        nozzle_diameter_mm=float(dataset.nozzle_diameter_mm),
        measurement_resolution_mm=float(dataset.measurement_resolution_mm),
        axis_observations=tuple(sorted(dataset.axis_observations, key=lambda item: item.observation_id)),
        hole_observations=tuple(sorted(dataset.hole_observations, key=lambda item: item.observation_id)),
        clearance_observations=tuple(sorted(dataset.clearance_observations, key=lambda item: item.observation_id)),
    )
    return CalibrationProfile(
        dataset=normalized,
        xy_scale=recommend_xy_scale(
            normalized.axis_observations,
            measurement_resolution_mm=normalized.measurement_resolution_mm,
        ),
        z_scale=recommend_z_scale(
            normalized.axis_observations,
            measurement_resolution_mm=normalized.measurement_resolution_mm,
        ),
        hole_diameter_compensation_mm=recommend_hole_compensation(
            normalized.hole_observations,
            measurement_resolution_mm=normalized.measurement_resolution_mm,
        ),
        clearance=recommend_clearance(normalized.clearance_observations),
    )


def plan_calibration_application(
    project: EnclosureProject,
    profile: CalibrationProfile,
) -> CalibrationApplicationPlan:
    """Plan recommendations without mutating CAD or claiming slicer changes."""

    from .project import EnclosureProject

    if not isinstance(project, EnclosureProject):
        raise TypeError("project must be an EnclosureProject")
    if not isinstance(profile, CalibrationProfile):
        raise TypeError("profile must be a CalibrationProfile")
    expected = fit_calibration_profile(profile.dataset)
    if profile != expected:
        raise ValueError("calibration profile does not match its recorded evidence")
    edits: list[dict[str, object]] = []
    if project.spec.lid.kind == "friction" and project.spec.lid.clearance_mm < profile.clearance.recommended_clearance_mm:
        edits.append(
            {
                "field": "lid.clearance_mm",
                "before": project.spec.lid.clearance_mm,
                "after": profile.clearance.recommended_clearance_mm,
                "basis": "smallest observed successful clearance in the bounded coupon evidence",
            }
        )
    return CalibrationApplicationPlan(
        profile_id=profile.dataset.profile_id,
        project_revision=project.revision,
        suggested_project_edits=tuple(edits),
        slicer_scale_recommendations={
            "x": profile.xy_scale.x.value,
            "y": profile.xy_scale.y.value,
            "z": profile.z_scale.value,
        },
        modeled_hole_compensation_recommendation_mm=profile.hole_diameter_compensation_mm.value,
    )


def apply_calibrated_clearance(
    project: EnclosureProject,
    profile: CalibrationProfile,
    *,
    reason: str | None = None,
) -> EnclosureProject:
    """Apply only the reviewable friction-clearance recommendation as a revision."""

    from .project import update_project

    plan = plan_calibration_application(project, profile)
    if not plan.suggested_project_edits:
        raise ValueError("project has no applicable calibration-driven clearance increase")
    edit = plan.suggested_project_edits[0]
    audit_reason = reason or f"apply clearance evidence from calibration profile {profile.dataset.profile_id}"
    return update_project(project, str(edit["field"]), edit["after"], reason=audit_reason)


def serialize_calibration_profile(profile: CalibrationProfile, *, pretty: bool = True) -> str:
    """Serialize a profile deterministically as strict JSON."""

    expected = fit_calibration_profile(profile.dataset)
    if profile != expected:
        raise ValueError("profile recommendations or metadata do not match the recorded evidence")
    separators = None if pretty else (",", ":")
    return json.dumps(profile.to_dict(), sort_keys=True, indent=2 if pretty else None, separators=separators, allow_nan=False)


def _axis_observation(value: object, index: int) -> AxisObservation:
    item = _require_keys(
        value,
        {"observation_id", "axis", "nominal_mm", "measured_mm", "run_id"},
        context=f"axis_observations[{index}]",
    )
    return AxisObservation(
        item["observation_id"],
        item["axis"],
        item["nominal_mm"],
        item["measured_mm"],
        item["run_id"],
    )


def _hole_observation(value: object, index: int) -> HoleObservation:
    item = _require_keys(
        value,
        {"observation_id", "orientation", "nominal_diameter_mm", "measured_diameter_mm", "run_id"},
        context=f"hole_observations[{index}]",
    )
    return HoleObservation(
        item["observation_id"],
        item["orientation"],
        item["nominal_diameter_mm"],
        item["measured_diameter_mm"],
        item["run_id"],
    )


def _clearance_observation(value: object, index: int) -> ClearanceObservation:
    item = _require_keys(
        value,
        {"observation_id", "clearance_mm", "fit_succeeded", "run_id"},
        context=f"clearance_observations[{index}]",
    )
    return ClearanceObservation(
        item["observation_id"],
        item["clearance_mm"],
        item["fit_succeeded"],
        item["run_id"],
    )


def _dataset_from_dict(value: object) -> CalibrationDataset:
    item = _require_keys(
        value,
        {
            "profile_id",
            "printer",
            "material",
            "process",
            "nozzle_diameter_mm",
            "measurement_resolution_mm",
            "axis_observations",
            "hole_observations",
            "clearance_observations",
        },
        context="dataset",
    )
    for name in ("axis_observations", "hole_observations", "clearance_observations"):
        if not isinstance(item[name], list):
            raise TypeError(f"dataset.{name} must be an array")
    return CalibrationDataset(
        profile_id=item["profile_id"],
        printer=item["printer"],
        material=item["material"],
        process=item["process"],
        nozzle_diameter_mm=item["nozzle_diameter_mm"],
        measurement_resolution_mm=item["measurement_resolution_mm"],
        axis_observations=tuple(_axis_observation(entry, index) for index, entry in enumerate(item["axis_observations"])),
        hole_observations=tuple(_hole_observation(entry, index) for index, entry in enumerate(item["hole_observations"])),
        clearance_observations=tuple(
            _clearance_observation(entry, index) for index, entry in enumerate(item["clearance_observations"])
        ),
    )


def parse_calibration_dataset(text: str) -> CalibrationDataset:
    """Parse and validate raw coupon evidence before fitting recommendations."""

    if not isinstance(text, str):
        raise TypeError("calibration dataset must be JSON text")
    if len(text.encode("utf-8")) > MAX_CALIBRATION_JSON_BYTES:
        raise ValueError("calibration dataset exceeds the 1 MiB input limit")
    try:
        decoded = strict_json_loads(text)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError(f"invalid calibration JSON: {exc}") from exc
    dataset = _dataset_from_dict(decoded)
    validate_calibration_dataset(dataset)
    return dataset


def serialize_calibration_dataset(dataset: CalibrationDataset, *, pretty: bool = True) -> str:
    """Serialize validated raw observations without inventing recommendations."""

    validate_calibration_dataset(dataset)
    separators = None if pretty else (",", ":")
    return json.dumps(
        dataset.to_dict(),
        sort_keys=True,
        indent=2 if pretty else None,
        separators=separators,
        allow_nan=False,
    )


def parse_calibration_profile(text: str) -> CalibrationProfile:
    """Parse, strictly validate, and recompute a profile to reject stale/tampered claims."""

    if not isinstance(text, str):
        raise TypeError("calibration profile must be JSON text")
    if len(text.encode("utf-8")) > MAX_CALIBRATION_JSON_BYTES:
        raise ValueError("calibration profile exceeds the 1 MiB input limit")
    try:
        decoded = strict_json_loads(text)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError(f"invalid calibration JSON: {exc}") from exc
    root = _require_keys(
        decoded,
        {"schema_version", "method_version", "dataset", "recommendations", "limitations"},
        context="calibration profile",
    )
    if root["schema_version"] != CALIBRATION_SCHEMA_VERSION:
        raise ValueError(f"unsupported calibration schema version: {root['schema_version']!r}")
    if root["method_version"] != CALIBRATION_METHOD_VERSION:
        raise ValueError(f"unsupported calibration method version: {root['method_version']!r}")
    if root["limitations"] != list(CALIBRATION_LIMITATIONS):
        raise ValueError("calibration limitations metadata is missing or modified")
    if not isinstance(root["recommendations"], dict):
        raise TypeError("recommendations must be an object")
    dataset = _dataset_from_dict(root["dataset"])
    expected = fit_calibration_profile(dataset)
    if root["recommendations"] != expected.to_dict()["recommendations"]:
        raise ValueError("serialized recommendations do not match the recorded evidence")
    return expected
