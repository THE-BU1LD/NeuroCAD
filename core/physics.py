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
class SteadyConvectionInput:
    heat_transfer_coefficient_w_m2k: float
    area_mm2: float
    surface_temperature_k: float
    fluid_temperature_k: float


def steady_convection(request: SteadyConvectionInput) -> dict[str, Any]:
    """Newton cooling at a surface with a supplied film coefficient."""

    coefficient = _positive(request.heat_transfer_coefficient_w_m2k, "heat_transfer_coefficient_w_m2k")
    area_m2 = _positive(request.area_mm2, "area_mm2") * 1e-6
    surface_temperature = _positive(request.surface_temperature_k, "surface_temperature_k")
    fluid_temperature = _positive(request.fluid_temperature_k, "fluid_temperature_k")
    delta_temperature = surface_temperature - fluid_temperature
    heat_flux = coefficient * delta_temperature
    heat_rate = heat_flux * area_m2
    return _checked(
        {
            "surface_to_fluid_delta_temperature_k": delta_temperature,
            "heat_rate_surface_to_fluid_w": heat_rate,
            "heat_flux_surface_to_fluid_w_m2": heat_flux,
            "thermal_resistance_k_per_w": 1.0 / (coefficient * area_m2),
        },
        model="steady_surface_convection_v1",
        assumptions=(
            "steady convection over a uniform isothermal surface",
            "user-supplied constant area-averaged heat-transfer coefficient",
            "no conduction, radiation, phase change, or coefficient correlation",
        ),
    )


@dataclass(frozen=True)
class RadiativeExchangeInput:
    emissivity: float
    area_mm2: float
    surface_temperature_k: float
    surroundings_temperature_k: float
    view_factor: float = 1.0


def radiative_exchange(request: RadiativeExchangeInput) -> dict[str, Any]:
    """Gray-surface radiation to large isothermal surroundings."""

    emissivity = _positive(request.emissivity, "emissivity")
    area_m2 = _positive(request.area_mm2, "area_mm2") * 1e-6
    surface_temperature = _positive(request.surface_temperature_k, "surface_temperature_k")
    surroundings_temperature = _positive(request.surroundings_temperature_k, "surroundings_temperature_k")
    view_factor = _positive(request.view_factor, "view_factor")
    if emissivity > 1.0 or view_factor > 1.0:
        raise ValueError("emissivity and view_factor must not exceed 1")
    stefan_boltzmann = 5.670374419e-8
    heat_flux = emissivity * view_factor * stefan_boltzmann * (
        surface_temperature**4 - surroundings_temperature**4
    )
    return _checked(
        {
            "surface_to_surroundings_delta_temperature_k": surface_temperature - surroundings_temperature,
            "heat_rate_surface_to_surroundings_w": heat_flux * area_m2,
            "heat_flux_surface_to_surroundings_w_m2": heat_flux,
        },
        model="gray_surface_radiation_v1",
        assumptions=(
            "diffuse gray isothermal surface and large isothermal surroundings",
            "user-supplied effective view factor with no participating medium",
            "constant emissivity and no reflected external irradiation beyond the surroundings model",
        ),
    )


@dataclass(frozen=True)
class LumpedThermalTransientInput:
    density_kg_m3: float
    specific_heat_j_kgk: float
    volume_mm3: float
    surface_area_mm2: float
    heat_transfer_coefficient_w_m2k: float
    conductivity_w_mk: float
    initial_temperature_k: float
    ambient_temperature_k: float
    time_s: float


def lumped_thermal_transient(request: LumpedThermalTransientInput) -> dict[str, Any]:
    """Lumped-capacitance heating or cooling when Biot number is at most 0.1."""

    density = _positive(request.density_kg_m3, "density_kg_m3")
    specific_heat = _positive(request.specific_heat_j_kgk, "specific_heat_j_kgk")
    volume_m3 = _positive(request.volume_mm3, "volume_mm3") * 1e-9
    area_m2 = _positive(request.surface_area_mm2, "surface_area_mm2") * 1e-6
    coefficient = _positive(request.heat_transfer_coefficient_w_m2k, "heat_transfer_coefficient_w_m2k")
    conductivity = _positive(request.conductivity_w_mk, "conductivity_w_mk")
    initial_temperature = _positive(request.initial_temperature_k, "initial_temperature_k")
    ambient_temperature = _positive(request.ambient_temperature_k, "ambient_temperature_k")
    time = _positive(request.time_s, "time_s", allow_zero=True)
    characteristic_length = volume_m3 / area_m2
    biot_number = coefficient * characteristic_length / conductivity
    if biot_number > 0.1:
        raise ValueError("lumped thermal model requires Biot number <= 0.1")
    mass = density * volume_m3
    time_constant = mass * specific_heat / (coefficient * area_m2)
    temperature_ratio = math.exp(-time / time_constant)
    temperature = ambient_temperature + (initial_temperature - ambient_temperature) * temperature_ratio
    return _checked(
        {
            "mass_kg": mass,
            "characteristic_length_m": characteristic_length,
            "biot_number": biot_number,
            "time_constant_s": time_constant,
            "temperature_ratio": temperature_ratio,
            "temperature_k": temperature,
            "stored_energy_relative_to_ambient_j": mass * specific_heat * (temperature - ambient_temperature),
        },
        model="lumped_thermal_transient_v1",
        assumptions=(
            "spatially uniform body temperature justified only when reported Biot number is at most 0.1",
            "constant material properties, ambient temperature, area, and heat-transfer coefficient",
            "no radiation, phase change, internal heat generation, contact resistance, or multidimensional gradient",
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
class HydrostaticBuoyancyInput:
    fluid_density_kg_m3: float
    depth_mm: float
    displaced_volume_mm3: float
    gravity_m_s2: float = 9.80665
    object_mass_kg: float | None = None


def hydrostatic_buoyancy(request: HydrostaticBuoyancyInput) -> dict[str, Any]:
    """Gauge pressure and Archimedes buoyancy in a uniform static fluid."""

    density = _positive(request.fluid_density_kg_m3, "fluid_density_kg_m3")
    depth_m = _positive(request.depth_mm, "depth_mm", allow_zero=True) * 1e-3
    volume_m3 = _positive(request.displaced_volume_mm3, "displaced_volume_mm3") * 1e-9
    gravity = _positive(request.gravity_m_s2, "gravity_m_s2")
    object_mass = _optional_positive(request.object_mass_kg, "object_mass_kg")
    buoyant_force = density * gravity * volume_m3
    weight = None if object_mass is None else object_mass * gravity
    apparent_weight = None if weight is None else weight - buoyant_force
    return _checked(
        {
            "gauge_pressure_pa": density * gravity * depth_m,
            "buoyant_force_n": buoyant_force,
            "object_weight_n": weight,
            "apparent_weight_n": apparent_weight,
            "buoyant_force_at_least_weight": None if weight is None else buoyant_force >= weight,
        },
        model="hydrostatic_buoyancy_v1",
        assumptions=(
            "uniform incompressible static fluid under constant gravity",
            "depth is measured below a free surface and pressure output is gauge pressure",
            "declared displaced volume is fully submerged; no surface tension, dynamics, leakage, or stability model",
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


@dataclass(frozen=True)
class CircularShaftTorsionInput:
    torque_n_m: float
    length_mm: float
    outer_diameter_mm: float
    shear_modulus_mpa: float
    inner_diameter_mm: float = 0.0
    yield_strength_mpa: float | None = None
    safety_factor: float = 1.0


def circular_shaft_torsion(request: CircularShaftTorsionInput) -> dict[str, Any]:
    """Saint-Venant elastic torsion of a solid or hollow circular shaft."""

    torque_n_mm = _finite(request.torque_n_m, "torque_n_m") * 1_000.0
    length = _positive(request.length_mm, "length_mm")
    outer_diameter = _positive(request.outer_diameter_mm, "outer_diameter_mm")
    inner_diameter = _positive(request.inner_diameter_mm, "inner_diameter_mm", allow_zero=True)
    shear_modulus = _positive(request.shear_modulus_mpa, "shear_modulus_mpa")
    yield_strength = _optional_positive(request.yield_strength_mpa, "yield_strength_mpa")
    safety = _positive(request.safety_factor, "safety_factor")
    if inner_diameter >= outer_diameter:
        raise ValueError("inner_diameter_mm must be less than outer_diameter_mm")
    polar_moment = math.pi * (outer_diameter**4 - inner_diameter**4) / 32.0
    maximum_shear = abs(torque_n_mm) * outer_diameter / (2.0 * polar_moment)
    twist_radians = torque_n_mm * length / (shear_modulus * polar_moment)
    von_mises = math.sqrt(3.0) * maximum_shear
    utilization = None
    passes = None
    if yield_strength is not None:
        allowable = yield_strength / safety
        utilization = von_mises / allowable
        passes = von_mises <= allowable
    return _checked(
        {
            "polar_second_moment_mm4": polar_moment,
            "maximum_shear_stress_mpa": maximum_shear,
            "von_mises_stress_mpa": von_mises,
            "twist_radians": twist_radians,
            "twist_degrees": math.degrees(twist_radians),
            "yield_utilization": utilization,
            "constraint_satisfied": passes,
        },
        model="circular_shaft_torsion_v1",
        assumptions=(
            "straight prismatic solid or hollow circular shaft under Saint-Venant torsion",
            "linear elastic isotropic material, small twist, and uniform applied torque",
            "no keyways, shoulders, stress concentrations, warping restraint, fatigue, buckling, or dynamics",
        ),
    )


@dataclass(frozen=True)
class SpringMassDamperInput:
    mass_kg: float
    stiffness_n_m: float
    damping_n_s_m: float = 0.0
    applied_force_n: float | None = None


def spring_mass_damper(request: SpringMassDamperInput) -> dict[str, Any]:
    """Undriven linear single-degree-of-freedom modal properties."""

    mass = _positive(request.mass_kg, "mass_kg")
    stiffness = _positive(request.stiffness_n_m, "stiffness_n_m")
    damping = _positive(request.damping_n_s_m, "damping_n_s_m", allow_zero=True)
    applied_force = None if request.applied_force_n is None else _finite(request.applied_force_n, "applied_force_n")
    natural_angular_frequency = math.sqrt(stiffness / mass)
    critical_damping = 2.0 * math.sqrt(stiffness * mass)
    damping_ratio = damping / critical_damping
    if damping_ratio < 1.0:
        regime = "underdamped"
        damped_angular_frequency: float | None = natural_angular_frequency * math.sqrt(1.0 - damping_ratio**2)
    elif damping_ratio == 1.0:
        regime = "critically_damped"
        damped_angular_frequency = None
    else:
        regime = "overdamped"
        damped_angular_frequency = None
    return _checked(
        {
            "natural_angular_frequency_rad_s": natural_angular_frequency,
            "natural_frequency_hz": natural_angular_frequency / (2.0 * math.pi),
            "critical_damping_n_s_m": critical_damping,
            "damping_ratio": damping_ratio,
            "damping_regime": regime,
            "damped_angular_frequency_rad_s": damped_angular_frequency,
            "damped_frequency_hz": None
            if damped_angular_frequency is None
            else damped_angular_frequency / (2.0 * math.pi),
            "static_deflection_m": None if applied_force is None else applied_force / stiffness,
        },
        model="linear_spring_mass_damper_v1",
        assumptions=(
            "linear single-degree-of-freedom mass, spring, and viscous damper",
            "modal properties are for free vibration about static equilibrium",
            "no forcing spectrum, nonlinear stiffness, friction, impacts, distributed mass, fatigue, or mounting dynamics",
        ),
    )


@dataclass(frozen=True)
class IdealBraytonCycleInput:
    """Inputs for a bounded ideal-gas Brayton-cycle diagnostic.

    This is a thermodynamic consistency calculation, not a jet-engine sizing or
    performance model. In particular, it contains no mass flow, thrust, nozzle,
    fuel, blade, cooling, bearing, structural, or control-system design.
    """

    inlet_temperature_k: float
    compressor_pressure_ratio: float
    turbine_inlet_temperature_k: float
    heat_capacity_ratio: float
    specific_heat_j_kgk: float
    compressor_efficiency: float = 1.0
    turbine_efficiency: float = 1.0


def ideal_brayton_cycle(request: IdealBraytonCycleInput) -> dict[str, Any]:
    """Evaluate an idealized simple Brayton cycle without propulsion outputs."""

    inlet_temperature = _positive(request.inlet_temperature_k, "inlet_temperature_k")
    pressure_ratio = _positive(request.compressor_pressure_ratio, "compressor_pressure_ratio")
    turbine_inlet_temperature = _positive(request.turbine_inlet_temperature_k, "turbine_inlet_temperature_k")
    gamma = _positive(request.heat_capacity_ratio, "heat_capacity_ratio")
    specific_heat = _positive(request.specific_heat_j_kgk, "specific_heat_j_kgk")
    compressor_efficiency = _positive(request.compressor_efficiency, "compressor_efficiency")
    turbine_efficiency = _positive(request.turbine_efficiency, "turbine_efficiency")
    if pressure_ratio <= 1.0 or pressure_ratio > 100.0:
        raise ValueError("compressor_pressure_ratio must be greater than 1 and at most 100")
    if not 1.0 < gamma <= 2.0:
        raise ValueError("heat_capacity_ratio must be greater than 1 and at most 2")
    if compressor_efficiency > 1.0 or turbine_efficiency > 1.0:
        raise ValueError("compressor_efficiency and turbine_efficiency must not exceed 1")

    exponent = (gamma - 1.0) / gamma
    ideal_compressor_outlet = inlet_temperature * pressure_ratio**exponent
    compressor_outlet = inlet_temperature + (ideal_compressor_outlet - inlet_temperature) / compressor_efficiency
    if turbine_inlet_temperature <= compressor_outlet:
        raise ValueError("turbine_inlet_temperature_k must exceed the calculated compressor outlet temperature")

    ideal_turbine_outlet = turbine_inlet_temperature / pressure_ratio**exponent
    turbine_outlet = turbine_inlet_temperature - turbine_efficiency * (
        turbine_inlet_temperature - ideal_turbine_outlet
    )
    compressor_work = specific_heat * (compressor_outlet - inlet_temperature)
    turbine_work = specific_heat * (turbine_inlet_temperature - turbine_outlet)
    heat_added = specific_heat * (turbine_inlet_temperature - compressor_outlet)
    net_work = turbine_work - compressor_work
    thermal_efficiency = net_work / heat_added
    back_work_ratio = compressor_work / turbine_work
    return _checked(
        {
            "compressor_outlet_temperature_k": compressor_outlet,
            "turbine_outlet_temperature_k": turbine_outlet,
            "compressor_specific_work_j_kg": compressor_work,
            "turbine_specific_work_j_kg": turbine_work,
            "net_specific_work_j_kg": net_work,
            "specific_heat_added_j_kg": heat_added,
            "thermal_efficiency": thermal_efficiency,
            "back_work_ratio": back_work_ratio,
            "cycle_net_positive": net_work > 0.0,
        },
        model="ideal_brayton_cycle_v1",
        assumptions=(
            "steady ideal gas with constant specific heat and heat-capacity ratio",
            "simple compressor, external heat-addition, turbine, and heat-rejection cycle",
            "no pressure losses, bleed, cooling flow, combustion chemistry, component maps, or mechanical losses",
            "no mass flow, thrust, nozzle, blade, fuel, structural, fatigue, bearing, or control-system prediction",
        ),
    )
