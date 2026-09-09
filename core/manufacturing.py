"""Explainable fabrication preflight for typed enclosure specifications."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .calibration import CalibrationProfile, fit_calibration_profile
from .enclosure import MANUFACTURING_PROFILES, EnclosureSpec, validate_enclosure_spec
from .engineering_math import ToleranceContribution, tolerance_stack


@dataclass(frozen=True)
class PreflightFinding:
    severity: str
    code: str
    message: str
    evidence: dict[str, Any]
    basis: str  # exact | empirical | analytical | heuristic

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "evidence": dict(self.evidence),
            "basis": self.basis,
        }


@dataclass(frozen=True)
class FabricationEstimate:
    bounding_volume_mm3: float
    approximate_material_volume_mm3: float
    approximate_mass_g: float | None
    approximate_material_cost: float | None

    def to_dict(self) -> dict[str, float | None]:
        return {
            "bounding_volume_mm3": self.bounding_volume_mm3,
            "approximate_material_volume_mm3": self.approximate_material_volume_mm3,
            "approximate_mass_g": self.approximate_mass_g,
            "approximate_material_cost": self.approximate_material_cost,
        }


@dataclass(frozen=True)
class PreflightReport:
    valid: bool
    findings: tuple[PreflightFinding, ...]
    measurements: dict[str, Any]
    estimate: FabricationEstimate

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "findings": [finding.to_dict() for finding in self.findings],
            "measurements": dict(self.measurements),
            "estimate": self.estimate.to_dict(),
            "disclaimer": "Analytical and heuristic findings are fabrication aids, not safety certification.",
        }


def _shell_volume(spec: EnclosureSpec) -> float:
    width, depth, height = spec.outer_size_mm
    floor = spec.floor_mm if spec.floor_mm is not None else spec.wall_mm
    inner_width = width - 2 * spec.wall_mm
    inner_depth = depth - 2 * spec.wall_mm
    cavity_height = height - floor
    shell = width * depth * height - max(0.0, inner_width * inner_depth * cavity_height)
    standoffs = sum(
        math.pi * (standoff.outer_diameter_mm**2 - standoff.hole_diameter_mm**2) * standoff.height_mm / 4
        for standoff in spec.standoffs
    )
    lid = 0.0
    if spec.lid.kind != "none":
        lid_width = width - 2 * spec.lid.clearance_mm
        lid_depth = depth - 2 * spec.lid.clearance_mm
        lid = max(0.0, lid_width * lid_depth * spec.lid.thickness_mm)
    return max(0.0, shell + standoffs + lid)


def fabrication_preflight(
    spec: EnclosureSpec,
    *,
    density_g_cm3: float | None = None,
    material_cost_per_kg: float | None = None,
    tolerance_contributions: tuple[ToleranceContribution, ...] = (),
    calibration_profile: CalibrationProfile | None = None,
) -> PreflightReport:
    validation = validate_enclosure_spec(spec)
    heuristic_policy_codes = {
        "below_profile_minimum",
        "below_profile_clearance",
        "edge_clearance",
        "feature_overlap",
        "standoff_overlap",
    }
    findings = [
        PreflightFinding(
            issue.severity,
            issue.code,
            issue.message,
            {"path": issue.path},
            "heuristic" if issue.code in heuristic_policy_codes else "exact",
        )
        for issue in validation.issues
    ]
    width, depth, height = spec.outer_size_mm
    floor = spec.floor_mm if spec.floor_mm is not None else spec.wall_mm
    internal = (width - 2 * spec.wall_mm, depth - 2 * spec.wall_mm, height - floor)
    profile = MANUFACTURING_PROFILES.get(spec.profile)
    calibrated: CalibrationProfile | None = None
    if calibration_profile is not None:
        if not isinstance(calibration_profile, CalibrationProfile):
            raise TypeError("calibration_profile must be a CalibrationProfile")
        calibrated = fit_calibration_profile(calibration_profile.dataset)
        if calibrated != calibration_profile:
            raise ValueError("calibration profile does not match its recorded evidence")
    if profile is not None:
        if spec.wall_mm < profile.minimum_wall_mm * 1.2:
            findings.append(
                PreflightFinding(
                    "warning",
                    "wall_near_minimum",
                    "wall thickness is within 20% of the selected profile minimum",
                    {"wall_mm": spec.wall_mm, "minimum_wall_mm": profile.minimum_wall_mm},
                    "heuristic",
                )
            )
        for standoff in spec.standoffs:
            ligament = (standoff.outer_diameter_mm - standoff.hole_diameter_mm) / 2
            if ligament < profile.minimum_ligament_mm:
                findings.append(
                    PreflightFinding(
                        "warning",
                        "thin_standoff_ligament",
                        f"standoff {standoff.id!r} has a thin radial ligament",
                        {"ligament_mm": ligament, "recommended_mm": profile.minimum_ligament_mm},
                        "heuristic",
                    )
                )
        if spec.lid.kind == "friction" and calibrated is not None:
            recommendation = calibrated.clearance
            meets_observed = spec.lid.clearance_mm >= recommendation.recommended_clearance_mm
            findings.append(
                PreflightFinding(
                    "info" if meets_observed else "error",
                    "calibrated_lid_clearance",
                    (
                        "lid clearance meets the smallest observed successful coupon clearance"
                        if meets_observed
                        else "lid clearance is below the smallest observed successful coupon clearance"
                    ),
                    {
                        "specified_clearance_mm": spec.lid.clearance_mm,
                        "recommended_clearance_mm": recommendation.recommended_clearance_mm,
                        "bracket_half_width_mm": recommendation.bracket_half_width_mm,
                        "coupon_run_count": recommendation.run_count,
                        "calibration_profile_id": calibrated.dataset.profile_id,
                    },
                    "empirical",
                )
            )
        elif spec.lid.kind == "friction" and tolerance_contributions:
            tolerance = tolerance_stack(spec.lid.clearance_mm, tolerance_contributions)
            severity = "warning" if tolerance.success_probability < 0.99 else "info"
            findings.append(
                PreflightFinding(
                    severity,
                    "lid_fit_probability",
                    "estimated lid fit under the supplied independent tolerance model",
                    tolerance.to_dict(),
                    "analytical",
                )
            )

        if calibrated is not None:
            findings.append(
                PreflightFinding(
                    "info",
                    "calibration_actions_not_implicit",
                    "slicer scale and measured hole compensation are reported but never silently applied",
                    {
                        "calibration_profile_id": calibrated.dataset.profile_id,
                        "slicer_scale_x": calibrated.xy_scale.x.value,
                        "slicer_scale_y": calibrated.xy_scale.y.value,
                        "slicer_scale_z": calibrated.z_scale.value,
                        "measured_hole_compensation_mm": calibrated.hole_diameter_compensation_mm.value,
                        "built_in_hole_compensation_mm": profile.hole_compensation_mm,
                    },
                    "empirical",
                )
            )
        if spec.lid.kind == "friction" and calibrated is None and not tolerance_contributions:
            findings.append(
                PreflightFinding(
                    "info",
                    "lid_fit_not_evaluated",
                    "fit probability was not evaluated because no measured tolerance contributions were supplied",
                    {
                        "specified_clearance_mm": spec.lid.clearance_mm,
                        "profile_minimum_clearance_mm": profile.press_clearance_mm,
                    },
                    "heuristic",
                )
            )

    bounding = width * depth * height
    material = _shell_volume(spec)
    mass: float | None = None
    cost: float | None = None
    if density_g_cm3 is not None:
        if isinstance(density_g_cm3, bool) or not math.isfinite(density_g_cm3) or density_g_cm3 <= 0:
            raise ValueError("density_g_cm3 must be positive and finite")
        mass = material / 1000 * density_g_cm3
        if not math.isfinite(mass):
            raise ValueError("calculated mass exceeds the finite numeric range")
        if material_cost_per_kg is not None:
            if isinstance(material_cost_per_kg, bool) or not math.isfinite(material_cost_per_kg) or material_cost_per_kg < 0:
                raise ValueError("material_cost_per_kg must be finite and non-negative")
            cost = mass / 1000 * material_cost_per_kg
            if not math.isfinite(cost):
                raise ValueError("calculated material cost exceeds the finite numeric range")
    elif material_cost_per_kg is not None:
        raise ValueError("material cost requires a material density")

    measurements = {
        "outer_size_mm": list(spec.outer_size_mm),
        "internal_size_mm": list(internal),
        "minimum_wall_mm": spec.wall_mm,
        "floor_mm": floor,
        "cutout_count": len(spec.cutouts),
        "vent_hole_count": sum(vent.rows * vent.columns for vent in spec.vents),
        "standoff_count": len(spec.standoffs),
        "lid_part_count": 0 if spec.lid.kind == "none" else 1,
        "profile_assumptions": (
            {
                "minimum_wall_mm": profile.minimum_wall_mm,
                "minimum_ligament_mm": profile.minimum_ligament_mm,
                "friction_fit_clearance_mm": profile.press_clearance_mm,
                "hole_compensation_applied_mm": profile.hole_compensation_mm,
            }
            if profile is not None
            else None
        ),
        "calibration_profile_id": calibrated.dataset.profile_id if calibrated is not None else None,
    }
    estimate = FabricationEstimate(bounding, material, mass, cost)
    valid = validation.valid and not any(finding.severity == "error" for finding in findings)
    return PreflightReport(valid, tuple(findings), measurements, estimate)
