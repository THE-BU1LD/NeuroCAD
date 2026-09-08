"""Integrity receipts describe the exact bytes published on every platform."""

from pathlib import Path

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
