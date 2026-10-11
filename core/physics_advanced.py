"""Bounded analytical models added by the NeuroCAD Physics v3 successor.

The functions in this module deliberately stop at closed-form or small
network calculations whose assumptions can be stated and checked.  They do
not emulate FEA, CFD, nonlinear constitutive laws, or spatial field solvers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _positive(value: Any, name: str, *, allow_zero: bool = False) -> float:
    result = _finite(value, name)
    if result < 0 if allow_zero else result <= 0:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be {qualifier}")
    return result


def _optional_positive(value: Any, name: str) -> float | None:
    return None if value is None else _positive(value, name)


def _assert_finite(value: Any, name: str = "result") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{name} exceeds the finite numerical range")
    if isinstance(value, dict):
        for key, item in value.items():
            _assert_finite(item, f"{name}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_finite(item, f"{name}[{index}]")


def _checked(values: dict[str, Any], *, model: str, assumptions: tuple[str, ...]) -> dict[str, Any]:
    _assert_finite(values)
    return {
        "model": model,
        "results": values,
        "assumptions": list(assumptions),
        "claim_boundary": "bounded analytical estimate; not FEA, CFD, certification, or physical validation",
    }


@dataclass(frozen=True)
class CantileverBeamInput:
    length_mm: float
    elastic_modulus_mpa: float
    second_moment_mm4: float
    tip_force_n: float = 0.0
    uniform_load_n_per_mm: float = 0.0
    section_modulus_mm3: float | None = None
    yield_strength_mpa: float | None = None
    safety_factor: float = 1.0


def cantilever_beam(request: CantileverBeamInput) -> dict[str, Any]:
    """Euler-Bernoulli cantilever under signed tip and uniform transverse loads."""

    length = _positive(request.length_mm, "length_mm")
    modulus = _positive(request.elastic_modulus_mpa, "elastic_modulus_mpa")
    inertia = _positive(request.second_moment_mm4, "second_moment_mm4")
    force = _finite(request.tip_force_n, "tip_force_n")
    distributed = _finite(request.uniform_load_n_per_mm, "uniform_load_n_per_mm")
    section_modulus = _optional_positive(request.section_modulus_mm3, "section_modulus_mm3")
    yield_strength = _optional_positive(request.yield_strength_mpa, "yield_strength_mpa")
    safety = _positive(request.safety_factor, "safety_factor")
    if yield_strength is not None and section_modulus is None:
        raise ValueError("yield_strength_mpa requires section_modulus_mm3")

    fixed_shear = force + distributed * length
    fixed_moment = force * length + distributed * length**2 / 2.0
    slope = force * length**2 / (2.0 * modulus * inertia) + distributed * length**3 / (6.0 * modulus * inertia)
    deflection = force * length**3 / (3.0 * modulus * inertia) + distributed * length**4 / (8.0 * modulus * inertia)
    stress = None if section_modulus is None else abs(fixed_moment) / section_modulus
    utilization = None
    passes = None
    if stress is not None and yield_strength is not None:
        allowable = yield_strength / safety
        utilization = stress / allowable
        passes = stress <= allowable
    return _checked(
        {
            "fixed_end_shear_n": fixed_shear,
            "fixed_end_moment_n_mm": fixed_moment,
            "tip_slope_radians": slope,
            "tip_deflection_mm": deflection,
            "maximum_bending_stress_mpa": stress,
            "yield_utilization": utilization,
            "constraint_satisfied": passes,
        },
        model="euler_bernoulli_cantilever_v1",
        assumptions=(
            "straight prismatic cantilever with an ideal fixed root",
            "linear elastic Euler-Bernoulli bending with small rotations and negligible shear deformation",
            "loads act in one bending plane; local stress concentrations, lateral-torsional buckling, fatigue, and dynamics are excluded",
        ),
    )


@dataclass(frozen=True)
class CombinedStressInput:
    normal_x_mpa: float
    normal_y_mpa: float
    normal_z_mpa: float
    shear_xy_mpa: float = 0.0
    shear_yz_mpa: float = 0.0
    shear_zx_mpa: float = 0.0
    yield_strength_mpa: float | None = None
    safety_factor: float = 1.0


def _principal_stresses(xx: float, yy: float, zz: float, xy: float, yz: float, zx: float) -> list[float]:
    if xy == 0.0 and yz == 0.0 and zx == 0.0:
        return sorted([xx, yy, zz], reverse=True)
    mean = (xx + yy + zz) / 3.0
    a = xx - mean
    b = yy - mean
    c = zz - mean
    p2 = (a * a + b * b + c * c + 2.0 * (xy * xy + yz * yz + zx * zx)) / 6.0
    if p2 <= 1e-30:
        return [mean, mean, mean]
    p = math.sqrt(p2)
    determinant = a * (b * c - yz * yz) - xy * (xy * c - yz * zx) + zx * (xy * yz - b * zx)
    r = max(-1.0, min(1.0, determinant / (2.0 * p**3)))
    angle = math.acos(r) / 3.0
    values = [
        mean + 2.0 * p * math.cos(angle),
        mean + 2.0 * p * math.cos(angle + 2.0 * math.pi / 3.0),
        mean + 2.0 * p * math.cos(angle + 4.0 * math.pi / 3.0),
    ]
    return sorted(values, reverse=True)


def combined_stress(request: CombinedStressInput) -> dict[str, Any]:
    """Principal and von Mises stress for a symmetric three-dimensional stress tensor."""

    xx = _finite(request.normal_x_mpa, "normal_x_mpa")
    yy = _finite(request.normal_y_mpa, "normal_y_mpa")
    zz = _finite(request.normal_z_mpa, "normal_z_mpa")
    xy = _finite(request.shear_xy_mpa, "shear_xy_mpa")
    yz = _finite(request.shear_yz_mpa, "shear_yz_mpa")
    zx = _finite(request.shear_zx_mpa, "shear_zx_mpa")
    yield_strength = _optional_positive(request.yield_strength_mpa, "yield_strength_mpa")
    safety = _positive(request.safety_factor, "safety_factor")
    principal = _principal_stresses(xx, yy, zz, xy, yz, zx)
    von_mises = math.sqrt(
        0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2) + 3.0 * (xy**2 + yz**2 + zx**2)
    )
    utilization = None if yield_strength is None else von_mises / (yield_strength / safety)
    return _checked(
        {
            "principal_stresses_mpa": principal,
            "maximum_principal_stress_mpa": principal[0],
            "minimum_principal_stress_mpa": principal[-1],
            "maximum_shear_stress_mpa": (principal[0] - principal[-1]) / 2.0,
            "hydrostatic_stress_mpa": (xx + yy + zz) / 3.0,
            "von_mises_stress_mpa": von_mises,
            "yield_utilization": utilization,
            "constraint_satisfied": None if yield_strength is None else von_mises <= yield_strength / safety,
        },
        model="combined_stress_3d_v1",
        assumptions=(
            "the supplied values form a symmetric Cauchy stress tensor at one material point",
            "von Mises utilization is applicable only to an isotropic ductile material with a supplied yield strength",
            "no stress gradients, concentrations, fatigue, fracture, buckling, or nonlinear material response are represented",
        ),
    )


@dataclass(frozen=True)
class ThermalNetworkInput:
    conductance_w_per_k: list[list[float]]
    heat_input_w: list[float]
    fixed_temperature_k: dict[str, float]
    node_labels: list[str] | None = None


def _solve_linear(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        scale = max(1.0, max(abs(value) for value in augmented[pivot][:-1]))
        if abs(augmented[pivot][column]) <= 1e-14 * scale:
            raise ValueError("thermal network is singular; every free node must be conductively connected to a fixed-temperature node")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [augmented[row][index] - factor * augmented[column][index] for index in range(size + 1)]
    return [augmented[index][-1] for index in range(size)]


def thermal_network(request: ThermalNetworkInput) -> dict[str, Any]:
    """Solve a steady linear thermal-resistance network with Dirichlet nodes."""

    conductance = request.conductance_w_per_k
    heat = request.heat_input_w
    if not isinstance(conductance, list) or len(conductance) < 2:
        raise ValueError("conductance_w_per_k must be a square matrix with at least two nodes")
    size = len(conductance)
    if not isinstance(heat, list) or len(heat) != size:
        raise ValueError("heat_input_w must have one value per node")
    checked_heat = [_finite(value, f"heat_input_w[{index}]") for index, value in enumerate(heat)]
    checked: list[list[float]] = []
    for row_index, raw_row in enumerate(conductance):
        if not isinstance(raw_row, list) or len(raw_row) != size:
            raise ValueError("conductance_w_per_k must be square")
        checked_row = [
            _positive(value, f"conductance_w_per_k[{row_index}][{column}]", allow_zero=True)
            for column, value in enumerate(raw_row)
        ]
        if checked_row[row_index] != 0:
            raise ValueError("conductance_w_per_k diagonal must be zero")
        checked.append(checked_row)
    for row in range(size):
        for column in range(row + 1, size):
            if not math.isclose(checked[row][column], checked[column][row], rel_tol=1e-12, abs_tol=1e-15):
                raise ValueError("conductance_w_per_k must be symmetric")
    if not isinstance(request.fixed_temperature_k, dict) or not request.fixed_temperature_k:
        raise ValueError("fixed_temperature_k requires at least one fixed node")
    fixed: dict[int, float] = {}
    for raw_index, value in request.fixed_temperature_k.items():
        if not isinstance(raw_index, str) or not raw_index.isdigit():
            raise ValueError("fixed_temperature_k keys must be decimal node indices")
        index = int(raw_index)
        if not 0 <= index < size:
            raise ValueError(f"fixed_temperature_k node {index} is outside the network")
        fixed[index] = _positive(value, f"fixed_temperature_k.{raw_index}")
    labels = request.node_labels
    if labels is None:
        node_labels = [f"node_{index}" for index in range(size)]
    else:
        if not isinstance(labels, list) or len(labels) != size or any(not isinstance(item, str) or not item.strip() for item in labels):
            raise ValueError("node_labels must contain one non-empty string per node")
        if len(set(labels)) != size:
            raise ValueError("node_labels must be unique")
        node_labels = [item.strip() for item in labels]

    free = [index for index in range(size) if index not in fixed]
    temperatures: list[float | None] = [None] * size
    for index, value in fixed.items():
        temperatures[index] = value
    if free:
        matrix: list[list[float]] = []
        vector: list[float] = []
        for row_node in free:
            matrix.append(
                [sum(checked[row_node]) if column_node == row_node else -checked[row_node][column_node] for column_node in free]
            )
            vector.append(checked_heat[row_node] + sum(checked[row_node][node] * value for node, value in fixed.items()))
        solved = _solve_linear(matrix, vector)
        for index, value in zip(free, solved, strict=True):
            if value <= 0:
                raise ValueError("thermal network solution produced a non-positive absolute temperature")
            temperatures[index] = value
    resolved = [float(value) for value in temperatures if value is not None]
    if len(resolved) != size:  # pragma: no cover - defensive guard
        raise RuntimeError("thermal network did not resolve every node")
    residuals = [sum(checked[node][other] * (resolved[node] - resolved[other]) for other in range(size)) - checked_heat[node] for node in range(size)]
    edge_flows = [
        {
            "from_node": node_labels[left],
            "to_node": node_labels[right],
            "heat_flow_w": checked[left][right] * (resolved[left] - resolved[right]),
        }
        for left in range(size)
        for right in range(left + 1, size)
        if checked[left][right] > 0
    ]
    fixed_external = {node_labels[index]: residuals[index] for index in sorted(fixed)}
    energy_residual = sum(checked_heat) + sum(fixed_external.values())
    return _checked(
        {
            "node_temperatures_k": {node_labels[index]: resolved[index] for index in range(size)},
            "edge_heat_flows_w": edge_flows,
            "fixed_node_external_heat_w": fixed_external,
            "maximum_free_node_balance_residual_w": max((abs(residuals[index]) for index in free), default=0.0),
            "network_energy_balance_residual_w": energy_residual,
        },
        model="steady_linear_thermal_network_v1",
        assumptions=(
            "steady linear network with constant symmetric pairwise conductances",
            "heat_input_w is positive into each node and fixed-temperature nodes exchange whatever boundary heat is required",
            "radiation, phase change, contact nonlinearities, temperature-dependent conductance, and spatial gradients within nodes are excluded",
        ),
    )


@dataclass(frozen=True)
class ForcedVibrationInput:
    mass_kg: float
    stiffness_n_m: float
    damping_n_s_m: float
    excitation_frequency_hz: float
    force_amplitude_n: float | None = None
    base_displacement_amplitude_mm: float | None = None
    resonance_warning_margin: float = 0.05


def forced_vibration(request: ForcedVibrationInput) -> dict[str, Any]:
    """Steady harmonic response of a viscously damped linear SDOF oscillator."""

    mass = _positive(request.mass_kg, "mass_kg")
    stiffness = _positive(request.stiffness_n_m, "stiffness_n_m")
    damping = _positive(request.damping_n_s_m, "damping_n_s_m", allow_zero=True)
    frequency = _positive(request.excitation_frequency_hz, "excitation_frequency_hz")
    force = _optional_positive(request.force_amplitude_n, "force_amplitude_n")
    base = _optional_positive(request.base_displacement_amplitude_mm, "base_displacement_amplitude_mm")
    margin_limit = _positive(request.resonance_warning_margin, "resonance_warning_margin", allow_zero=True)
    if (force is None) == (base is None):
        raise ValueError("provide exactly one of force_amplitude_n or base_displacement_amplitude_mm")
    omega = 2.0 * math.pi * frequency
    natural_omega = math.sqrt(stiffness / mass)
    natural_frequency = natural_omega / (2.0 * math.pi)
    critical_damping = 2.0 * math.sqrt(stiffness * mass)
    damping_ratio = damping / critical_damping
    frequency_ratio = omega / natural_omega
    denominator = math.hypot(stiffness - mass * omega**2, damping * omega)
    if denominator == 0:
        raise ValueError("undamped excitation at the exact natural frequency has no finite steady-state amplitude")
    resonance_margin = abs(frequency - natural_frequency) / natural_frequency
    results: dict[str, Any] = {
        "natural_frequency_hz": natural_frequency,
        "damping_ratio": damping_ratio,
        "frequency_ratio": frequency_ratio,
        "relative_frequency_margin": resonance_margin,
        "within_resonance_warning_band": resonance_margin <= margin_limit,
    }
    if force is not None:
        amplitude_m = force / denominator
        results.update(
            {
                "excitation_type": "harmonic_force",
                "displacement_amplitude_mm": amplitude_m * 1_000.0,
                "response_phase_lag_radians": math.atan2(damping * omega, stiffness - mass * omega**2),
                "dynamic_magnification_factor": amplitude_m / (force / stiffness),
            }
        )
    else:
        assert base is not None
        base_m = base * 1e-3
        relative_amplitude_m = base_m * mass * omega**2 / denominator
        absolute_amplitude_m = base_m * math.hypot(stiffness, damping * omega) / denominator
        results.update(
            {
                "excitation_type": "harmonic_base_displacement",
                "relative_displacement_amplitude_mm": relative_amplitude_m * 1_000.0,
                "absolute_displacement_amplitude_mm": absolute_amplitude_m * 1_000.0,
                "displacement_transmissibility": absolute_amplitude_m / base_m,
            }
        )
    return _checked(
        results,
        model="forced_vibration_sdof_v1",
        assumptions=(
            "linear time-invariant single-degree-of-freedom mass, spring, and viscous damper",
            "steady sinusoidal response after transients have decayed",
            "no nonlinear stiffness, friction, multi-mode coupling, random excitation, fatigue, or structural stress recovery",
        ),
    )


@dataclass(frozen=True)
class PipeNetworkInput:
    density_kg_m3: float
    dynamic_viscosity_pa_s: float
    total_flow_m3_s: float
    series_segments: list[dict[str, Any]] = field(default_factory=list)
    parallel_branches: list[list[dict[str, Any]]] = field(default_factory=list)


_SEGMENT_KEYS = {
    "label",
    "length_mm",
    "diameter_mm",
    "roughness_mm",
    "minor_loss_coefficient",
    "darcy_friction_factor",
}


def _segment_loss(
    raw: Any,
    *,
    flow_m3_s: float,
    density: float,
    viscosity: float,
    name: str,
    require_explicit_factor: bool = False,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise TypeError(f"{name} must be an object")
    extra = sorted(set(raw) - _SEGMENT_KEYS)
    missing = sorted({"length_mm", "diameter_mm"} - set(raw))
    if extra or missing:
        raise ValueError(f"{name} requires length_mm and diameter_mm; unsupported={extra}, missing={missing}")
    label = raw.get("label", name)
    if not isinstance(label, str) or not label.strip() or len(label) > 128:
        raise ValueError(f"{name}.label must be a non-empty string of at most 128 characters")
    length_m = _positive(raw["length_mm"], f"{name}.length_mm") * 1e-3
    diameter_m = _positive(raw["diameter_mm"], f"{name}.diameter_mm") * 1e-3
    roughness_m = _positive(raw.get("roughness_mm", 0.0), f"{name}.roughness_mm", allow_zero=True) * 1e-3
    if roughness_m >= diameter_m / 2.0:
        raise ValueError(f"{name}.roughness_mm must be less than half the diameter")
    minor = _positive(raw.get("minor_loss_coefficient", 0.0), f"{name}.minor_loss_coefficient", allow_zero=True)
    supplied = raw.get("darcy_friction_factor")
    factor = None if supplied is None else _positive(supplied, f"{name}.darcy_friction_factor")
    if require_explicit_factor and factor is None:
        raise ValueError("parallel branch segments require an explicit darcy_friction_factor for deterministic flow balancing")
    area = math.pi * diameter_m**2 / 4.0
    velocity = flow_m3_s / area
    reynolds = density * abs(velocity) * diameter_m / viscosity
    if flow_m3_s == 0:
        regime = "stagnant"
        calculated_factor = factor
    elif factor is not None:
        regime = "user_factor"
        calculated_factor = factor
    elif reynolds < 2_300:
        regime = "laminar"
        calculated_factor = 64.0 / reynolds
    elif reynolds < 4_000:
        raise ValueError(f"{name} is transitional and requires an explicit darcy_friction_factor")
    else:
        regime = "turbulent_swamee_jain"
        calculated_factor = 0.25 / math.log10(roughness_m / (3.7 * diameter_m) + 5.74 / reynolds**0.9) ** 2
    pressure_loss = 0.0 if calculated_factor is None else (calculated_factor * length_m / diameter_m + minor) * density * velocity**2 / 2.0
    return {
        "label": label.strip(),
        "flow_m3_s": flow_m3_s,
        "velocity_m_s": velocity,
        "reynolds_number": reynolds,
        "flow_regime": regime,
        "darcy_friction_factor": calculated_factor,
        "pressure_loss_pa": pressure_loss,
    }


def _branch_loss(branch: list[dict[str, Any]], flow: float, density: float, viscosity: float, name: str) -> tuple[float, list[dict[str, Any]]]:
    segments = [
        _segment_loss(
            segment,
            flow_m3_s=flow,
            density=density,
            viscosity=viscosity,
            name=f"{name}[{index}]",
            require_explicit_factor=True,
        )
        for index, segment in enumerate(branch)
    ]
    return sum(float(segment["pressure_loss_pa"]) for segment in segments), segments


def pipe_network(request: PipeNetworkInput) -> dict[str, Any]:
    """Darcy-Weisbach pressure loss for series segments and one parallel bank."""

    density = _positive(request.density_kg_m3, "density_kg_m3")
    viscosity = _positive(request.dynamic_viscosity_pa_s, "dynamic_viscosity_pa_s")
    total_flow = _positive(request.total_flow_m3_s, "total_flow_m3_s", allow_zero=True)
    series = request.series_segments
    branches = request.parallel_branches
    if not isinstance(series, list) or not isinstance(branches, list):
        raise TypeError("series_segments and parallel_branches must be lists")
    if not series and not branches:
        raise ValueError("pipe network requires at least one series segment or a parallel branch bank")
    if branches and len(branches) < 2:
        raise ValueError("parallel_branches must contain at least two branches")
    if any(not isinstance(branch, list) or not branch for branch in branches):
        raise ValueError("every parallel branch must contain at least one segment")

    series_results = [
        _segment_loss(segment, flow_m3_s=total_flow, density=density, viscosity=viscosity, name=f"series_segments[{index}]")
        for index, segment in enumerate(series)
    ]
    series_loss = sum(float(segment["pressure_loss_pa"]) for segment in series_results)
    branch_results: list[dict[str, Any]] = []
    parallel_loss = 0.0
    if branches:
        if total_flow == 0:
            branch_flows = [0.0] * len(branches)
        else:
            high = max(_branch_loss(branch, total_flow, density, viscosity, f"parallel_branches[{index}]")[0] for index, branch in enumerate(branches))
            low = 0.0
            for _ in range(100):
                pressure = (low + high) / 2.0
                candidate_flows = []
                for index, branch in enumerate(branches):
                    branch_low, branch_high = 0.0, total_flow
                    for _ in range(80):
                        candidate = (branch_low + branch_high) / 2.0
                        loss, _ = _branch_loss(branch, candidate, density, viscosity, f"parallel_branches[{index}]")
                        if loss < pressure:
                            branch_low = candidate
                        else:
                            branch_high = candidate
                    candidate_flows.append((branch_low + branch_high) / 2.0)
                if sum(candidate_flows) < total_flow:
                    low = pressure
                else:
                    high = pressure
            parallel_loss = (low + high) / 2.0
            branch_flows = []
            for index, branch in enumerate(branches):
                branch_low, branch_high = 0.0, total_flow
                for _ in range(100):
                    candidate = (branch_low + branch_high) / 2.0
                    loss, _ = _branch_loss(branch, candidate, density, viscosity, f"parallel_branches[{index}]")
                    if loss < parallel_loss:
                        branch_low = candidate
                    else:
                        branch_high = candidate
                branch_flows.append((branch_low + branch_high) / 2.0)
            correction = total_flow / sum(branch_flows)
            branch_flows = [flow * correction for flow in branch_flows]
        for index, (branch, flow) in enumerate(zip(branches, branch_flows, strict=True)):
            loss, segment_results = _branch_loss(branch, flow, density, viscosity, f"parallel_branches[{index}]")
            branch_results.append(
                {
                    "branch_index": index,
                    "flow_m3_s": flow,
                    "pressure_loss_pa": loss,
                    "segments": segment_results,
                }
            )
        parallel_loss = sum(float(branch["pressure_loss_pa"]) for branch in branch_results) / len(branch_results)
    total_loss = series_loss + parallel_loss
    return _checked(
        {
            "series_pressure_loss_pa": series_loss,
            "parallel_bank_pressure_loss_pa": parallel_loss,
            "total_pressure_loss_pa": total_loss,
            "hydraulic_power_w": total_loss * total_flow,
            "series_segments": series_results,
            "parallel_branches": branch_results,
            "parallel_flow_balance_residual_m3_s": sum(float(branch["flow_m3_s"]) for branch in branch_results) - total_flow if branches else 0.0,
            "parallel_pressure_spread_pa": (
                max(float(branch["pressure_loss_pa"]) for branch in branch_results)
                - min(float(branch["pressure_loss_pa"]) for branch in branch_results)
                if branch_results
                else 0.0
            ),
        },
        model="darcy_weisbach_pipe_network_v1",
        assumptions=(
            "steady incompressible single-phase flow in circular pipes with one series path and at most one parallel branch bank",
            "parallel balancing uses user-supplied constant Darcy factors so the branch loss remains monotonic across trial flows",
            "no pump curve, elevation head, compressibility, heat transfer, cavitation, water hammer, leakage, or network loops are represented",
        ),
    )


@dataclass(frozen=True)
class ElectroThermalWireInput:
    length_mm: float
    area_mm2: float
    resistivity_ohm_m: float
    current_a: float
    thermal_resistance_k_per_w: float
    ambient_temperature_k: float
    resistance_temperature_coefficient_per_k: float = 0.0
    expansion_coefficient_per_k: float = 0.0
    elastic_modulus_mpa: float | None = None
    yield_strength_mpa: float | None = None
    safety_factor: float = 1.0


def electro_thermal_wire(request: ElectroThermalWireInput) -> dict[str, Any]:
    """Self-consistent lumped Joule heating with optional restrained thermal stress."""

    length_mm = _positive(request.length_mm, "length_mm")
    area_mm2 = _positive(request.area_mm2, "area_mm2")
    resistivity = _positive(request.resistivity_ohm_m, "resistivity_ohm_m")
    current = _positive(request.current_a, "current_a", allow_zero=True)
    thermal_resistance = _positive(request.thermal_resistance_k_per_w, "thermal_resistance_k_per_w")
    ambient = _positive(request.ambient_temperature_k, "ambient_temperature_k")
    temperature_coefficient = _finite(request.resistance_temperature_coefficient_per_k, "resistance_temperature_coefficient_per_k")
    expansion_coefficient = _finite(request.expansion_coefficient_per_k, "expansion_coefficient_per_k")
    modulus = _optional_positive(request.elastic_modulus_mpa, "elastic_modulus_mpa")
    yield_strength = _optional_positive(request.yield_strength_mpa, "yield_strength_mpa")
    safety = _positive(request.safety_factor, "safety_factor")
    if yield_strength is not None and modulus is None:
        raise ValueError("yield_strength_mpa requires elastic_modulus_mpa")
    cold_resistance = resistivity * (length_mm * 1e-3) / (area_mm2 * 1e-6)
    feedback = current**2 * cold_resistance * thermal_resistance * temperature_coefficient
    if feedback >= 1.0:
        raise ValueError("linear electro-thermal feedback has no finite stable equilibrium because its loop gain is at least one")
    temperature_rise = current**2 * cold_resistance * thermal_resistance / (1.0 - feedback)
    hot_resistance = cold_resistance * (1.0 + temperature_coefficient * temperature_rise)
    if hot_resistance <= 0:
        raise ValueError("linear temperature coefficient predicts non-positive resistance outside its applicable range")
    heat = current**2 * hot_resistance
    thermal_strain = expansion_coefficient * temperature_rise
    restrained_stress = None if modulus is None else -modulus * thermal_strain
    utilization = None
    passes = None
    if yield_strength is not None and restrained_stress is not None:
        utilization = abs(restrained_stress) / (yield_strength / safety)
        passes = abs(restrained_stress) <= yield_strength / safety
    return _checked(
        {
            "cold_resistance_ohm": cold_resistance,
            "hot_resistance_ohm": hot_resistance,
            "voltage_drop_v": current * hot_resistance,
            "current_density_a_per_mm2": current / area_mm2,
            "joule_heat_w": heat,
            "temperature_rise_k": temperature_rise,
            "equilibrium_temperature_k": ambient + temperature_rise,
            "electro_thermal_loop_gain": feedback,
            "free_expansion_mm": length_mm * thermal_strain,
            "fully_restrained_stress_mpa": restrained_stress,
            "yield_utilization": utilization,
            "constraint_satisfied": passes,
        },
        model="lumped_electro_thermal_wire_v1",
        assumptions=(
            "uniform conductor cross-section and temperature with constant thermal resistance to a fixed ambient",
            "resistance varies linearly with temperature and the reported loop gain must remain below one",
            "optional mechanical output is one-dimensional linear-elastic full restraint; radiation, contact resistance, creep, and thermal gradients are excluded",
        ),
    )
