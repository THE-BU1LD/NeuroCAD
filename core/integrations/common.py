"""Bounded serialization and naming helpers for integration artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

from ..artifacts import write_text_atomic

MAX_FILENAME_STEM = 64


def safe_filename_stem(value: str, *, fallback: str = "neurocad-design") -> str:
    """Return a portable ASCII filename stem with no path semantics."""

    if not isinstance(value, str):
        raise TypeError("filename source must be a string")

    def slug(source: str) -> str:
        normalized = unicodedata.normalize("NFKD", source).encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-.").lower()[:MAX_FILENAME_STEM].rstrip("-.")

    if not isinstance(fallback, str):
        raise TypeError("filename fallback must be a string")
    stem = slug(value) or slug(fallback) or "neurocad-design"
    if stem in {"con", "prn", "aux", "nul", *(f"com{index}" for index in range(1, 10)), *(f"lpt{index}" for index in range(1, 10))}:
        stem = f"neurocad-{stem}"
    return stem


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, value: Any, *, overwrite: bool = False) -> Path:
    """Publish canonical JSON atomically, refusing clobber by default.

    The no-overwrite path stages a complete same-filesystem file and publishes
    it with an atomic hard link.  Unlike a check followed by ``os.replace``, a
    concurrently appearing destination cannot be overwritten.
    """

    destination = Path(path)
    encoded = canonical_json(value)
    if overwrite:
        return write_text_atomic(destination, encoded)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            raise FileExistsError(f"refusing to overwrite existing JSON artifact: {destination}") from None
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    temporary.unlink()
    return destination
