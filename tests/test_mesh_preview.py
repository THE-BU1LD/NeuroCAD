import base64
import hashlib
import shutil

import pytest

from core.demo_server import generate_demo_payload
from core.mesh_preview import _COMPILER_SLOT, MeshDownloadStore, compile_payload_meshes


def test_download_cache_preserves_bytes_and_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [100.0]
    monkeypatch.setattr('core.mesh_preview.time.monotonic', lambda: clock[0])
    store = MeshDownloadStore(max_bytes=8, ttl_seconds=10)
    artifacts = {'body': {'stl_base64': base64.b64encode(b'geometry').decode()}}
    store.publish(artifacts)
    url = artifacts['body']['download_url']
    assert store.get(url) == b'geometry'
    assert 'stl_base64' not in artifacts['body']
    clock[0] = 111
    assert store.get(url) is None


def test_download_cache_evicts_and_rejects_oversized_batches() -> None:
    store = MeshDownloadStore(max_bytes=3)
    first = {'model': {'stl_base64': base64.b64encode(b'abc').decode()}}
    second = {'model': {'stl_base64': base64.b64encode(b'def').decode()}}
    store.publish(first)
    store.publish(second)
    assert store.get(first['model']['download_url']) is None
    assert store.get(second['model']['download_url']) == b'def'
    with pytest.raises(ValueError, match='budget'):
        store.publish({'model': {'stl_base64': base64.b64encode(b'abcd').decode()}})


def test_busy_compiler_fails_explicitly() -> None:
    with _COMPILER_SLOT, pytest.raises(ValueError, match='busy'):
        compile_payload_meshes({})


@pytest.mark.parametrize("budget", [True, 0, 30.0, "30", 121, 600])
def test_interactive_budget_is_bounded_before_any_compiler_work(budget: object) -> None:
    with pytest.raises(ValueError, match="30, 60, or 120"):
        compile_payload_meshes({}, timeout_seconds=budget)  # type: ignore[arg-type]


@pytest.mark.parametrize("budget", [30, 60, 120])
def test_selected_budget_reaches_kernel_and_timeout_releases_slot(budget: int, monkeypatch: pytest.MonkeyPatch) -> None:
    from core.artifacts import CompilerTimeoutError

    def timeout(*args: object, **kwargs: object) -> None:
        assert kwargs["timeout"] == budget
        raise CompilerTimeoutError("test deadline")

    monkeypatch.setattr("core.mesh_preview.compile_scad_verified", timeout)
    with pytest.raises(CompilerTimeoutError):
        compile_payload_meshes({"mode": "canonical_program", "scad": "cube([1,2,3]);"}, timeout_seconds=budget)
    assert _COMPILER_SLOT.acquire(blocking=False)
    _COMPILER_SLOT.release()


@pytest.mark.skipif(shutil.which('openscad') is None, reason='OpenSCAD required')
def test_preview_download_matches_verified_mesh() -> None:
    payload = compile_payload_meshes(generate_demo_payload('a 120 x 80 x 4 mm plate with four 4 mm holes'))
    artifact = payload['mesh_artifacts']['model']
    raw = base64.b64decode(artifact['stl_base64'], validate=True)
    assert hashlib.sha256(raw).hexdigest() == artifact['sha256']
    assert payload['evaluation']['kernel_validity'] is True
    assert '<polygon' in artifact['preview_svg']
    assert 'Actual compiled mesh' in payload['preview_svg']
    assert artifact['verification']['watertight']


@pytest.mark.skipif(shutil.which('openscad') is None, reason='OpenSCAD required')
def test_enclosure_has_individually_verified_downloads() -> None:
    source = ('80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; '
              'friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm')
    payload = compile_payload_meshes(generate_demo_payload(source, 'enclosure'))
    assert set(payload['mesh_artifacts']) == {'body', 'lid'}
    for part in payload['mesh_artifacts'].values():
        assert part['verification']['enclosure_features']['valid']
