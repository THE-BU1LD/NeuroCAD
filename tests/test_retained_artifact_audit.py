"""Exercise evidence loss, corruption and unsafe manifest rejection."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_retained_artifacts import audit


def write_manifest(root: Path, entries: dict[str, str]) -> Path:
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({"artifact_sha256": entries}), encoding="utf-8")
    return manifest


def test_audit_retains_missing_and_corrupted_files_without_repair(tmp_path):
    payload = b"original measurement\n"
    digest = hashlib.sha256(payload).hexdigest()
    (tmp_path / "good.bin").write_bytes(payload)
    (tmp_path / "changed.bin").write_bytes(b"edited")
    manifest = write_manifest(tmp_path, dict.fromkeys(["good.bin", "changed.bin", "missing.bin"], digest))
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = audit(manifest)
    assert result["status"] == "FAIL"
    assert (result["listed"], result["matched"]) == (3, 1)
    assert {r["path"] for r in result["failures"]} == {"changed.bin", "missing.bin"}
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_native_hash_manifest_and_research_manifest_agree(tmp_path):
    payload = b"retained bytes\r\n"
    (tmp_path / "part.step").write_bytes(payload)
    entries = {"part.step": hashlib.sha256(payload).hexdigest()}
    research = audit(write_manifest(tmp_path, entries))
    native = tmp_path / "SHA256SUMS.json"
    native.write_text(json.dumps(entries), encoding="utf-8")
    result = audit(native, "hashes")
    assert research["status"] == result["status"] == "PASS"
    assert result["matched"] == 1


@pytest.mark.parametrize("name", ["../outside", "/absolute", "C:/outside", "a\\b", "a/../b", "a//b", "./a"])
def test_unsafe_manifest_paths_are_rejected(tmp_path, name):
    with pytest.raises(ValueError, match="unsafe artifact path"):
        audit(write_manifest(tmp_path, {name: "0" * 64}))


def test_symlink_artifact_is_not_followed(tmp_path):
    target = tmp_path / "real"
    target.write_bytes(b"bytes")
    link = tmp_path / "link"
    try:
        link.symlink_to(target)
    except OSError as error:
        pytest.skip(f"OS did not permit symlink creation: {error}")
    result = audit(write_manifest(tmp_path, {"link": hashlib.sha256(b"bytes").hexdigest()}))
    assert result["status"] == "FAIL"
    assert "symlink" in result["failures"][0]["error"]


@pytest.mark.parametrize("raw", ['{"artifact_sha256": {}}', '{"artifact_sha256": {"a": true}}',
                                '{"artifact_sha256": {}, "artifact_sha256": {}}'])
def test_empty_invalid_and_duplicate_manifests_are_rejected(tmp_path, raw):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError):
        audit(manifest)
