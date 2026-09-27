"""Real subprocess transport/fault tests; synthetic bytes are not native meshes."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core import gmsh_process as module
from core.gmsh_integrity import GmshMeshingError
from core.gmsh_process import GmshProcessBackend

# This deliberately produces a transport fixture, NOT a geometric/native result.
WORKER_FIXTURE = r'''
import hashlib
import json
import os
import sys
import time
from pathlib import Path
mode, source, bundle, minimum, maximum = sys.argv[1:]
source, bundle = Path(source), Path(bundle)
bundle.mkdir()
mesh = bundle / "design.msh"
mesh.write_bytes(b"synthetic worker transport fixture; not a native mesh\n")
payload = dict(
    backend="gmsh", backend_version="synthetic-transport-fixture",
    source_step_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), source_step_bytes=source.stat().st_size,
    mesh_path="design.msh", mesh_sha256=hashlib.sha256(mesh.read_bytes()).hexdigest(), mesh_bytes=mesh.stat().st_size,
    volume_entity_count=1, boundary_surface_count=4, node_count=4, volume_element_count=1,
    physical_groups=("boundary", "domain"), mesh_size_min_mm=float(minimum), mesh_size_max_mm=float(maximum),
    min_sicn=0.5, mean_sicn=0.5, roundtrip_node_count=4, roundtrip_volume_element_count=1,
    roundtrip_physical_groups=("boundary", "domain"),
)
payload.update(
    receipt_version="neurocad-gmsh-mesh-receipt-v1",
    roundtrip_verification="nodes-connectivity-physical-membership-v1",
    roundtrip_coordinate_abs_tol_mm=1e-12, roundtrip_coordinate_rel_tol=1e-13,
    claim_boundary="synthetic transport fixture; not geometry evidence",
)
mutations = {
    "wrong_hash": ("mesh_sha256", "0" * 64), "wrong_source": ("source_step_sha256", "0" * 64),
    "wrong_size": ("mesh_bytes", 999), "different_settings": ("mesh_size_max_mm", 999),
    "extra_field": ("unrecognized", True), "bad_quality": ("mean_sicn", 0.1),
    "half_null_quality": ("mean_sicn", None), "boolean_quality": ("min_sicn", True),
    "zero_count": ("node_count", 0), "boolean_count": ("node_count", True),
    "float_count": ("node_count", 4.0), "wrong_group": ("physical_groups", ["domain"]),
    "roundtrip_count": ("roundtrip_node_count", 5), "roundtrip_groups": ("roundtrip_physical_groups", ["domain", "boundary"]),
    "bad_metadata": ("backend_version", False), "path_escape": ("mesh_path", "../escape.msh"),
    "nonfinite": ("min_sicn", float("nan")), "boolean_size": ("mesh_size_max_mm", True),
    "quality_overflow": ("min_sicn", 10 ** 1000), "version": ("receipt_version", "unknown"),
}
if mode in mutations:
    key, value = mutations[mode]
    payload[key] = value
if mode == "missing_field":
    payload.pop("claim_boundary")
if mode == "null_quality":
    payload["min_sicn"] = payload["mean_sicn"] = None
text = json.dumps(payload)
if mode == "duplicate_key":
    text = text[:-1] + ', "node_count":4}'
if mode == "oversize_receipt":
    text += " " * 65537
if mode == "list_receipt":
    text = "[]"
receipt_path = bundle / "meshing-receipt.json"
receipt_path.write_text(text, encoding="utf-8")
if mode == "invalid_utf8":
    receipt_path.write_bytes(b"\xff")
if mode == "missing_receipt":
    receipt_path.unlink()
if mode == "missing_mesh":
    mesh.unlink()
if mode == "empty_mesh":
    mesh.write_bytes(b"")
if mode == "unexpected_file":
    (bundle / "extra").write_bytes(b"unexpected")
if mode == "crash":
    os._exit(17)
if mode in ("error", "bad_error", "oversize_error"):
    error = '{"message": "deliberate native failure\\u001b[31m"}'
    if mode == "bad_error":
        error = "not json"
    if mode == "oversize_error":
        error += " " * 65537
    (bundle.parent / "worker-error.json").write_text(error, encoding="utf-8")
    raise SystemExit(2)
if mode == "late_hang":
    # A completed-looking private bundle must not become public before exit.
    (source.parent.parent / "worker-created-private-bundle").write_bytes(b"ready")
    time.sleep(30)
'''


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "source with spaces.step"
    path.write_bytes(b"ISO-10303-21; synthetic source; END-ISO-10303-21;")
    return path


def _use_fixture_worker(monkeypatch, mode="success"):
    def command(source, bundle, minimum, maximum):
        return [sys.executable, "-c", WORKER_FIXTURE, mode, str(source), str(bundle), str(minimum), str(maximum)]
    monkeypatch.setattr(module, "_worker_command", command)


@pytest.mark.parametrize("value", [True, False, None, "120", 0, -1, 0.09, 3601, float("nan"), float("inf"), -float("inf"), 10 ** 1000])
def test_timeout_contract_rejects_invalid_values(value):
    with pytest.raises((TypeError, ValueError), match="timeout_seconds"):
        GmshProcessBackend(timeout_seconds=value)


@pytest.mark.parametrize("value", [0.1, 1, 120, 3600])
def test_timeout_contract_accepts_documented_endpoints(value):
    assert GmshProcessBackend(timeout_seconds=value).timeout_seconds == float(value)


@pytest.mark.parametrize("mode", ["success", "null_quality"])
def test_real_worker_success_publishes_three_hash_bound_files(monkeypatch, source, tmp_path, mode):
    _use_fixture_worker(monkeypatch, mode)
    destination = tmp_path / "result with spaces"
    before = source.read_bytes()
    receipt = GmshProcessBackend(timeout_seconds=10).mesh_step(source, destination, max_size_mm=3)
    assert source.read_bytes() == before
    assert {path.name for path in destination.iterdir()} == {"design.msh", "meshing-receipt.json", "execution-receipt.json"}
    stored = json.loads((destination / "meshing-receipt.json").read_text(encoding="utf-8"))
    assert stored == receipt.to_dict()
    execution = json.loads((destination / "execution-receipt.json").read_text(encoding="utf-8"))
    assert execution["status"] == "success"
    assert execution["worker_returncode"] == 0
    assert execution["timeout_seconds"] == 10
    assert execution["worker_elapsed_seconds"] >= 0
    assert execution["source_step_sha256"] == receipt.source_step_sha256 == hashlib.sha256(before).hexdigest()
    assert execution["mesh_sha256"] == hashlib.sha256((destination / "design.msh").read_bytes()).hexdigest()
    assert execution["meshing_receipt_sha256"] == hashlib.sha256((destination / "meshing-receipt.json").read_bytes()).hexdigest()
    assert not list(tmp_path.glob(".neurocad-gmsh-worker-*"))


@pytest.mark.parametrize("mode", [
    "wrong_hash", "wrong_source", "wrong_size", "different_settings", "extra_field", "bad_quality",
    "half_null_quality", "boolean_quality", "zero_count", "boolean_count", "float_count", "wrong_group",
    "roundtrip_count", "roundtrip_groups", "bad_metadata", "path_escape", "nonfinite", "boolean_size",
    "quality_overflow", "version", "missing_field", "duplicate_key", "oversize_receipt", "list_receipt",
    "invalid_utf8", "missing_receipt", "missing_mesh", "empty_mesh", "unexpected_file",
])
def test_success_exit_cannot_publish_invalid_worker_bundle(monkeypatch, source, tmp_path, mode):
    _use_fixture_worker(monkeypatch, mode)
    destination = tmp_path / "result"
    with pytest.raises(GmshMeshingError):
        GmshProcessBackend(timeout_seconds=10).mesh_step(source, destination, max_size_mm=3)
    assert not destination.exists()
    assert not list(tmp_path.glob(".neurocad-gmsh-worker-*"))


@pytest.mark.parametrize("mode", ["crash", "error", "bad_error", "oversize_error"])
def test_failed_worker_never_publishes_completed_looking_bundle(monkeypatch, source, tmp_path, mode):
    _use_fixture_worker(monkeypatch, mode)
    destination = tmp_path / "result"
    with pytest.raises(GmshMeshingError, match="worker exited with code") as caught:
        GmshProcessBackend(timeout_seconds=10).mesh_step(source, destination, max_size_mm=3)
    if mode == "error":
        assert "deliberate native failure" in str(caught.value)
        assert "\x1b" not in str(caught.value)
    assert not destination.exists()
    assert not list(tmp_path.glob(".neurocad-gmsh-worker-*"))


def test_timeout_kills_and_reaps_only_spawned_worker(monkeypatch):
    original = subprocess.Popen
    processes = []

    def tracked(*args, **kwargs):
        assert kwargs["shell"] is False
        assert kwargs["stdin"] == kwargs["stdout"] == kwargs["stderr"] == subprocess.DEVNULL
        process = original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(module.subprocess, "Popen", tracked)
    with pytest.raises(subprocess.TimeoutExpired):
        module._run_worker([sys.executable, "-c", "import time; time.sleep(30)"], 0.2)
    assert len(processes) == 1
    assert processes[0].poll() is not None
    assert processes[0].returncode != 0


def test_timeout_cleans_private_completed_looking_bundle(monkeypatch, source, tmp_path):
    _use_fixture_worker(monkeypatch, "late_hang")
    destination = tmp_path / "result"
    with pytest.raises(GmshMeshingError, match="exceeded.*terminated"):
        GmshProcessBackend(timeout_seconds=2).mesh_step(source, destination, max_size_mm=3)
    assert (tmp_path / "worker-created-private-bundle").is_file()
    assert not destination.exists()
    assert not list(tmp_path.glob(".neurocad-gmsh-worker-*"))


@pytest.mark.parametrize("kind", ["empty_directory", "nonempty_directory", "file"])
def test_existing_destination_is_preserved_without_starting_worker(monkeypatch, source, tmp_path, kind):
    destination = tmp_path / "accepted"
    if kind == "file":
        destination.write_bytes(b"accepted")
    else:
        destination.mkdir()
        if kind == "nonempty_directory":
            (destination / "keep").write_bytes(b"accepted")
    def forbidden(*args):
        raise AssertionError("must reject before worker launch")
    monkeypatch.setattr(module, "_run_worker", forbidden)
    with pytest.raises(FileExistsError):
        GmshProcessBackend().mesh_step(source, destination, max_size_mm=3)
    if kind == "file":
        assert destination.read_bytes() == b"accepted"
    elif kind == "nonempty_directory":
        assert (destination / "keep").read_bytes() == b"accepted"
    else:
        assert list(destination.iterdir()) == []


def test_late_destination_race_preserves_other_writer(monkeypatch, source, tmp_path):
    _use_fixture_worker(monkeypatch)
    destination = tmp_path / "accepted"
    original = module._run_worker
    def race(command, timeout):
        result = original(command, timeout)
        destination.mkdir()
        (destination / "keep").write_bytes(b"other writer")
        return result
    monkeypatch.setattr(module, "_run_worker", race)
    with pytest.raises(FileExistsError):
        GmshProcessBackend(timeout_seconds=10).mesh_step(source, destination, max_size_mm=3)
    assert [path.name for path in destination.iterdir()] == ["keep"]
    assert (destination / "keep").read_bytes() == b"other writer"
    assert not list(tmp_path.glob(".neurocad-gmsh-worker-*"))


def test_snapshot_binds_worker_input_when_original_changes(monkeypatch, source, tmp_path):
    _use_fixture_worker(monkeypatch)
    original = module._run_worker
    before = source.read_bytes()
    def replace_source(command, timeout):
        source.write_bytes(b"changed after private snapshot")
        return original(command, timeout)
    monkeypatch.setattr(module, "_run_worker", replace_source)
    receipt = GmshProcessBackend(timeout_seconds=10).mesh_step(source, tmp_path / "result", max_size_mm=3)
    assert receipt.source_step_sha256 == hashlib.sha256(before).hexdigest()
    assert receipt.source_step_bytes == len(before)


@pytest.mark.parametrize("kind", ["missing", "directory", "empty"])
def test_invalid_source_fails_before_workspace_or_worker(monkeypatch, tmp_path, kind):
    source = tmp_path / "source.step"
    if kind == "directory":
        source.mkdir()
    elif kind == "empty":
        source.write_bytes(b"")
    with pytest.raises((FileNotFoundError, GmshMeshingError)):
        GmshProcessBackend().mesh_step(source, tmp_path / "new_parent" / "result", max_size_mm=3)
    assert not (tmp_path / "new_parent").exists()


@pytest.mark.parametrize("minimum,maximum", [(0, 3), (4, 3), (None, float("nan")), (None, True)])
def test_invalid_sizes_fail_before_workspace(source, tmp_path, minimum, maximum):
    with pytest.raises((TypeError, ValueError)):
        GmshProcessBackend().mesh_step(source, tmp_path / "new_parent" / "result", min_size_mm=minimum, max_size_mm=maximum)
    assert not (tmp_path / "new_parent").exists()


def test_worker_error_is_bounded_and_keeps_no_success_receipt(monkeypatch, source, tmp_path):
    class Unavailable:
        def __init__(self):
            raise RuntimeError("failure" * 10000)
    monkeypatch.setattr(module, "GmshBackend", Unavailable)
    workspace = tmp_path / "worker"
    workspace.mkdir()
    result = module._worker_main([str(source), str(workspace / "bundle"), "1", "3"])
    assert result == 2
    raw = (workspace / "worker-error.json").read_bytes()
    assert len(raw) < module.MAX_WORKER_JSON_BYTES
    assert len(json.loads(raw)["message"]) == 2048
    assert not (workspace / "bundle").exists()


def test_native_worker_delegates_original_backend_without_rewriting_paths(monkeypatch, source, tmp_path):
    seen = {}
    class Backend:
        def mesh_step(self, source, bundle, **kwargs):
            seen.update(source=source, bundle=bundle, **kwargs)
    monkeypatch.setattr(module, "GmshBackend", Backend)
    bundle = tmp_path / "private" / "bundle"
    assert module._worker_main([str(source), str(bundle), "1", "3"]) == 0
    assert seen == {"source": source, "bundle": bundle, "min_size_mm": 1.0, "max_size_mm": 3.0}


def test_production_worker_command_is_argument_vector_not_shell(source, tmp_path):
    bundle = tmp_path / "with spaces;not-a-shell" / "bundle"
    command = module._worker_command(source, bundle, 1.0, 3.0)
    assert command[:2] == [sys.executable, "-c"]
    assert command[2] == (
        "import sys; sys.path[0] = sys.argv.pop(1); "
        "from core.gmsh_process import _worker_main; raise SystemExit(_worker_main())"
    )
    assert command[3:] == [str(Path(module.__file__).resolve().parents[1]), str(source), str(bundle), "1.0", "3.0"]


def test_worker_bootstrap_does_not_import_core_from_callers_directory(source, tmp_path):
    hostile = tmp_path / "unrelated working directory"
    (hostile / "core").mkdir(parents=True)
    marker = tmp_path / "wrong_package_imported"
    (hostile / "core" / "__init__.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_bytes(b'wrong package')\nraise RuntimeError('wrong package')\n",
        encoding="utf-8",
    )
    workspace = tmp_path / "private worker"
    workspace.mkdir()
    result = subprocess.run(
        module._worker_command(source, workspace / "bundle", 1.0, 3.0),
        cwd=hostile, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=15, check=False,
    )
    # Native Gmsh is absent OR rejects this deliberately invalid STEP fixture.
    assert result.returncode != 0
    assert not marker.exists()
    assert not (workspace / "bundle").exists()


@pytest.mark.parametrize("kind", ["source", "destination", "mesh", "receipt", "bundle"])
def test_symlink_metadata_is_rejected_without_following_it(monkeypatch, source, tmp_path, kind):
    _use_fixture_worker(monkeypatch)
    destination = tmp_path / "result"
    original = Path.is_symlink
    names = {"mesh": "design.msh", "receipt": "meshing-receipt.json", "bundle": "bundle"}
    def reported_symlink(path):
        return ((kind == "source" and path == source) or (kind == "destination" and path == destination)
                or (kind in names and path.name == names[kind]) or original(path))
    monkeypatch.setattr(Path, "is_symlink", reported_symlink)
    with pytest.raises((FileNotFoundError, FileExistsError, GmshMeshingError)):
        GmshProcessBackend(timeout_seconds=10).mesh_step(source, destination, max_size_mm=3)
    assert not destination.exists()
    assert source.read_bytes().startswith(b"ISO-10303-21;")


def test_parent_mesh_byte_limit_is_enforced(monkeypatch, source, tmp_path):
    _use_fixture_worker(monkeypatch)
    monkeypatch.setattr(module, "MAX_WORKER_MESH_BYTES", 1)
    with pytest.raises(GmshMeshingError, match="worker mesh must contain"):
        GmshProcessBackend(timeout_seconds=10).mesh_step(source, tmp_path / "result", max_size_mm=3)
    assert not (tmp_path / "result").exists()
