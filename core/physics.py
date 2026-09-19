"""Dimensionally explicit, bounded analytical physics models.

These closed-form models are useful for early design constraints. They are not
finite-element analysis, computational fluid dynamics, certification, or a
substitute for material/process-specific validation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _positive(value: float, name: str, *, allow_zero: bool = False) -> float:
    result = _finite(value, name)
    if result < 0 if allow_zero else result <= 0:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be {qualifier}")
    return result


def _optional_positive(value: float | None, name: str) -> float | None:
    return None if value is None else _positive(value, name)


def _checked(values: dict[str, Any], *, model: str, assumptions: tuple[str, ...]) -> dict[str, Any]:
    if any(isinstance(value, float) and not math.isfinite(value) for value in values.values()):
        raise ValueError(f"{model} result exceeds the finite numerical range")
    return {
        "model": model,
        "results": values,
        "assumptions": list(assumptions),
        "claim_boundary": "bounded analytical estimate; not simulation, certification, or physical validation",
    }


@dataclass(frozen=True)
class EulerBucklingInput:
    elastic_modulus_mpa: float
    second_moment_mm4: float
    effective_length_mm: float
    area_mm2: float | None = None
    applied_load_n: float | None = None
    safety_factor: float = 1.0


def euler_buckling(request: EulerBucklingInput) -> dict[str, Any]:
    """Ideal elastic Euler buckling for the supplied effective length."""

    modulus = _positive(request.elastic_modulus_mpa, "elastic_modulus_mpa")
    inertia = _positive(request.second_moment_mm4, "second_moment_mm4")
    length = _positive(request.effective_length_mm, "effective_length_mm")
    area = _optional_positive(request.area_mm2, "area_mm2")
    applied = None if request.applied_load_n is None else _positive(request.applied_load_n, "applied_load_n", allow_zero=True)
    safety = _positive(request.safety_factor, "safety_factor")
    critical = math.pi**2 * modulus * inertia / length**2
    allowable = critical / safety
    radius_of_gyration = None if area is None else math.sqrt(inertia / area)
    slenderness = None if radius_of_gyration is None else length / radius_of_gyration
    utilization = None if applied is None else applied / allowable
    passes = None if applied is None else applied <= allowable
    return _checked(
        {
            "critical_load_n": critical,
            "allowable_load_n": allowable,
            "radius_of_gyration_mm": radius_of_gyration,
            "slenderness_ratio": slenderness,
            "utilization": utilization,
            "constraint_satisfied": passes,
        },
        model="euler_buckling_v1",
        assumptions=(
            "straight prismatic column with the supplied effective length",
            "linear elastic material, small deflection, centered axial load",
            "no imperfections, residual stress, local buckling, creep, or connection failure",
        ),
    )


@dataclass(frozen=True)
class ThermalExpansionInput:
    length_mm: float
    coefficient_per_k: float
    delta_temperature_k: float
    elastic_modulus_mpa: float | None = None
    area_mm2: float | None = None
    yield_strength_mpa: float | None = None
    safety_factor: float = 1.0


def thermal_expansion(request: ThermalExpansionInput) -> dict[str, Any]:
    """Uniform one-dimensional expansion and ideal fully restrained stress."""

    length = _positive(request.length_mm, "length_mm")
    coefficient = _finite(request.coefficient_per_k, "coefficient_per_k")
    delta_temperature = _finite(request.delta_temperature_k, "delta_temperature_k")
    modulus = _optional_positive(request.elastic_modulus_mpa, "elastic_modulus_mpa")
    area = _optional_positive(request.area_mm2, "area_mm2")
    yield_strength = _optional_positive(request.yield_strength_mpa, "yield_strength_mpa")
    safety = _positive(request.safety_factor, "safety_factor")
    if (area is not None or yield_strength is not None) and modulus is None:
        raise ValueError("area_mm2 and yield_strength_mpa require elastic_modulus_mpa")
    strain = coefficient * delta_temperature
    expansion = length * strain
    restrained_stress = None if modulus is None else -modulus * strain
    reaction = None if area is None or restrained_stress is None else restrained_stress * area
    utilization = None
    passes = None
    if yield_strength is not None and restrained_stress is not None:
        allowable = yield_strength / safety
        utilization = abs(restrained_stress) / allowable
        passes = abs(restrained_stress) <= allowable
    return _checked(
        {
            "thermal_strain": strain,
            "free_expansion_mm": expansion,
            "fully_restrained_stress_mpa": restrained_stress,
            "fully_restrained_reaction_n": reaction,
            "yield_utilization": utilization,
            "constraint_satisfied": passes,
        },
        model="uniform_thermal_expansion_v1",
        assumptions=(
            "uniform temperature and constant isotropic coefficient",
            "one-dimensional member with ideal free or fully restrained boundary condition",
            "linear elasticity when restrained stress is requested",
        ),
    )


@dataclass(frozen=True)
class SteadyConductionInput:
    conductivity_w_mk: float
    area_mm2: float
    thickness_mm: float
    delta_temperature_k: float


def steady_conduction(request: SteadyConductionInput) -> dict[str, Any]:
    """One-dimensional steady Fourier conduction through a uniform slab."""

    conductivity = _positive(request.conductivity_w_mk, "conductivity_w_mk")
    area_mm2 = _positive(request.area_mm2, "area_mm2")
    thickness_mm = _positive(request.thickness_mm, "thickness_mm")
    delta_temperature = _finite(request.delta_temperature_k, "delta_temperature_k")
    area_m2 = area_mm2 * 1e-6
    thickness_m = thickness_mm * 1e-3
    resistance = thickness_m / (conductivity * area_m2)
    heat_rate = delta_temperature / resistance
    heat_flux = heat_rate / area_m2
    return _checked(
        {
            "thermal_resistance_k_per_w": resistance,
            "heat_rate_w": heat_rate,
            "heat_flux_w_m2": heat_flux,
        },
        model="steady_1d_conduction_v1",
        assumptions=(
            "steady one-dimensional conduction through a uniform slab",
            "constant isotropic conductivity and uniform face temperatures",
            "no convection, radiation, contact resistance, or internal heat generation",
        ),
    )


@dataclass(frozen=True)
class InternalPipeFlowInput:
    density_kg_m3: float
    dynamic_viscosity_pa_s: float
    velocity_m_s: float
    diameter_mm: float
    length_mm: float
    darcy_friction_factor: float | None = None


def internal_pipe_flow(request: InternalPipeFlowInput) -> dict[str, Any]:
    """Reynolds number and Darcy-Weisbach major loss for a round pipe."""

    density = _positive(request.density_kg_m3, "density_kg_m3")
    viscosity = _positive(request.dynamic_viscosity_pa_s, "dynamic_viscosity_pa_s")
    velocity = _positive(request.velocity_m_s, "velocity_m_s", allow_zero=True)
    diameter_m = _positive(request.diameter_mm, "diameter_mm") * 1e-3
    length_m = _positive(request.length_mm, "length_mm") * 1e-3
    supplied_factor = _optional_positive(request.darcy_friction_factor, "darcy_friction_factor")
    reynolds = density * velocity * diameter_m / viscosity
    regime = "stagnant" if reynolds == 0 else ("laminar" if reynolds < 2300 else ("transitional" if reynolds < 4000 else "turbulent"))
    if supplied_factor is None:
        if reynolds == 0:
            friction_factor = 0.0
            factor_source = "zero-flow limit"
        elif regime == "laminar":
            friction_factor = 64.0 / reynolds
            factor_source = "fully-developed laminar 64/Re"
        else:
            raise ValueError("transitional or turbulent flow requires an explicit darcy_friction_factor")
    else:
        friction_factor = supplied_factor
        factor_source = "user supplied"
    dynamic_pressure = 0.5 * density * velocity**2
    pressure_loss = friction_factor * (length_m / diameter_m) * dynamic_pressure
    volumetric_flow = velocity * math.pi * diameter_m**2 / 4.0
    return _checked(
        {
            "reynolds_number": reynolds,
            "flow_regime": regime,
            "darcy_friction_factor": friction_factor,
            "dynamic_pressure_pa": dynamic_pressure,
            "major_pressure_loss_pa": pressure_loss,
            "volumetric_flow_m3_s": volumetric_flow,
        },
        model="round_pipe_darcy_weisbach_v1",
        assumptions=(
            "steady incompressible fully developed flow in a constant round pipe",
            "major loss only; no entrance, fitting, elevation, cavitation, or compressibility effects",
            f"friction factor source: {factor_source}",
        ),
    )


@dataclass(frozen=True)
class ThinWallCylinderInput:
    internal_pressure_mpa: float
    mean_radius_mm: float
    wall_thickness_mm: float
    yield_strength_mpa: float | None = None
    safety_factor: float = 1.0


def thin_wall_cylinder(request: ThinWallCylinderInput) -> dict[str, Any]:
    """Membrane stress for an ideal closed-end thin-wall pressure cylinder."""

    pressure = _positive(request.internal_pressure_mpa, "internal_pressure_mpa", allow_zero=True)
    radius = _positive(request.mean_radius_mm, "mean_radius_mm")
    thickness = _positive(request.wall_thickness_mm, "wall_thickness_mm")
    yield_strength = _optional_positive(request.yield_strength_mpa, "yield_strength_mpa")
    safety = _positive(request.safety_factor, "safety_factor")
    radius_to_thickness = radius / thickness
    if radius_to_thickness < 10:
        raise ValueError("thin-wall model requires mean_radius_mm / wall_thickness_mm >= 10")
    hoop = pressure * radius / thickness
    longitudinal = pressure * radius / (2.0 * thickness)
    von_mises = math.sqrt(hoop**2 - hoop * longitudinal + longitudinal**2)
    utilization = None
    passes = None
    if yield_strength is not None:
        allowable = yield_strength / safety
        utilization = von_mises / allowable
        passes = von_mises <= allowable
    return _checked(
        {
            "radius_to_thickness_ratio": radius_to_thickness,
            "hoop_stress_mpa": hoop,
            "longitudinal_stress_mpa": longitudinal,
            "plane_stress_von_mises_mpa": von_mises,
            "yield_utilization": utilization,
            "constraint_satisfied": passes,
        },
        model="closed_end_thin_wall_cylinder_v1",
        assumptions=(
            "thin uniform circular cylinder with closed ends and membrane stress",
            "static internal pressure, linear elasticity, no openings or stress concentrations",
            "no fatigue, creep, instability, joints, defects, or material anisotropy",
        ),
    )
