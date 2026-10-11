from __future__ import annotations

import json
import math

import pytest

from core.agentic import AgentComponent
from core.physics import (
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
from core.physics_context import (
    StalePhysicsBindingError,
    component_geometry_sha256,
)
from neurocad_cli import build_parser, main


def _write_agent_project(path, *, radius: float = 10.0, revision: int = 1) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "neurocad-agent-project-v1",
                "project_id": "shaft-project",
                "revision": revision,
                "plan": {
                    "version": "neurocad-agent-plan-v1",
                    "title": "Bound shaft",
                    "summary": "A primitive used to test traceable physics bindings.",
                    "assumptions": [],
                    "components": [
                        {
                            "id": "shaft",
                            "label": "Shaft",
                            "part": "shaft",
                            "operation": "add",
                            "shape": "cylinder",
                            "parameters": {"radius": radius, "height": 100.0},
                            "translate": [0.0, 0.0, 50.0],
                            "rotate": [0.0, 0.0, 0.0],
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )


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


def test_steady_convection_reports_signed_surface_heat_transfer() -> None:
    result = steady_convection(SteadyConvectionInput(25, 20_000, 350, 295))["results"]
    assert result["surface_to_fluid_delta_temperature_k"] == pytest.approx(55)
    assert result["heat_flux_surface_to_fluid_w_m2"] == pytest.approx(1_375)
    assert result["heat_rate_surface_to_fluid_w"] == pytest.approx(27.5)
    assert result["thermal_resistance_k_per_w"] == pytest.approx(2)


def test_radiative_exchange_uses_absolute_temperature_and_signed_direction() -> None:
    result = radiative_exchange(RadiativeExchangeInput(0.85, 20_000, 500, 295))["results"]
    expected_flux = 0.85 * 5.670374419e-8 * (500**4 - 295**4)
    assert result["heat_flux_surface_to_surroundings_w_m2"] == pytest.approx(expected_flux)
    assert result["heat_rate_surface_to_surroundings_w"] == pytest.approx(expected_flux * 0.02)
    reverse = radiative_exchange(RadiativeExchangeInput(0.85, 20_000, 295, 500))["results"]
    assert reverse["heat_rate_surface_to_surroundings_w"] < 0


def test_lumped_thermal_transient_reports_biot_gate_and_exponential_cooling() -> None:
    request = LumpedThermalTransientInput(2_700, 900, 100_000, 12_000, 20, 205, 400, 295, 300)
    result = lumped_thermal_transient(request)["results"]
    mass = 2_700 * 100_000e-9
    time_constant = mass * 900 / (20 * 12_000e-6)
    expected_ratio = math.exp(-300 / time_constant)
    assert result["biot_number"] == pytest.approx(20 * (100_000e-9 / 12_000e-6) / 205)
    assert result["temperature_ratio"] == pytest.approx(expected_ratio)
    assert result["temperature_k"] == pytest.approx(295 + (400 - 295) * expected_ratio)
    with pytest.raises(ValueError, match="Biot number <= 0.1"):
        lumped_thermal_transient(LumpedThermalTransientInput(1_000, 1_000, 1e6, 100, 100, 0.1, 400, 300, 1))


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


def test_hydrostatic_buoyancy_reports_pressure_force_and_apparent_weight() -> None:
    result = hydrostatic_buoyancy(HydrostaticBuoyancyInput(1_000, 1_500, 2_500_000, object_mass_kg=2))["results"]
    assert result["gauge_pressure_pa"] == pytest.approx(1_000 * 9.80665 * 1.5)
    assert result["buoyant_force_n"] == pytest.approx(1_000 * 9.80665 * 0.0025)
    assert result["apparent_weight_n"] == pytest.approx(2 * 9.80665 - 1_000 * 9.80665 * 0.0025)
    assert result["buoyant_force_at_least_weight"] is True


def test_circular_shaft_torsion_reports_stress_twist_and_constraint() -> None:
    result = circular_shaft_torsion(CircularShaftTorsionInput(120, 500, 30, 79_000, 10, 250, 2))["results"]
    polar_moment = math.pi * (30**4 - 10**4) / 32
    expected_shear = 120_000 * 15 / polar_moment
    assert result["polar_second_moment_mm4"] == pytest.approx(polar_moment)
    assert result["maximum_shear_stress_mpa"] == pytest.approx(expected_shear)
    assert result["twist_radians"] == pytest.approx(120_000 * 500 / (79_000 * polar_moment))
    assert result["constraint_satisfied"] is True
    with pytest.raises(ValueError, match="less than"):
        circular_shaft_torsion(CircularShaftTorsionInput(1, 1, 10, 1, 10))


def test_spring_mass_damper_reports_modal_properties_and_static_deflection() -> None:
    result = spring_mass_damper(SpringMassDamperInput(2, 8_000, 40, 100))["results"]
    expected_omega = math.sqrt(8_000 / 2)
    assert result["natural_angular_frequency_rad_s"] == pytest.approx(expected_omega)
    assert result["critical_damping_n_s_m"] == pytest.approx(2 * math.sqrt(8_000 * 2))
    assert result["damping_ratio"] == pytest.approx(40 / (2 * math.sqrt(8_000 * 2)))
    assert result["damping_regime"] == "underdamped"
    assert result["static_deflection_m"] == pytest.approx(0.0125)


def test_ideal_brayton_cycle_reports_bounded_thermodynamics_without_propulsion_outputs() -> None:
    request = IdealBraytonCycleInput(
        inlet_temperature_k=300,
        compressor_pressure_ratio=4,
        turbine_inlet_temperature_k=1_200,
        heat_capacity_ratio=1.4,
        specific_heat_j_kgk=1_005,
        compressor_efficiency=0.82,
        turbine_efficiency=0.88,
    )
    report = ideal_brayton_cycle(request)
    result = report["results"]
    exponent = (1.4 - 1.0) / 1.4
    ideal_compressor_outlet = 300 * 4**exponent
    expected_compressor_outlet = 300 + (ideal_compressor_outlet - 300) / 0.82
    ideal_turbine_outlet = 1_200 / 4**exponent
    expected_turbine_outlet = 1_200 - 0.88 * (1_200 - ideal_turbine_outlet)
    assert result["compressor_outlet_temperature_k"] == pytest.approx(expected_compressor_outlet)
    assert result["turbine_outlet_temperature_k"] == pytest.approx(expected_turbine_outlet)
    assert result["cycle_net_positive"] is True
    assert 0 < result["thermal_efficiency"] < 1
    assert "thrust" not in result
    assert any("no mass flow, thrust" in item for item in report["assumptions"])


def test_ideal_brayton_cycle_rejects_invalid_or_thermodynamically_inconsistent_inputs() -> None:
    with pytest.raises(ValueError, match="greater than 1"):
        ideal_brayton_cycle(IdealBraytonCycleInput(300, 1, 1_200, 1.4, 1_005))
    with pytest.raises(ValueError, match="must exceed"):
        ideal_brayton_cycle(IdealBraytonCycleInput(300, 10, 400, 1.4, 1_005, 0.8, 0.9))
    with pytest.raises(ValueError, match="must not exceed 1"):
        ideal_brayton_cycle(IdealBraytonCycleInput(300, 4, 1_200, 1.4, 1_005, 1.01, 0.9))


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
    assert report["inputs"]["conductivity_w_mk"] == 200
    assert len(report["input_sha256"]) == 64
    assert len(report["request_sha256"]) == 64
    assert "not simulation" in report["claim_boundary"]


def test_physics_cli_lists_machine_readable_model_catalog(tmp_path, capsys) -> None:
    output = tmp_path / "catalog.json"
    args = build_parser().parse_args(["physics", "--list", "-o", str(output)])
    assert args.func(args) == 0
    catalog = json.loads(capsys.readouterr().out)
    assert json.loads(output.read_text(encoding="utf-8")) == catalog
    assert catalog["schema_version"] == "neurocad-physics-catalog-v2"
    models = {entry["name"]: entry for entry in catalog["models"]}
    assert len(models) == 18
    assert models["lumped_thermal_transient"]["parameters"][0] == {
        "name": "density_kg_m3",
        "required": True,
    }
    damping = next(parameter for parameter in models["spring_mass_damper"]["parameters"] if parameter["name"] == "damping_n_s_m")
    assert damping == {"default": 0.0, "name": "damping_n_s_m", "required": False}


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


def test_physics_cli_supports_ideal_brayton_cycle_without_emitting_thrust(tmp_path, capsys) -> None:
    source = tmp_path / "cycle.json"
    source.write_text(
        json.dumps(
            {
                "model": "ideal_brayton_cycle",
                "inputs": {
                    "inlet_temperature_k": 300,
                    "compressor_pressure_ratio": 4,
                    "turbine_inlet_temperature_k": 1_200,
                    "heat_capacity_ratio": 1.4,
                    "specific_heat_j_kgk": 1_005,
                    "compressor_efficiency": 0.82,
                    "turbine_efficiency": 0.88,
                },
            }
        ),
        encoding="utf-8",
    )
    assert build_parser().parse_args(["physics", str(source)]).func(build_parser().parse_args(["physics", str(source)])) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["model"] == "ideal_brayton_cycle_v1"
    assert "thrust" not in report["results"]


def test_physics_v2_binds_geometry_material_and_load_case(tmp_path, capsys) -> None:
    project = tmp_path / "project.json"
    _write_agent_project(project)
    request = tmp_path / "bound-physics.json"
    request.write_text(
        json.dumps(
            {
                "model": "circular_shaft_torsion",
                "inputs": {
                    "torque_n_m": 120,
                    "length_mm": 100,
                    "outer_diameter_mm": 20,
                    "shear_modulus_mpa": 79_000,
                    "yield_strength_mpa": 250,
                    "safety_factor": 2,
                },
                "context": {
                    "schema_version": "neurocad-physics-context-v1",
                    "geometry": {"agent_project": "project.json", "component_id": "shaft"},
                    "material": {
                        "schema_version": "neurocad-material-card-v1",
                        "material_id": "steel-example",
                        "revision": 1,
                        "source": "Declared test fixture; not a production material allow-list.",
                        "properties": {
                            "density_kg_m3": 7_850,
                            "shear_modulus_mpa": 79_000,
                            "yield_strength_mpa": 250,
                        },
                    },
                    "load_case": {
                        "schema_version": "neurocad-load-case-v1",
                        "case_id": "rated-torque",
                        "coordinate_system": "component-local",
                        "source": "Declared test fixture.",
                        "values": {"torque_n_m": 120, "safety_factor": 2},
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    args = build_parser().parse_args(["physics", str(request)])
    assert args.func(args) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["schema_version"] == "neurocad-physics-v2"
    bindings = report["bindings"]
    assert bindings["geometry"]["component_id"] == "shaft"
    assert bindings["geometry"]["model_inputs_checked"] == ["length_mm", "outer_diameter_mm"]
    assert bindings["geometry"]["metrics"]["volume_mm3"] == pytest.approx(math.pi * 10**2 * 100)
    assert bindings["geometry"]["metrics"]["material_mass_kg"] == pytest.approx(7_850 * math.pi * 10**2 * 100e-9)
    assert bindings["geometry"]["metrics"]["section_properties"]["polar_second_moment_mm4"] == pytest.approx(math.pi * 10**4 / 2)
    assert bindings["material"]["properties_used"] == ["shear_modulus_mpa", "yield_strength_mpa"]
    assert bindings["load_case"]["values_used"] == ["safety_factor", "torque_n_m"]
    assert len(bindings["binding_sha256"]) == 64


def test_physics_v2_rejects_stale_or_contradictory_bindings(tmp_path) -> None:
    project = tmp_path / "project.json"
    _write_agent_project(project)
    component = AgentComponent("shaft", "Shaft", "shaft", "add", "cylinder", {"radius": 9.0, "height": 100.0}, (0.0, 0.0, 50.0))
    stale_hash = component_geometry_sha256(component)
    base = {
        "model": "circular_shaft_torsion",
        "inputs": {"torque_n_m": 120, "length_mm": 100, "outer_diameter_mm": 20, "shear_modulus_mpa": 79_000},
        "context": {
            "schema_version": "neurocad-physics-context-v1",
            "geometry": {
                "agent_project": str(project),
                "component_id": "shaft",
                "expected_geometry_sha256": stale_hash,
            },
        },
    }
    source = tmp_path / "stale.json"
    source.write_text(json.dumps(base), encoding="utf-8")
    with pytest.raises(StalePhysicsBindingError, match="geometry binding is stale"):
        build_parser().parse_args(["physics", str(source)]).func(build_parser().parse_args(["physics", str(source)]))

    base["context"]["geometry"].pop("expected_geometry_sha256")
    base["inputs"]["outer_diameter_mm"] = 30
    source.write_text(json.dumps(base), encoding="utf-8")
    with pytest.raises(ValueError, match="contradicts bound component"):
        build_parser().parse_args(["physics", str(source)]).func(build_parser().parse_args(["physics", str(source)]))
    base["inputs"]["outer_diameter_mm"] = 20

    base["context"] = {
        "schema_version": "neurocad-physics-context-v1",
        "material": {
            "schema_version": "neurocad-material-card-v1",
            "material_id": "contradiction",
            "revision": 1,
            "source": "Declared test fixture.",
            "properties": {"shear_modulus_mpa": 80_000},
        },
    }
    source.write_text(json.dumps(base), encoding="utf-8")
    with pytest.raises(ValueError, match="contradicts material card"):
        build_parser().parse_args(["physics", str(source)]).func(build_parser().parse_args(["physics", str(source)]))


def test_physics_verify_detects_geometry_drift(tmp_path, capsys) -> None:
    project = tmp_path / "project.json"
    _write_agent_project(project)
    request = tmp_path / "request.json"
    report_path = tmp_path / "report.json"
    request.write_text(
        json.dumps(
            {
                "model": "spring_mass_damper",
                "inputs": {"mass_kg": 1, "stiffness_n_m": 1_000},
                "context": {
                    "schema_version": "neurocad-physics-context-v1",
                    "geometry": {"agent_project": str(project), "component_id": "shaft"},
                },
            }
        ),
        encoding="utf-8",
    )
    run_args = build_parser().parse_args(["physics", str(request), "-o", str(report_path)])
    assert run_args.func(run_args) == 0
    capsys.readouterr()

    verify_args = build_parser().parse_args(["physics", "--verify", str(report_path)])
    assert verify_args.func(verify_args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "current"

    _write_agent_project(project, radius=11.0, revision=2)
    assert verify_args.func(verify_args) == 2
    verification = json.loads(capsys.readouterr().out)
    assert verification["status"] == "stale"
    assert verification["current"] is False
    assert verification["observed_project_revision"] == 2


@pytest.mark.parametrize(
    "model_input",
    [
        EulerBucklingInput(True, 1, 1),
        ThermalExpansionInput(1, float("nan"), 1),
        SteadyConductionInput(1, 0, 1, 1),
        InternalPipeFlowInput(1, 1, -1, 1, 1),
        ThinWallCylinderInput(1, 1, 0),
        IdealBraytonCycleInput(300, 4, 1_200, 1.4, float("inf")),
        SteadyConvectionInput(1, 1, 0, 1),
        RadiativeExchangeInput(1.1, 1, 300, 300),
        LumpedThermalTransientInput(1, 1, 1, 1, 1, 1, 1, 1, -1),
        HydrostaticBuoyancyInput(1, 1, -1),
        CircularShaftTorsionInput(1, 1, 1, 1, -1),
        SpringMassDamperInput(1, 1, -1),
    ],
)
def test_physics_models_reject_nonphysical_or_nonfinite_inputs(model_input: object) -> None:
    evaluator = {
        EulerBucklingInput: euler_buckling,
        ThermalExpansionInput: thermal_expansion,
        SteadyConductionInput: steady_conduction,
        InternalPipeFlowInput: internal_pipe_flow,
        ThinWallCylinderInput: thin_wall_cylinder,
        IdealBraytonCycleInput: ideal_brayton_cycle,
        SteadyConvectionInput: steady_convection,
        RadiativeExchangeInput: radiative_exchange,
        LumpedThermalTransientInput: lumped_thermal_transient,
        HydrostaticBuoyancyInput: hydrostatic_buoyancy,
        CircularShaftTorsionInput: circular_shaft_torsion,
        SpringMassDamperInput: spring_mass_damper,
    }[type(model_input)]
    with pytest.raises((TypeError, ValueError)):
        evaluator(model_input)
