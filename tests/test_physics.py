from __future__ import annotations

import json
import math

import pytest

from core.physics import (
    EulerBucklingInput,
    InternalPipeFlowInput,
    SteadyConductionInput,
    ThermalExpansionInput,
    ThinWallCylinderInput,
    euler_buckling,
    internal_pipe_flow,
    steady_conduction,
    thermal_expansion,
    thin_wall_cylinder,
)
from neurocad_cli import build_parser, main


def test_euler_buckling_reports_constraint_and_slenderness() -> None:
    report = euler_buckling(
        EulerBucklingInput(
            elastic_modulus_mpa=200_000,
            second_moment_mm4=1_000,
            effective_length_mm=1_000,
            area_mm2=100,
            applied_load_n=900,
            safety_factor=2,
        )
    )
    result = report["results"]
    assert result["critical_load_n"] == pytest.approx(math.pi**2 * 200)
    assert result["allowable_load_n"] == pytest.approx(math.pi**2 * 100)
    assert result["radius_of_gyration_mm"] == pytest.approx(math.sqrt(10))
    assert result["constraint_satisfied"] is True


def test_thermal_expansion_reports_free_and_fully_restrained_cases() -> None:
    report = thermal_expansion(
        ThermalExpansionInput(
            length_mm=100,
            coefficient_per_k=12e-6,
            delta_temperature_k=50,
            elastic_modulus_mpa=200_000,
            area_mm2=10,
            yield_strength_mpa=250,
            safety_factor=2,
        )
    )
    result = report["results"]
    assert result["free_expansion_mm"] == pytest.approx(0.06)
    assert result["fully_restrained_stress_mpa"] == pytest.approx(-120)
    assert result["fully_restrained_reaction_n"] == pytest.approx(-1_200)
    assert result["yield_utilization"] == pytest.approx(0.96)
    assert result["constraint_satisfied"] is True


def test_steady_conduction_preserves_declared_unit_conversions() -> None:
    report = steady_conduction(
        SteadyConductionInput(
            conductivity_w_mk=200,
            area_mm2=1_000,
            thickness_mm=10,
            delta_temperature_k=50,
        )
    )
    result = report["results"]
    assert result["thermal_resistance_k_per_w"] == pytest.approx(0.05)
    assert result["heat_rate_w"] == pytest.approx(1_000)
    assert result["heat_flux_w_m2"] == pytest.approx(1_000_000)


def test_pipe_flow_uses_laminar_factor_and_requires_turbulent_input() -> None:
    laminar = internal_pipe_flow(
        InternalPipeFlowInput(
            density_kg_m3=1_000,
            dynamic_viscosity_pa_s=0.001,
            velocity_m_s=0.1,
            diameter_mm=10,
            length_mm=1_000,
        )
    )["results"]
    assert laminar["reynolds_number"] == pytest.approx(1_000)
    assert laminar["darcy_friction_factor"] == pytest.approx(0.064)
    assert laminar["major_pressure_loss_pa"] == pytest.approx(32)
    with pytest.raises(ValueError, match="requires an explicit"):
        internal_pipe_flow(
            InternalPipeFlowInput(
                density_kg_m3=1_000,
                dynamic_viscosity_pa_s=0.001,
                velocity_m_s=1,
                diameter_mm=10,
                length_mm=1_000,
            )
        )


def test_thin_wall_pressure_model_enforces_applicability() -> None:
    result = thin_wall_cylinder(
        ThinWallCylinderInput(
            internal_pressure_mpa=1,
            mean_radius_mm=100,
            wall_thickness_mm=5,
            yield_strength_mpa=100,
            safety_factor=2,
        )
    )["results"]
    assert result["hoop_stress_mpa"] == pytest.approx(20)
    assert result["longitudinal_stress_mpa"] == pytest.approx(10)
    assert result["plane_stress_von_mises_mpa"] == pytest.approx(math.sqrt(300))
    assert result["constraint_satisfied"] is True
    with pytest.raises(ValueError, match="requires mean_radius_mm"):
        thin_wall_cylinder(ThinWallCylinderInput(1, 20, 4))


def test_physics_cli_writes_versioned_auditable_report(tmp_path, capsys) -> None:
    source = tmp_path / "physics.json"
    source.write_text(
        json.dumps(
            {
                "model": "steady_conduction",
                "inputs": {
                    "conductivity_w_mk": 200,
                    "area_mm2": 1_000,
                    "thickness_mm": 10,
                    "delta_temperature_k": 50,
                },
            }
        ),
        encoding="utf-8",
    )
    args = build_parser().parse_args(["physics", str(source)])
    assert args.func(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == "neurocad-physics-v1"
    assert report["model"] == "steady_1d_conduction_v1"
    assert "not simulation" in report["claim_boundary"]


def test_physics_command_routes_through_main_without_daemon(tmp_path, capsys) -> None:
    source = tmp_path / "physics.json"
    source.write_text(
        json.dumps(
            {
                "model": "thin_wall_cylinder",
                "inputs": {
                    "internal_pressure_mpa": 1,
                    "mean_radius_mm": 100,
                    "wall_thickness_mm": 5,
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as stopped:
        main(["physics", str(source)])
    assert stopped.value.code == 0
    assert json.loads(capsys.readouterr().out)["requested_model"] == "thin_wall_cylinder"


@pytest.mark.parametrize(
    "model_input",
    [
        EulerBucklingInput(True, 1, 1),
        ThermalExpansionInput(1, float("nan"), 1),
        SteadyConductionInput(1, 0, 1, 1),
        InternalPipeFlowInput(1, 1, -1, 1, 1),
        ThinWallCylinderInput(1, 1, 0),
    ],
)
def test_physics_models_reject_nonphysical_or_nonfinite_inputs(model_input: object) -> None:
    evaluator = {
        EulerBucklingInput: euler_buckling,
        ThermalExpansionInput: thermal_expansion,
        SteadyConductionInput: steady_conduction,
        InternalPipeFlowInput: internal_pipe_flow,
        ThinWallCylinderInput: thin_wall_cylinder,
    }[type(model_input)]
    with pytest.raises((TypeError, ValueError)):
        evaluator(model_input)
