"""Adapter fault-injection tests; these do not run or validate a native mesh."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from core import gmsh_backend as module
from core.gmsh_backend import GmshBackend, GmshMeshingError


class FakeGmsh:
    """Minimal API double for ownership, provenance and publication contracts."""

    def __init__(self, *, active=False, qualities=(0.5, 0.75)):
        self.active = active
        self.qualities = qualities
        self.calls = []
        self.options = {}
        self.groups = {}
        self.loaded_step = None
        self.on_initialize = None
        self.fail_finalize = False
        self.option = SimpleNamespace(setNumber=self.set_number)
        self.model = SimpleNamespace(
            mesh=self,
            getEntities=lambda dim: [(dim, 1)],
            addPhysicalGroup=self.add_group,
            setPhysicalName=self.set_name,
            getPhysicalGroups=lambda: list(self.groups),
            getPhysicalName=lambda dim, tag: self.groups[(dim, tag)],
        )

    def isInitialized(self):
        return int(self.active)

    def initialize(self, **kwargs):
        assert kwargs == {"readConfigFiles": False}
        self.calls.append("initialize")
        self.active = True
        if self.on_initialize:
            self.on_initialize()

    def set_number(self, key, value):
        self.options[key] = value

    def add_group(self, dim, tags):
        assert tags
        return dim

    def set_name(self, dim, tag, name):
        self.groups[(dim, tag)] = name

    def open(self, path):
        self.calls.append("open")
        if Path(path).suffix == ".step":
            self.loaded_step = Path(path).read_bytes()

    def generate(self, dim):
        assert dim == 3

    def getNodes(self):
        return [1, 2, 3, 4, 5], [], []

    def getElements(self, dim):
        assert dim == 3
        return [4], [[11, 12]], []

    def getElementQualities(self, tags, kind):
        assert tags == [11, 12]
        assert kind == "minSICN"
        return self.qualities

    def write(self, path):
        Path(path).write_bytes(b"adapter-test-double; not a native mesh\n")

    def clear(self):
        self.calls.append("clear")

    def finalize(self):
        self.calls.append("finalize")
        self.active = False
        if self.fail_finalize:
            raise RuntimeError("injected finalize failure")


def _case(tmp_path, **kwargs):
    source = tmp_path / "part.step"
    source.write_bytes(b"adapter source fixture\n")
    fake = FakeGmsh(**kwargs)
    backend = GmshBackend.__new__(GmshBackend)
    backend.gmsh = fake
    backend.version = "test-double"
    return backend, fake, source, tmp_path / "mesh"


def _assert_not_published(destination):
    assert not destination.exists()
    assert not list(destination.parent.glob(f".{destination.name}.*"))


def test_adapter_success_records_source_and_publishes_only_declared_artifacts(tmp_path):
    backend, fake, source, destination = _case(tmp_path)
    original = source.read_bytes()
    receipt = backend.mesh_step(source, destination, max_size_mm=4.0)
    assert receipt.source_step_sha256 == hashlib.sha256(original).hexdigest()
    assert receipt.source_step_bytes == len(original)
    assert fake.loaded_step == original
    assert receipt.min_sicn == 0.5
    assert receipt.mean_sicn == 0.625
    assert fake.calls.count("finalize") == 1
    assert {path.name for path in destination.iterdir()} == {
        "design.msh", "meshing-receipt.json"
    }


def test_existing_gmsh_session_is_not_cleared_or_finalized(tmp_path):
    backend, fake, source, destination = _case(tmp_path, active=True)
    with pytest.raises(GmshMeshingError, match="already initialized"):
        backend.mesh_step(source, destination, max_size_mm=4.0)
    assert fake.active
    assert fake.calls == []
    _assert_not_published(destination)


@pytest.mark.parametrize("qualities", [(), (0.5,), (0.5, 0.6, 0.7)])
def test_incomplete_or_oversized_quality_vectors_fail_closed(tmp_path, qualities):
    backend, fake, source, destination = _case(tmp_path, qualities=qualities)
    with pytest.raises(GmshMeshingError, match="quality count"):
        backend.mesh_step(source, destination, max_size_mm=4.0)
    assert fake.calls.count("finalize") == 1
    _assert_not_published(destination)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_quality_fails_closed(tmp_path, bad):
    backend, _, source, destination = _case(tmp_path, qualities=(0.5, bad))
    with pytest.raises(GmshMeshingError, match="non-finite"):
        backend.mesh_step(source, destination, max_size_mm=4.0)
    _assert_not_published(destination)


@pytest.mark.parametrize("bad", [0.0, -0.1])
def test_nonpositive_quality_fails_closed(tmp_path, bad):
    backend, _, source, destination = _case(tmp_path, qualities=(0.5, bad))
    with pytest.raises(GmshMeshingError, match="non-positive"):
        backend.mesh_step(source, destination, max_size_mm=4.0)
    _assert_not_published(destination)


@pytest.mark.parametrize("maximum", [0.01, 0.025, 0.05, 4.0, 1_000_000.0])
def test_default_minimum_stays_within_the_documented_size_contract(tmp_path, maximum):
    backend, _, source, destination = _case(tmp_path)
    receipt = backend.mesh_step(source, destination, max_size_mm=maximum)
    assert receipt.mesh_size_min_mm == max(0.01, maximum / 5.0)
    assert 0.01 <= receipt.mesh_size_min_mm <= maximum


@pytest.mark.parametrize("bad", [True, "4", 0, -1, float("nan"), float("inf"), 10**1000])
def test_invalid_size_is_a_documented_input_error(tmp_path, bad):
    backend, fake, source, destination = _case(tmp_path)
    with pytest.raises((TypeError, ValueError)):
        backend.mesh_step(source, destination, max_size_mm=bad)
    assert fake.calls == []
    _assert_not_published(destination)


def test_receipt_binds_the_snapshot_actually_given_to_gmsh(tmp_path):
    backend, fake, source, destination = _case(tmp_path)
    original = source.read_bytes()
    fake.on_initialize = lambda: source.write_bytes(b"concurrently changed source")
    receipt = backend.mesh_step(source, destination, max_size_mm=4.0)
    assert source.read_bytes() != original
    assert fake.loaded_step == original
    assert receipt.source_step_sha256 == hashlib.sha256(fake.loaded_step).hexdigest()
    assert receipt.source_step_bytes == len(fake.loaded_step)


def test_source_read_failure_removes_staging(tmp_path, monkeypatch):
    backend, fake, source, destination = _case(tmp_path)
    original_open = Path.open

    def fail_source_open(path, mode="r", *args, **kwargs):
        if path == source and mode == "rb":
            raise PermissionError("injected source read failure")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_source_open)
    with pytest.raises(PermissionError, match="source read"):
        backend.mesh_step(source, destination, max_size_mm=4.0)
    assert fake.calls == []
    _assert_not_published(destination)


def test_finalize_failure_removes_staging_without_publication(tmp_path):
    backend, fake, source, destination = _case(tmp_path)
    fake.fail_finalize = True
    with pytest.raises(RuntimeError, match="finalize failure"):
        backend.mesh_step(source, destination, max_size_mm=4.0)
    _assert_not_published(destination)


def test_publication_failure_removes_staging(tmp_path, monkeypatch):
    backend, fake, source, destination = _case(tmp_path)

    def fail_replace(*args):
        raise PermissionError("injected publication failure")

    monkeypatch.setattr(module.os, "replace", fail_replace)
    with pytest.raises(PermissionError, match="publication failure"):
        backend.mesh_step(source, destination, max_size_mm=4.0)
    assert fake.calls.count("finalize") == 1
    _assert_not_published(destination)


def test_dangling_output_symlink_is_not_followed(tmp_path):
    backend, fake, source, destination = _case(tmp_path)
    target = tmp_path / "unrelated-target"
    try:
        destination.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(FileExistsError):
        backend.mesh_step(source, destination, max_size_mm=4.0)
    assert destination.is_symlink()
    assert not target.exists()
    assert fake.calls == []
    assert not list(tmp_path.glob(".unrelated-target.*"))


@pytest.mark.parametrize("replacement", [b"", b"x" * 65])
def test_snapshot_rechecks_size_after_initial_stat(tmp_path, monkeypatch, replacement):
    backend, fake, source, destination = _case(tmp_path)
    monkeypatch.setattr(module, "MAX_STEP_BYTES", 64)
    original_mkdtemp = module.tempfile.mkdtemp

    def mutate_after_stat(*args, **kwargs):
        staging = original_mkdtemp(*args, **kwargs)
        source.write_bytes(replacement)
        return staging

    monkeypatch.setattr(module.tempfile, "mkdtemp", mutate_after_stat)
    with pytest.raises(GmshMeshingError, match="STEP source size"):
        backend.mesh_step(source, destination, max_size_mm=4.0)
    assert fake.calls == []
    _assert_not_published(destination)


def test_quality_omission_above_budget_is_explicit(tmp_path, monkeypatch):
    backend, _, source, destination = _case(tmp_path, qualities=())
    monkeypatch.setattr(module, "MAX_QUALITY_ELEMENTS", 1)
    receipt = backend.mesh_step(source, destination, max_size_mm=4.0)
    assert receipt.min_sicn is None
    assert receipt.mean_sicn is None
