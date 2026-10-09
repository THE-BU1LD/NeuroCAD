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


def test_atomic_text_new_publication_preserves_bytes_and_default_replacement(tmp_path: Path) -> None:
    path = tmp_path / "artifact.txt"
    write_text_atomic(path, "first π\n", overwrite=False)
    assert path.read_bytes() == "first π\n".encode()
    write_text_atomic(path, "replacement π\n")
    assert path.read_bytes() == "replacement π\n".encode()
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_text_atomic(path, "must not replace\n", overwrite=False)
    assert path.read_bytes() == "replacement π\n".encode()
    assert list(tmp_path.iterdir()) == [path]


def test_atomic_text_new_publication_preserves_concurrent_destination(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    path = tmp_path / "artifact.txt"
    native_link = os.link

    def concurrent_writer(source, destination):
        # The staged artifact is already complete, but another writer wins
        # publication before this operation can claim the destination name.
        assert Path(source).read_bytes() == "staged π\n".encode()
        Path(destination).write_bytes(b"concurrent artifact\n")
        return native_link(source, destination)

    monkeypatch.setattr("core.artifacts.os.link", concurrent_writer)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        write_text_atomic(path, "staged π\n", overwrite=False)
    assert path.read_bytes() == b"concurrent artifact\n"
    assert list(tmp_path.iterdir()) == [path]


def test_atomic_text_new_publication_cleans_up_when_links_are_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def unsupported_link(*args, **kwargs):
        raise OSError("hard-link publication unavailable")

    monkeypatch.setattr("core.artifacts.os.link", unsupported_link)
    with pytest.raises(OSError, match="publication unavailable"):
        write_text_atomic(tmp_path / "artifact.txt", "complete artifact\n", overwrite=False)
    assert not list(tmp_path.iterdir())


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
