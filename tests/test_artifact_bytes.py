"""Integrity receipts describe the exact bytes published on every platform."""

import subprocess
from pathlib import Path

import pytest

from core.artifacts import write_text_atomic
from core.integrations.common import canonical_json, write_json_atomic


def test_atomic_text_preserves_utf8_lf_bytes(tmp_path: Path) -> None:
    path = tmp_path / "artifact.txt"
    text = "first\nsecond π\n"
    write_text_atomic(path, text)
    assert path.read_bytes() == text.encode("utf-8")


def test_atomic_json_publishes_exact_canonical_bytes(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    for overwrite in (False, True):
        value = {"title": "π", "revision": int(overwrite)}
        write_json_atomic(path, value, overwrite=overwrite)
        assert path.read_bytes() == canonical_json(value).encode("utf-8")


def test_compiler_timeout_preserves_previous_output_and_cleans_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from core.artifacts import CompilerTimeoutError, compile_scad_verified

    source, output = tmp_path / "part.scad", tmp_path / "part.stl"
    source.write_text("cube([1,2,3]);")
    output.write_bytes(b"previous artifact")
    monkeypatch.setattr("core.artifacts.find_openscad", lambda: "openscad")

    def timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired("openscad", 30)

    monkeypatch.setattr("core.artifacts.subprocess.run", timeout)
    with pytest.raises(CompilerTimeoutError, match="30 seconds"):
        compile_scad_verified(source, output, timeout=30)
    assert output.read_bytes() == b"previous artifact"
    assert {path.name for path in tmp_path.iterdir()} == {"part.scad", "part.stl"}
