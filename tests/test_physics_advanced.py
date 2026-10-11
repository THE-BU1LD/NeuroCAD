from __future__ import annotations

import json
import math

import pytest

from core.physics_advanced import (
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
from core.physics_uncertainty import propagate_uncertainty
from neurocad_cli import build_parser


def _write_agent_project(path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "neurocad-agent-project-v1",
                "project_id": "wire-project",
                "revision": 1,
                "plan": {
                    "version": "neurocad-agent-plan-v1",
                    "title": "Bound wire",
                    "summary": "A cylinder used for an exact wire binding.",
                    "assumptions": [],
                    "components": [
                        {
                            "id": "wire",
                            "label": "Wire",
                            "part": "wire",
                            "operation": "add",
                            "shape": "cylinder",
                            "parameters": {"radius": 10.0, "height": 100.0},
                            "translate": [0.0, 0.0, 50.0],
                            "rotate": [0.0, 0.0, 0.0],
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )


def test_cantilever_beam_combines_tip_and_distributed_loads() -> None:
    result = cantilever_beam(
        CantileverBeamInput(
            length_mm=1_000,
            elastic_modulus_mpa=200_000,
            second_moment_mm4=1_000_000,
            tip_force_n=1_000,
            section_modulus_mm3=10_000,
            yield_strength_mpa=250,
            safety_factor=2,
        )
    )["results"]
    assert result["fixed_end_shear_n"] == pytest.approx(1_000)
    assert result["fixed_end_moment_n_mm"] == pytest.approx(1_000_000)
    assert result["tip_deflection_mm"] == pytest.approx(5 / 3)
    assert result["maximum_bending_stress_mpa"] == pytest.approx(100)
    assert result["yield_utilization"] == pytest.approx(0.8)
    assert result["constraint_satisfied"] is True


def test_combined_stress_matches_uniaxial_and_hydrostatic_invariants() -> None:
    uniaxial = combined_stress(CombinedStressInput(100, 0, 0, yield_strength_mpa=250, safety_factor=2))["results"]
    assert uniaxial["principal_stresses_mpa"] == pytest.approx([100, 0, 0])
    assert uniaxial["von_mises_stress_mpa"] == pytest.approx(100)
    assert uniaxial["maximum_shear_stress_mpa"] == pytest.approx(50)
    assert uniaxial["constraint_satisfied"] is True
    hydrostatic = combined_stress(CombinedStressInput(-20, -20, -20))["results"]
    assert hydrostatic["von_mises_stress_mpa"] == pytest.approx(0)
    assert hydrostatic["principal_stresses_mpa"] == pytest.approx([-20, -20, -20])


def test_thermal_network_solves_and_closes_energy_balance() -> None:
    result = thermal_network(
        ThermalNetworkInput(
            conductance_w_per_k=[[0, 10], [10, 0]],
            heat_input_w=[0, 100],
            fixed_temperature_k={"0": 300},
            node_labels=["ambient", "device"],
        )
    )["results"]
    assert result["node_temperatures_k"] == pytest.approx({"ambient": 300, "device": 310})
    assert result["fixed_node_external_heat_w"]["ambient"] == pytest.approx(-100)
    assert result["maximum_free_node_balance_residual_w"] == pytest.approx(0, abs=1e-12)
    assert result["network_energy_balance_residual_w"] == pytest.approx(0, abs=1e-12)
    with pytest.raises(ValueError, match="singular"):
        thermal_network(ThermalNetworkInput([[0, 0], [0, 0]], [0, 10], {"0": 300}))


def test_forced_vibration_reports_force_and_base_response() -> None:
    force = forced_vibration(ForcedVibrationInput(1, 100, 2, 1, force_amplitude_n=10))["results"]
    omega = 2 * math.pi
    denominator = math.hypot(100 - omega**2, 2 * omega)
    assert force["displacement_amplitude_mm"] == pytest.approx(10 / denominator * 1_000)
    assert force["dynamic_magnification_factor"] == pytest.approx((10 / denominator) / 0.1)
    base = forced_vibration(ForcedVibrationInput(1, 100, 2, 1, base_displacement_amplitude_mm=1))["results"]
    assert base["excitation_type"] == "harmonic_base_displacement"
    assert base["displacement_transmissibility"] == pytest.approx(math.hypot(100, 2 * omega) / denominator)
    with pytest.raises(ValueError, match="exactly one"):
        forced_vibration(ForcedVibrationInput(1, 100, 2, 1))


def test_pipe_network_balances_identical_parallel_branches() -> None:
    segment = {
        "length_mm": 1_000,
        "diameter_mm": 20,
        "darcy_friction_factor": 0.02,
        "minor_loss_coefficient": 1.0,
    }
    result = pipe_network(
        PipeNetworkInput(
            density_kg_m3=1_000,
            dynamic_viscosity_pa_s=0.001,
            total_flow_m3_s=0.002,
            parallel_branches=[[segment], [segment]],
        )
    )["results"]
    assert [branch["flow_m3_s"] for branch in result["parallel_branches"]] == pytest.approx([0.001, 0.001])
    assert result["parallel_flow_balance_residual_m3_s"] == pytest.approx(0, abs=1e-15)
    assert result["parallel_pressure_spread_pa"] == pytest.approx(0, abs=1e-9)
    assert result["hydraulic_power_w"] == pytest.approx(result["total_pressure_loss_pa"] * 0.002)


def test_pipe_network_auto_friction_and_fail_closed_transition() -> None:
    laminar = pipe_network(
        PipeNetworkInput(
            density_kg_m3=1_000,
            dynamic_viscosity_pa_s=0.001,
            total_flow_m3_s=math.pi * 0.01**2 / 4 * 0.1,
            series_segments=[{"length_mm": 1_000, "diameter_mm": 10}],
        )
    )["results"]["series_segments"][0]
    assert laminar["reynolds_number"] == pytest.approx(1_000)
    assert laminar["darcy_friction_factor"] == pytest.approx(0.064)
    transitional_flow = math.pi * 0.01**2 / 4 * 0.003 * 1_000 / (1_000 * 0.01)
    with pytest.raises(ValueError, match="transitional"):
        pipe_network(PipeNetworkInput(1_000, 0.001, transitional_flow, [{"length_mm": 1_000, "diameter_mm": 10}]))


def test_electro_thermal_wire_solves_feedback_and_restrained_stress() -> None:
    request = ElectroThermalWireInput(
        length_mm=1_000,
        area_mm2=1,
        resistivity_ohm_m=1.7e-8,
        current_a=10,
        thermal_resistance_k_per_w=2,
        ambient_temperature_k=300,
        resistance_temperature_coefficient_per_k=0.004,
        expansion_coefficient_per_k=12e-6,
        elastic_modulus_mpa=200_000,
        yield_strength_mpa=250,
        safety_factor=2,
    )
    result = electro_thermal_wire(request)["results"]
    assert result["cold_resistance_ohm"] == pytest.approx(0.017)
    assert result["electro_thermal_loop_gain"] == pytest.approx(0.0136)
    assert result["temperature_rise_k"] == pytest.approx(3.4 / (1 - 0.0136))
    assert result["joule_heat_w"] * 2 == pytest.approx(result["temperature_rise_k"])
    assert result["constraint_satisfied"] is True
    with pytest.raises(ValueError, match="loop gain"):
        electro_thermal_wire(ElectroThermalWireInput(1_000, 1, 1e-6, 100, 10, 300, 0.01))


def test_uncertainty_interval_monte_carlo_and_local_sensitivity_are_deterministic() -> None:
    base = {
        "length_mm": 1_000,
        "elastic_modulus_mpa": 200_000,
        "second_moment_mm4": 1_000_000,
        "tip_force_n": 1_000,
    }
    interval = propagate_uncertainty(
        CantileverBeamInput,
        cantilever_beam,
        base,
        {
            "method": "interval",
            "inputs": {"tip_force_n": {"lower": 900, "upper": 1_100}},
            "outputs": ["tip_deflection_mm"],
        },
    )
    envelope = interval["result_envelopes"]["tip_deflection_mm"]
    assert interval["evaluation_count"] == 2
    assert envelope["minimum"] == pytest.approx(1.5)
    assert envelope["maximum"] == pytest.approx(11 / 6)
    monte_carlo_spec = {
        "method": "monte_carlo",
        "inputs": {"tip_force_n": {"lower": 900, "upper": 1_100}},
        "outputs": ["tip_deflection_mm"],
        "samples": 20,
        "seed": 42,
    }
    first = propagate_uncertainty(CantileverBeamInput, cantilever_beam, base, monte_carlo_spec)
    second = propagate_uncertainty(CantileverBeamInput, cantilever_beam, base, monte_carlo_spec)
    assert first == second
    local = propagate_uncertainty(
        CantileverBeamInput,
        cantilever_beam,
        base,
        {
            "method": "local_sensitivity",
            "inputs": {"tip_force_n": {"lower": 900, "upper": 1_100}},
            "outputs": ["tip_deflection_mm"],
        },
    )
    assert local["local_derivatives"]["tip_force_n"]["derivatives"]["tip_deflection_mm"] == pytest.approx(1 / 600)


def test_physics_v3_context_interpolates_combines_binds_and_builds_uniform_overlay(tmp_path, capsys) -> None:
    project = tmp_path / "project.json"
    _write_agent_project(project)
    source = tmp_path / "request.json"
    source.write_text(
        json.dumps(
            {
                "model": "electro_thermal_wire",
                "inputs": {
                    "length_mm": 100,
                    "area_mm2": math.pi * 100,
                    "resistivity_ohm_m": 1.85e-8,
                    "current_a": 5,
                    "thermal_resistance_k_per_w": 2,
                    "ambient_temperature_k": 300,
                    "resistance_temperature_coefficient_per_k": 0.004,
                },
                "context": {
                    "schema_version": "neurocad-physics-context-v2",
                    "geometry": {"agent_project": "project.json", "component_id": "wire"},
                    "material": {
                        "schema_version": "neurocad-material-card-v2",
                        "material_id": "temperature-aware-conductor",
                        "revision": 1,
                        "source": "Declared test fixture, not an authoritative material database.",
                        "properties": {"density_kg_m3": 8_000},
                        "temperature_tables": {
                            "resistivity_ohm_m": [
                                {"temperature_k": 300, "value": 1.7e-8},
                                {"temperature_k": 400, "value": 2.0e-8},
                            ]
                        },
                        "evaluation_temperature_k": 350,
                    },
                    "load_cases": [
                        {
                            "schema_version": "neurocad-load-case-v1",
                            "case_id": "service",
                            "coordinate_system": "component-local",
                            "source": "Declared service current.",
                            "values": {"current_a": 4},
                        },
                        {
                            "schema_version": "neurocad-load-case-v1",
                            "case_id": "increment",
                            "coordinate_system": "component-local",
                            "source": "Declared current increment.",
                            "values": {"current_a": 2},
                        },
                    ],
                    "load_combination": {
                        "schema_version": "neurocad-load-combination-v1",
                        "combination_id": "service-plus-half-increment",
                        "source": "Declared algebraic test combination.",
                        "coefficients": {"service": 1, "increment": 0.5},
                    },
                },
                "uncertainty": {
                    "method": "interval",
                    "inputs": {"current_a": {"lower": 4.5, "upper": 5.5}},
                    "outputs": ["temperature_rise_k"],
                },
            }
        ),
        encoding="utf-8",
    )
    args = build_parser().parse_args(["physics", str(source)])
    assert args.func(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == "neurocad-physics-v3"
    assert report["bindings"]["material"]["resolved_properties"]["resistivity_ohm_m"] == pytest.approx(1.85e-8)
    assert report["bindings"]["material"]["interpolated_properties"] == ["resistivity_ohm_m"]
    assert report["bindings"]["load_combination"]["combined_values"]["current_a"] == pytest.approx(5)
    assert report["bindings"]["geometry"]["model_inputs_checked"] == ["area_mm2", "length_mm"]
    assert report["uncertainty"]["evaluation_count"] == 2
    assert report["overlay"]["component_id"] == "wire"
    assert report["overlay"]["spatial_field"] is False
    assert report["overlay"]["status"] == "not_evaluated"
    assert len(report["overlay"]["overlay_sha256"]) == 64


def test_physics_v3_context_refuses_material_extrapolation_and_mixed_coordinates(tmp_path) -> None:
    base = {
        "model": "electro_thermal_wire",
        "inputs": {
            "length_mm": 100,
            "area_mm2": 1,
            "resistivity_ohm_m": 1.7e-8,
            "current_a": 1,
            "thermal_resistance_k_per_w": 1,
            "ambient_temperature_k": 300,
        },
        "context": {
            "schema_version": "neurocad-physics-context-v2",
            "material": {
                "schema_version": "neurocad-material-card-v2",
                "material_id": "test",
                "revision": 1,
                "source": "Declared test fixture.",
                "temperature_tables": {
                    "resistivity_ohm_m": [
                        {"temperature_k": 300, "value": 1.7e-8},
                        {"temperature_k": 400, "value": 2e-8},
                    ]
                },
                "evaluation_temperature_k": 500,
            },
        },
    }
    source = tmp_path / "bad.json"
    source.write_text(json.dumps(base), encoding="utf-8")
    with pytest.raises(ValueError, match="extrapolation"):
        build_parser().parse_args(["physics", str(source)]).func(build_parser().parse_args(["physics", str(source)]))

    base["context"] = {
        "schema_version": "neurocad-physics-context-v2",
        "load_cases": [
            {
                "schema_version": "neurocad-load-case-v1",
                "case_id": "a",
                "coordinate_system": "local",
                "source": "test a",
                "values": {"current_a": 1},
            },
            {
                "schema_version": "neurocad-load-case-v1",
                "case_id": "b",
                "coordinate_system": "world",
                "source": "test b",
                "values": {"current_a": 1},
            },
        ],
        "load_combination": {
            "schema_version": "neurocad-load-combination-v1",
            "combination_id": "bad",
            "source": "test",
            "coefficients": {"a": 1, "b": 1},
        },
    }
    base["inputs"]["current_a"] = 2
    source.write_text(json.dumps(base), encoding="utf-8")
    with pytest.raises(ValueError, match="same coordinate_system"):
        build_parser().parse_args(["physics", str(source)]).func(build_parser().parse_args(["physics", str(source)]))
