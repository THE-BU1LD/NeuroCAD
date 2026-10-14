"""Single discovery surface for NeuroCAD analytical physics models."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .physics import (
    CircularShaftTorsionInput,
    EulerBucklingInput,
    HydrostaticBuoyancyInput,
    IdealBraytonCycleInput,
    InternalPipeFlowInput,
    LumpedThermalTransientInput,
    RadiativeExchangeInput,
    SpringMassDamperInput,
    SteadyConductionInput,
    SteadyConvectionInput,
    ThermalExpansionInput,
    ThinWallCylinderInput,
    circular_shaft_torsion,
    euler_buckling,
    hydrostatic_buoyancy,
    ideal_brayton_cycle,
    internal_pipe_flow,
    lumped_thermal_transient,
    radiative_exchange,
    spring_mass_damper,
    steady_conduction,
    steady_convection,
    thermal_expansion,
    thin_wall_cylinder,
)
from .physics_advanced import (
    CantileverBeamInput,
    CombinedStressInput,
    ElectroThermalWireInput,
    ForcedVibrationInput,
    PipeNetworkInput,
    ThermalNetworkInput,
    cantilever_beam,
    combined_stress,
    electro_thermal_wire,
    forced_vibration,
    pipe_network,
    thermal_network,
)

PhysicsEvaluator = Callable[[Any], dict[str, Any]]


def physics_models() -> dict[str, tuple[type[Any], PhysicsEvaluator]]:
    """Return every supported model without mutating the frozen v2 modules."""

    return {
        "cantilever_beam": (CantileverBeamInput, cantilever_beam),
        "circular_shaft_torsion": (CircularShaftTorsionInput, circular_shaft_torsion),
        "combined_stress": (CombinedStressInput, combined_stress),
        "electro_thermal_wire": (ElectroThermalWireInput, electro_thermal_wire),
        "euler_buckling": (EulerBucklingInput, euler_buckling),
        "forced_vibration": (ForcedVibrationInput, forced_vibration),
        "hydrostatic_buoyancy": (HydrostaticBuoyancyInput, hydrostatic_buoyancy),
        "ideal_brayton_cycle": (IdealBraytonCycleInput, ideal_brayton_cycle),
        "internal_pipe_flow": (InternalPipeFlowInput, internal_pipe_flow),
        "lumped_thermal_transient": (LumpedThermalTransientInput, lumped_thermal_transient),
        "pipe_network": (PipeNetworkInput, pipe_network),
        "radiative_exchange": (RadiativeExchangeInput, radiative_exchange),
        "spring_mass_damper": (SpringMassDamperInput, spring_mass_damper),
        "steady_conduction": (SteadyConductionInput, steady_conduction),
        "steady_convection": (SteadyConvectionInput, steady_convection),
        "thermal_expansion": (ThermalExpansionInput, thermal_expansion),
        "thermal_network": (ThermalNetworkInput, thermal_network),
        "thin_wall_cylinder": (ThinWallCylinderInput, thin_wall_cylinder),
    }


def physics_descriptions() -> dict[str, str]:
    return {
        "cantilever_beam": "Euler-Bernoulli cantilever reactions, tip response, and optional bending utilization.",
        "circular_shaft_torsion": "Elastic stress and twist of a solid or hollow circular shaft.",
        "combined_stress": "Three-dimensional principal, maximum-shear, and von Mises stress at one point.",
        "electro_thermal_wire": "Lumped electrical heating, thermal equilibrium, expansion, and optional restrained stress.",
        "euler_buckling": "Ideal elastic critical load for a prismatic column.",
        "forced_vibration": "Steady forced or base-excited response of a linear single-degree-of-freedom oscillator.",
        "hydrostatic_buoyancy": "Static-fluid gauge pressure and Archimedes buoyancy.",
        "ideal_brayton_cycle": "Ideal-gas cycle temperatures and specific work without propulsion sizing.",
        "internal_pipe_flow": "Reynolds number and Darcy-Weisbach major loss in a round pipe.",
        "lumped_thermal_transient": "Heating or cooling with a fail-closed Biot-number check.",
        "pipe_network": "Darcy-Weisbach losses for series segments and one balanced parallel bank.",
        "radiative_exchange": "Gray-surface radiation to large isothermal surroundings.",
        "spring_mass_damper": "Linear single-degree-of-freedom modal properties.",
        "steady_conduction": "Steady one-dimensional Fourier conduction through a slab.",
        "steady_convection": "Steady Newton cooling with a supplied film coefficient.",
        "thermal_expansion": "Uniform free expansion and optional restrained elastic stress.",
        "thermal_network": "Steady temperatures and heat flows in a linear conductance network.",
        "thin_wall_cylinder": "Closed-end pressure-vessel membrane stress with a thin-wall check.",
    }


ADVANCED_MODEL_NAMES = frozenset(
    {
        "cantilever_beam",
        "combined_stress",
        "electro_thermal_wire",
        "forced_vibration",
        "pipe_network",
        "thermal_network",
    }
)
