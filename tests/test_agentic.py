from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

import pytest

import neurocad_cli
from core.agent_workbench import start_agent_workbench
from core.agentic import (
    AGENT_PLAN_VERSION,
    AgentComponent,
    AgentPlan,
    AgentWorkspace,
    BuiltinPlanningProvider,
    OpenAICompatiblePlanningProvider,
    parse_agent_plan,
    plan_to_program,
    planning_provider,
)
from core.ir import validate_program


def _component(plan: AgentPlan, identifier: str) -> AgentComponent:
    return next(item for item in plan.components if item.id == identifier)


def _provider_payload() -> dict[str, Any]:
    return {
        "version": AGENT_PLAN_VERSION,
        "title": "Desk organizer",
        "summary": "A simple open organizer concept.",
        "assumptions": [
            {
                "name": "size",
                "value": "120 x 80 x 50 mm",
                "reason": "Compact desktop default",
                "source": "provider",
            }
        ],
        "components": [
            {
                "id": "outer",
                "label": "Outer body",
                "part": "organizer",
                "operation": "add",
                "shape": "rounded_box",
                "parameters": {"size": [120, 80, 50], "radius": 5},
                "translate": [0, 0, 25],
                "rotate": [0, 0, 0],
            },
            {
                "id": "cavity",
                "label": "Storage cavity",
                "part": "organizer",
                "operation": "subtract",
                "shape": "box",
                "parameters": {"size": [108, 68, 46]},
                "translate": [0, 0, 29],
                "rotate": [0, 0, 0],
            },
        ],
    }


def test_builtin_bottle_plan_records_assumptions_and_valid_ir() -> None:
    plan = BuiltinPlanningProvider().plan("Make a 1 L water bottle with a carrying loop")
    assert plan.title == "Water bottle concept"
    assert _component(plan, "carry_loop").shape == "torus"
    assert any(item.name == "capacity" and item.value == "1000 mL" for item in plan.assumptions)
    assert validate_program(plan_to_program(plan)).valid


def test_builtin_underspecified_primitive_uses_visible_defaults() -> None:
    plan = BuiltinPlanningProvider().plan("Please make a cylinder")
    cylinder = _component(plan, "cylinder")
    assert cylinder.parameters == {"radius": 20.0, "height": 50.0}
    assert any(item.name == "overall dimensions" and item.source == "inferred" for item in plan.assumptions)


@pytest.mark.parametrize(
    ("prompt", "title", "component_count"),
    [
        (
            "make a hollow shaft with outer diameter 40 mm inner diameter 24 mm and length 500 mm",
            "Hollow shaft concept",
            2,
        ),
        (
            "make an I-beam width 100 mm height 200 mm flange thickness 10 mm web thickness 8 mm length 1000 mm",
            "I-beam concept",
            3,
        ),
        (
            "make an L-bracket width 50 mm height 80 mm thickness 5 mm length 300 mm",
            "L-bracket concept",
            2,
        ),
        (
            "make a perforated plate width 120 mm height 80 mm thickness 4 mm hole diameter 10 mm columns 4 rows 3 edge margin 15 mm",
            "Perforated plate concept",
            13,
        ),
    ],
)
def test_builtin_generates_dimensioned_complex_profiles(prompt: str, title: str, component_count: int) -> None:
    plan = BuiltinPlanningProvider().plan(prompt)
    assert plan.title == title
    assert len(plan.components) == component_count
    assert plan.assumptions[0].source == "user"
    assert validate_program(plan_to_program(plan)).valid


def test_workspace_revises_bottle_and_keeps_checkpoints(tmp_path: Path) -> None:
    workspace = AgentWorkspace(tmp_path / "bottle")
    provider = BuiltinPlanningProvider()
    first = workspace.run("make a water bottle", provider)
    second = workspace.run("make it 750 mL, add a carrying loop, and widen the base", provider)

    assert first.revision == 1
    assert second.revision == 2
    assert float(_component(second.plan, "body_outer").parameters["radius"]) > float(
        _component(first.plan, "body_outer").parameters["radius"]
    )
    assert _component(second.plan, "carry_loop")
    state = workspace.read_state()
    assert state is not None
    assert state["status"] == "draft_complete"
    assert state["validation_level"] == "canonical_ir"
    assert [item["revision"] for item in state["history"]] == [1, 2]
    assert (workspace.root / "design.ncad.json").is_file()
    assert (workspace.root / "design.scad").is_file()
    assert (workspace.root / "preview.svg").is_file()
    snapshot = state["current_snapshot"]
    for artifact in ("ir", "scad", "preview"):
        content = (workspace.root / snapshot[artifact]).read_bytes()
        assert snapshot["sha256"][artifact] == hashlib.sha256(content).hexdigest()


def test_builtin_routes_new_objects_before_previous_bottle_context() -> None:
    provider = BuiltinPlanningProvider()
    bottle = provider.plan("make a water bottle")
    wheel = provider.plan("make a wheel", bottle)
    armor = provider.plan("delete the water bottle make an iron man suit", bottle)

    assert wheel.title == "Wheel concept"
    assert _component(wheel, "axle_bore").operation == "subtract"
    assert armor.title == "Mark III inspired cosplay shell"
    assert _component(armor, "helmet_outer")


def test_builtin_wheel_revision_applies_inch_delta_to_prior_diameter() -> None:
    provider = BuiltinPlanningProvider()
    first = provider.plan("make a wheel")
    second = provider.plan("make the wheel 10 inches bigger", first)

    first_tire = _component(first, "tire")
    second_tire = _component(second, "tire")
    first_diameter = 2.0 * sum(float(first_tire.parameters[key]) for key in ("major_radius", "minor_radius"))
    second_diameter = 2.0 * sum(float(second_tire.parameters[key]) for key in ("major_radius", "minor_radius"))
    assert second_diameter == pytest.approx(first_diameter + 254.0)
    assert any(item.name == "overall diameter" and item.value == "360 mm" for item in second.assumptions)
    assert any(item.name == "unit conversion" and item.value == "10 in = 254 mm" for item in second.assumptions)
    assert validate_program(plan_to_program(second)).valid


def test_builtin_taller_bottle_changes_proportions_and_preserves_state() -> None:
    provider = BuiltinPlanningProvider()
    first = provider.plan("make a 750 mL water bottle with a carrying loop")
    second = provider.plan("make the water bottle taller", first)

    assert float(_component(second, "body_outer").parameters["height"]) > float(_component(first, "body_outer").parameters["height"])
    assert float(_component(second, "body_outer").parameters["radius"]) < float(_component(first, "body_outer").parameters["radius"])
    assert _component(second, "carry_loop")
    assert any(item.name == "capacity" and item.value == "750 mL" for item in second.assumptions)
    assert any(item.name == "proportion change" for item in second.assumptions)


def test_mark_three_is_a_non_protective_cosplay_shell() -> None:
    plan = BuiltinPlanningProvider().plan("Design a Mark III cosplay suit for a person 182 cm tall")
    assert len(plan.components) >= 12
    boundary = next(item for item in plan.assumptions if item.name == "intended use")
    assert boundary.value == "cosplay and display only"
    assert "weapon" in boundary.reason
    assert validate_program(plan_to_program(plan)).valid


def test_builtin_jet_engine_is_non_operational_physics_aware_cutaway() -> None:
    plan = BuiltinPlanningProvider().plan("Generate a physics-aware jet engine")
    assert plan.title == "Non-operational jet-engine cutaway concept"
    assert _component(plan, "casing_duct").operation == "subtract"
    assert _component(plan, "fan_disk").label == "Schematic fan disk without blades"
    assert _component(plan, "chamber_outer").label == "Non-combusting chamber envelope"
    bridges = [_component(plan, identifier) for identifier in (
        "fan_display_bridge", "chamber_display_bridge", "turbine_display_bridge"
    )]
    assert all(component.shape == "cylinder" for component in bridges)
    assert len({component.translate[2] for component in bridges}) == 3
    assert _component(plan, "nozzle_coupler_outer").shape == "cylinder"
    assert {component.part for component in plan.components} >= {
        "inlet",
        "fan",
        "compressor_1",
        "chamber",
        "turbine_1",
        "nozzle",
    }
    boundary = next(item for item in plan.assumptions if item.name == "intended use")
    physics = next(item for item in plan.assumptions if item.name == "physics binding")
    assert boundary.value == "educational cutaway and display only"
    assert "unsuitable for propulsion" in boundary.reason
    assert physics.value == "explicit analytical-model inputs required"
    assert "lumped_thermal_transient" in physics.reason
    assert "models are not coupled" in physics.reason
    assert validate_program(plan_to_program(plan)).valid


@pytest.mark.parametrize("prompt", ["make a missile", "design a firearm", "add an explosive warhead"])
def test_agent_rejects_weapon_design(prompt: str) -> None:
    with pytest.raises(ValueError, match="weapon design"):
        BuiltinPlanningProvider().plan(prompt)


def test_plan_rejects_a_subtractive_first_component() -> None:
    component = AgentComponent("void", "Void", "part", "subtract", "sphere", {"radius": 10})
    with pytest.raises(ValueError, match="must begin with an additive"):
        AgentPlan("Invalid", "Invalid progressive order", (), (component,))


def test_plan_parser_is_strict_and_validates_geometry() -> None:
    plan = parse_agent_plan(_provider_payload())
    assert len(plan.components) == 2
    malformed = _provider_payload()
    malformed["unexpected"] = True
    with pytest.raises(ValueError, match="requires exactly"):
        parse_agent_plan(malformed)


def test_openai_compatible_provider_sends_bounded_request(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []

    class Response:
        def __enter__(self) -> Any:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _limit: int) -> bytes:
            body = {"choices": [{"message": {"content": json.dumps(_provider_payload())}}]}
            return json.dumps(body).encode("utf-8")

    def fake_urlopen(request: urllib.request.Request, timeout: int) -> Response:
        calls.append((request, timeout))
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    provider = OpenAICompatiblePlanningProvider(
        "http://127.0.0.1:11434/v1/chat/completions",
        "local-model",
        api_key="secret",
        timeout_seconds=10,
    )
    plan = provider.plan("make a desk organizer")
    request, timeout = calls[0]
    sent = json.loads(request.data)
    assert plan.title == "Desk organizer"
    assert timeout == 10
    assert sent["model"] == "local-model"
    assert sent["response_format"] == {"type": "json_object"}
    assert request.get_header("Authorization") == "Bearer secret"


def test_provider_selection_is_explicit_and_credential_safe() -> None:
    assert planning_provider("auto", {}).name == "builtin"
    assert planning_provider("ollama", {}).name == "openai-compatible"
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        planning_provider("openai", {})
    with pytest.raises(ValueError, match="requires"):
        planning_provider("compatible", {})


def test_live_workbench_serves_project_state_and_artifacts(tmp_path: Path) -> None:
    workspace = AgentWorkspace(tmp_path / "viewer")
    workspace.run("make a sphere", BuiltinPlanningProvider())
    server, thread, url = start_agent_workbench(workspace, port=0)
    try:
        with urllib.request.urlopen(url, timeout=5) as response:  # nosec B310
            html = response.read().decode("utf-8")
            assert "NeuroCAD Agent Studio" in html
            assert "Content-Security-Policy" in response.headers
        with urllib.request.urlopen(url + "api/state", timeout=5) as response:  # nosec B310
            payload = json.load(response)
            assert payload["state"]["revision"] == 1
            assert payload["events"][-1]["kind"] == "complete"
        with urllib.request.urlopen(url + "preview.svg", timeout=5) as response:  # nosec B310
            assert response.headers.get_content_type() == "image/svg+xml"
            assert b"<svg" in response.read()
        with urllib.request.urlopen(url + "static/three.module.min.js", timeout=5) as response:  # nosec B310
            assert response.headers.get_content_type() == "text/javascript"
            assert len(response.read()) > 100_000
        with urllib.request.urlopen(url + "static/three.core.min.js", timeout=5) as response:  # nosec B310
            assert response.headers.get_content_type() == "text/javascript"
            assert len(response.read()) > 100_000
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_live_workbench_rejects_remote_bind(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="loopback-only"):
        start_agent_workbench(AgentWorkspace(tmp_path / "viewer"), host="0.0.0.0")


def test_vendored_three_bundle_is_pinned_and_licensed() -> None:
    static = Path(__file__).parents[1] / "core" / "static"
    expected = {
        "three.core.min.js": "61ba0df005b05991361d040d8ff670e1aadfd0ce7aeebd1fdb0725957a8957de",
        "three.module.min.js": "e2b5ee6bccd38fd6d8a2428546b83c5f2426d84b152ef82be8055556e3b40eb6",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((static / name).read_bytes()).hexdigest() == digest
    assert "MIT License" in (static / "LICENSE").read_text(encoding="utf-8")


def test_agent_cli_creates_a_persistent_draft(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project = tmp_path / "cli-project"
    with pytest.raises(SystemExit) as stopped:
        neurocad_cli.main(["agent", "run", "make", "a", "cylinder", "--project", str(project)])
    assert stopped.value.code == 0
    assert "draft complete" in capsys.readouterr().out
    state = AgentWorkspace(project).read_state()
    assert state is not None and state["status"] == "draft_complete"
