"""Engineering fault-injection tests. FakeGmsh is not native meshing evidence."""
from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import multiprocessing
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.gmsh_backend import GmshBackend, GmshMeshingError
from core.gmsh_integrity import capture_mesh, publish_directory_noreplace, verify_mesh_roundtrip


def fixture_data():
    return {
        "nodes": [1, 2, 3, 4, 5],
        "coords": [0., 0., 0., 1., 0., 0., 0., 1., 0., 0., 0., 1., 1., 1., 1.],
        "entities": {"2": [1, 2], "3": [1, 2]},
        "blocks": [
            {"dim": 2, "entity": 1, "type": 2, "tags": [201], "conn": [1, 2, 3]},
            {"dim": 2, "entity": 2, "type": 2, "tags": [202], "conn": [2, 3, 5]},
            {"dim": 3, "entity": 1, "type": 4, "tags": [101], "conn": [1, 2, 3, 4]},
            {"dim": 3, "entity": 2, "type": 4, "tags": [102], "conn": [2, 3, 4, 5]},
        ],
        "groups": [],
    }


class FakeModel:
    def __init__(self, owner):
        self.owner = owner
        self.mesh = self

    def getEntities(self, dim):
        return [(dim, tag) for tag in self.owner.data["entities"][str(dim)]]

    def getNodes(self):
        return self.owner.data["nodes"], self.owner.data["coords"], []

    def getElements(self, dim, tag=-1):
        blocks = [b for b in self.owner.data["blocks"]
                  if b["dim"] == dim and (tag == -1 or b["entity"] == tag)]
        return ([b["type"] for b in blocks], [b["tags"] for b in blocks],
                [b["conn"] for b in blocks])

    def getElementProperties(self, element_type):
        return {2: ("Triangle", 2, 1, 3, [], 3), 4: ("Tetrahedron", 3, 1, 4, [], 4)}[element_type]

    def addPhysicalGroup(self, dim, entities):
        tag = len(self.owner.data["groups"]) + 1
        self.owner.data["groups"].append({"dim": dim, "tag": tag, "name": "", "entities": entities})
        return tag

    def setPhysicalName(self, dim, tag, name):
        self._group(dim, tag)["name"] = name

    def _group(self, dim, tag):
        return next(g for g in self.owner.data["groups"] if (g["dim"], g["tag"]) == (dim, tag))

    def getPhysicalGroups(self):
        return [(g["dim"], g["tag"]) for g in self.owner.data["groups"]]

    def getPhysicalName(self, dim, tag):
        return self._group(dim, tag)["name"]

    def getEntitiesForPhysicalGroup(self, dim, tag):
        return self._group(dim, tag)["entities"]

    def generate(self, dim):
        assert dim == 3

    def getElementQualities(self, tags, measure):
        assert measure == "minSICN"
        return [0.5] * len(tags)


class FakeGmsh:
    def __init__(self, mutation=None, on_finalize=None):
        self.data = fixture_data()
        self.model = FakeModel(self)
        self.option = SimpleNamespace(setNumber=lambda *_: None)
        self.mutation = mutation
        self.on_finalize = on_finalize
        self.initialized = False
        self.finalized = False

    def isInitialized(self):
        return self.initialized

    def initialize(self, **kwargs):
        assert kwargs == {"readConfigFiles": False}
        self.initialized = True

    def finalize(self):
        self.initialized = False
        self.finalized = True
        if self.on_finalize:
            self.on_finalize()

    def clear(self):
        self.data = {}

    def open(self, path):
        if Path(path).suffix == ".msh":
            self.data = json.loads(Path(path).read_text())
            if self.mutation:
                self.mutation(self.data)

    def write(self, path):
        Path(path).write_text(json.dumps(self.data))


def make_backend(fake):
    instance = object.__new__(GmshBackend)
    instance.gmsh = fake
    instance.version = "FAKE-engineering-test-only"
    return instance


def source_file(tmp_path):
    path = tmp_path / "source.step"
    path.write_text("not a real STEP file: engineering fake-adapter fixture\n")
    return path


def corrupt(data, kind):
    if kind == "coordinates":
        data["coords"][0] += 0.25
    elif kind == "connectivity":
        data["blocks"][2]["conn"][0:2] = [2, 1]
    elif kind == "surface-connectivity":
        data["blocks"][0]["conn"][0:2] = [2, 1]
    elif kind == "surface-elements":
        data["blocks"].pop(0)
    elif kind == "physical-membership":
        data["groups"][0]["entities"] = [1]
    elif kind == "node-identities":
        data["nodes"][-1] = 6
    elif kind == "element-identities":
        data["blocks"][2]["tags"][0] = 199
    elif kind == "entity-membership":
        data["blocks"][2]["entity"] = 2
    elif kind == "nan-coordinates":
        data["coords"][0] = float("nan")
    elif kind == "infinite-coordinates":
        data["coords"][0] = float("inf")
    elif kind == "short-coordinates":
        data["coords"].pop()
    elif kind == "malformed-connectivity":
        data["blocks"][2]["conn"].pop()
    elif kind == "duplicate-node-identities":
        data["nodes"][-1] = 4
    else:
        raise AssertionError(kind)


CORRUPTIONS = ["coordinates", "connectivity", "surface-connectivity", "surface-elements",
               "physical-membership", "node-identities", "element-identities", "entity-membership",
               "nan-coordinates", "infinite-coordinates", "short-coordinates",
               "malformed-connectivity", "duplicate-node-identities"]


@pytest.mark.parametrize("kind", CORRUPTIONS)
def test_backend_rejects_count_preserving_corruption(tmp_path, kind):
    fake = FakeGmsh(mutation=lambda data: corrupt(data, kind))
    destination = tmp_path / "bundle"
    with pytest.raises(GmshMeshingError):
        make_backend(fake).mesh_step(source_file(tmp_path), destination, max_size_mm=4.)
    assert fake.finalized
    assert not destination.exists()
    assert not list(tmp_path.glob(".bundle.*"))


def reorder(data):
    data["nodes"].reverse()
    triples = [data["coords"][i:i + 3] for i in range(0, len(data["coords"]), 3)]
    data["coords"] = [value for triple in reversed(triples) for value in triple]
    data["blocks"].reverse()
    data["groups"].reverse()
    for group in data["groups"]:
        group["entities"].reverse()
    for entities in data["entities"].values():
        entities.reverse()


@pytest.mark.parametrize("mutation", [None, reorder, lambda d: d["coords"].__setitem__(0, 1e-14)])
def test_backend_accepts_identical_reordered_or_tiny_roundoff_mesh(tmp_path, mutation):
    fake = FakeGmsh(mutation)
    source = source_file(tmp_path)
    receipt = make_backend(fake).mesh_step(source, tmp_path / "bundle", max_size_mm=4.)
    assert receipt.node_count == receipt.roundtrip_node_count == 5
    assert receipt.volume_element_count == receipt.roundtrip_volume_element_count == 2
    assert receipt.source_step_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    payload = json.loads((tmp_path / "bundle/meshing-receipt.json").read_text())
    assert payload["mesh_sha256"] == hashlib.sha256((tmp_path / "bundle/design.msh").read_bytes()).hexdigest()
    assert fake.finalized


def test_backend_refuses_destination_created_after_initial_check(tmp_path):
    destination = tmp_path / "bundle"
    fake = FakeGmsh(on_finalize=lambda: destination.mkdir())
    with pytest.raises(FileExistsError):
        make_backend(fake).mesh_step(source_file(tmp_path), destination, max_size_mm=4.)
    assert destination.is_dir() and list(destination.iterdir()) == []
    assert not list(tmp_path.glob(".bundle.*"))


def test_backend_refuses_file_created_after_initial_check(tmp_path):
    destination = tmp_path / "bundle"
    fake = FakeGmsh(on_finalize=lambda: destination.write_text("other writer"))
    with pytest.raises(OSError):
        make_backend(fake).mesh_step(source_file(tmp_path), destination, max_size_mm=4.)
    assert destination.read_text() == "other writer"
    assert not list(tmp_path.glob(".bundle.*"))


def test_snapshot_rejects_node_bound_before_copy(monkeypatch):
    import core.gmsh_integrity as module
    monkeypatch.setattr(module, "MAX_VERIFY_NODES", 4)
    with pytest.raises(GmshMeshingError, match="bounded"):
        capture_mesh(FakeGmsh())


def test_snapshot_rejects_element_bound(monkeypatch):
    import core.gmsh_integrity as module
    monkeypatch.setattr(module, "MAX_VERIFY_ELEMENTS", 3)
    with pytest.raises(GmshMeshingError, match="bounded"):
        capture_mesh(FakeGmsh())


def test_snapshot_rejects_mismatched_arrays():
    fake = FakeGmsh()
    fake.model.getElements = lambda *_: ([4], [], [])
    with pytest.raises(GmshMeshingError, match="inconsistent"):
        capture_mesh(fake)


def test_snapshot_rejects_zero_node_tag():
    fake = FakeGmsh()
    fake.data["nodes"][0] = 0
    with pytest.raises(GmshMeshingError, match="positive"):
        capture_mesh(fake)


def test_snapshot_rejects_duplicate_element_tag():
    fake = FakeGmsh()
    fake.data["blocks"][0]["tags"] = [201, 201]
    fake.data["blocks"][0]["conn"] *= 2
    with pytest.raises(GmshMeshingError, match="unique"):
        capture_mesh(fake)


def test_comparison_tolerance_is_enforced():
    fake = FakeGmsh()
    before = capture_mesh(fake)
    fake.data["coords"][0] = 2e-12
    with pytest.raises(GmshMeshingError, match="coordinates"):
        verify_mesh_roundtrip(before, capture_mesh(fake))


def test_snapshot_copies_mutable_backend_arrays():
    fake = FakeGmsh()
    before = capture_mesh(fake)
    fake.data["coords"][0] = 5.
    assert before.coordinates[0] == 0.


def staging_dir(tmp_path, name="staging"):
    path = tmp_path / name
    path.mkdir()
    (path / "payload").write_text(name)
    return path


@pytest.mark.parametrize("kind", ["empty-dir", "nonempty-dir", "file", "dangling-symlink"])
def test_atomic_publish_never_replaces_existing_destination(tmp_path, kind):
    staging = staging_dir(tmp_path)
    destination = tmp_path / "destination"
    if kind == "empty-dir":
        destination.mkdir()
    elif kind == "nonempty-dir":
        destination.mkdir()
        (destination / "owned").write_text("keep")
    elif kind == "file":
        destination.write_text("keep")
    else:
        destination.symlink_to(tmp_path / "absent")
    inode = destination.lstat().st_ino
    with pytest.raises(FileExistsError):
        publish_directory_noreplace(staging, destination)
    assert destination.lstat().st_ino == inode
    assert (staging / "payload").read_text() == "staging"


def test_atomic_publish_complete_bundle(tmp_path):
    staging = staging_dir(tmp_path)
    destination = tmp_path / "destination"
    publish_directory_noreplace(staging, destination)
    assert not staging.exists()
    assert (destination / "payload").read_text() == "staging"


def test_atomic_publish_refuses_different_parent(tmp_path):
    staging = staging_dir(tmp_path)
    with pytest.raises(ValueError, match="share a parent"):
        publish_directory_noreplace(staging, tmp_path / "other/destination")


def test_atomic_publish_refuses_symlink_staging(tmp_path):
    real = staging_dir(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="regular directory"):
        publish_directory_noreplace(link, tmp_path / "destination")


def test_atomic_publish_fails_closed_on_unsupported_platform(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "unsupported-test-platform")
    staging = staging_dir(tmp_path)
    with pytest.raises(OSError) as raised:
        publish_directory_noreplace(staging, tmp_path / "destination")
    assert raised.value.errno == errno.ENOTSUP
    assert staging.exists()


def test_atomic_publish_fails_closed_on_missing_symbol(tmp_path, monkeypatch):
    monkeypatch.setattr(ctypes, "CDLL", lambda *a, **k: SimpleNamespace())
    staging = staging_dir(tmp_path)
    with pytest.raises(OSError) as raised:
        publish_directory_noreplace(staging, tmp_path / "destination")
    assert raised.value.errno == errno.ENOTSUP
    assert staging.exists()


def _publish_worker(staging, destination, event, queue):
    event.wait(10)
    try:
        publish_directory_noreplace(Path(staging), Path(destination))
        queue.put((Path(staging).name, "published"))
    except FileExistsError:
        queue.put((Path(staging).name, "refused"))
    except (OSError, ValueError) as exc:
        queue.put((Path(staging).name, repr(exc)))


@pytest.mark.parametrize("iteration", range(5))
def test_atomic_publish_independent_processes_one_winner(tmp_path, iteration):
    context = multiprocessing.get_context("spawn")
    event, queue = context.Event(), context.Queue()
    first, second = staging_dir(tmp_path, "first"), staging_dir(tmp_path, "second")
    destination = tmp_path / "destination"
    workers = [context.Process(target=_publish_worker, args=(str(path), str(destination), event, queue))
               for path in (first, second)]
    try:
        for worker in workers:
            worker.start()
        event.set()
        results = [queue.get(timeout=15), queue.get(timeout=15)]
        for worker in workers:
            worker.join(15)
            assert worker.exitcode == 0
        assert sorted(status for _, status in results) == ["published", "refused"]
        winner = next(name for name, status in results if status == "published")
        assert (destination / "payload").read_text() == winner
        loser = next(name for name, status in results if status == "refused")
        assert (tmp_path / loser / "payload").read_text() == loser
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(5)
        queue.close()
