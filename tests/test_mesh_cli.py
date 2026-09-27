"""Companion CLI and discovery contracts without importing either native kernel."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from core import mesh_cli
from core.integrations import registry as registry_module
from core.integrations.model import CapabilityState
from neurocad_cli import KNOWN_COMMANDS, build_parser, cmd_feature_build


def test_legacy_feature_command_is_unchanged():
    assert "feature" in KNOWN_COMMANDS
    args = build_parser().parse_args(["feature", "build", "part.json", "--output-dir", "cad"])
    assert args.func is cmd_feature_build


def test_mesh_companion_routes_step_without_resolving_input(monkeypatch, tmp_path, capsys):
    seen = {}

    class Backend:
        def __init__(self, *, timeout_seconds):
            seen["timeout_seconds"] = timeout_seconds

        def mesh_step(self, source, destination, **kwargs):
            seen.update(source=source, destination=destination, **kwargs)
            return SimpleNamespace(to_dict=lambda: {"fixture_only": True})

    monkeypatch.setattr(mesh_cli, "GmshProcessBackend", Backend)
    source = tmp_path / "input.step"
    destination = tmp_path / "mesh"
    with pytest.raises(SystemExit) as result:
        mesh_cli.main(["step", str(source), "--output-dir", str(destination), "--max-size", "3"])
    assert result.value.code == 0
    assert seen == {"source": source, "destination": destination, "min_size_mm": None, "max_size_mm": 3.0, "timeout_seconds": 120.0}
    assert json.loads(capsys.readouterr().out) == {"fixture_only": True}


def test_mesh_companion_reports_unavailable_backend(monkeypatch, tmp_path, capsys):
    def unavailable(*, timeout_seconds):
        assert timeout_seconds == 120.0
        raise RuntimeError("native runtime unavailable")

    monkeypatch.setattr(mesh_cli, "GmshProcessBackend", unavailable)
    with pytest.raises(SystemExit) as result:
        mesh_cli.main(["step", str(tmp_path / "input.step"), "--output-dir", str(tmp_path / "mesh"), "--max-size", "3"])
    assert result.value.code == 2
    assert "native runtime unavailable" in capsys.readouterr().err
    assert not (tmp_path / "mesh").exists()


def test_mesh_companion_refuses_input_output_collision(tmp_path, capsys):
    path = str(tmp_path / "same")
    with pytest.raises(SystemExit) as result:
        mesh_cli.main(["step", path, "--output-dir", path, "--max-size", "3"])
    assert result.value.code == 2
    assert "must be distinct" in capsys.readouterr().err


@pytest.mark.parametrize("module_available", [False, True])
@pytest.mark.parametrize("executable_available", [False, True])
def test_gmsh_capability_depends_on_binding_not_standalone_executable(monkeypatch, module_available, executable_available):
    monkeypatch.setattr(registry_module.importlib.util, "find_spec",
                        lambda name: object() if name == "gmsh" and module_available else None)
    monkeypatch.setattr(registry_module.shutil, "which",
                        lambda name: "/fixture/gmsh" if name == "gmsh" and executable_available else None)
    registry = registry_module.default_registry()
    expected_ids = {"build123d", "cadquery", "gmsh", "calculix", "openfoam", "openems", "lammps",
                    "paraview", "openmdao", "casadi", "pyvista"}
    assert expected_ids.issubset(registry.ids())
    adapter = registry.get("gmsh")
    prerequisites = {item.id: item.available for item in adapter.prerequisites}
    assert prerequisites == {"gmsh_executable": executable_available, "gmsh_module": module_available}
    capability = adapter.capability("tagged_volume_mesh")
    expected = CapabilityState.AVAILABLE if module_available else CapabilityState.UNAVAILABLE
    assert capability.state is expected
    assert capability.external_operation_performed is False
    assert registry.get("calculix").capability("structural_fea").state is CapabilityState.UNAVAILABLE


def test_mesh_companion_accepts_explicit_worker_timeout():
    args = mesh_cli.build_parser().parse_args([
        "step", "part.step", "--output-dir", "new-mesh", "--max-size", "3", "--timeout-seconds", "2.5",
    ])
    assert args.timeout_seconds == 2.5


@pytest.mark.parametrize("timeout", ["0", "nan", "3601"])
def test_mesh_companion_rejects_invalid_timeout_before_native_import(timeout, tmp_path, capsys):
    with pytest.raises(SystemExit) as result:
        mesh_cli.main(["step", "missing.step", "--output-dir", str(tmp_path / "mesh"),
                       "--max-size", "3", "--timeout-seconds", timeout])
    assert result.value.code == 2
    assert "timeout_seconds" in capsys.readouterr().err
    assert not (tmp_path / "mesh").exists()
