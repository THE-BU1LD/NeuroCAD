"""Matched local adapters for direct and structured VeriCodeGen outputs.

Both arms enter the same OpenSCAD/mesh verification path after this boundary.
The adapter owns the frozen fragment resolution so neither arm can gain an
uncontrolled geometry-resolution advantage.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess  # OpenSCAD is invoked with a fixed, shell-free argument vector.  # nosec B404
from pathlib import Path
from typing import Any

from research.vericodegen.structured_spec import StructuredSpecError, compile_structured_json

ARM_NAMES = ("direct", "structured")
FORBIDDEN_DIRECT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("markdown_fence", re.compile(r"```")),
    ("include", re.compile(r"(?i)\binclude\s*<")),
    ("use", re.compile(r"(?i)\buse\s*<")),
    ("import", re.compile(r"(?i)\bimport\s*\(")),
    ("surface", re.compile(r"(?i)\bsurface\s*\(")),
    ("resolution_override_fn", re.compile(r"\$fn\s*=")),
    ("resolution_override_fa", re.compile(r"\$fa\s*=")),
    ("resolution_override_fs", re.compile(r"\$fs\s*=")),
)


class ArmAdapterError(ValueError):
    """Raised when a generated arm output violates the frozen adapter contract."""


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_fn(fn: Any) -> int:
    if not isinstance(fn, int) or isinstance(fn, bool) or not 12 <= fn <= 360:
        raise ArmAdapterError("openscad_fn must be an integer in [12, 360]")
    return fn


def validate_direct_output(text: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(text, str) or not text.strip():
        return ["direct output must be non-empty OpenSCAD source"]
    for name, pattern in FORBIDDEN_DIRECT_PATTERNS:
        if pattern.search(text):
            errors.append(f"direct output contains forbidden construct: {name}")
    if text.lstrip().startswith("{"):
        errors.append("direct output appears to be JSON rather than OpenSCAD source")
    return errors


def prepare_direct_scad(text: str, *, fn: int) -> str:
    """Wrap raw direct OpenSCAD with the same frozen fragment resolution used by structured."""

    fn = validate_fn(fn)
    errors = validate_direct_output(text)
    if errors:
        raise ArmAdapterError("direct output rejected:\n- " + "\n- ".join(errors))
    return (
        "// VeriCodeGen frozen direct-arm wrapper\n"
        "// Fragment resolution is treatment-neutral and supplied by the runner.\n"
        f"$fn = {fn};\n"
        + text.rstrip()
        + "\n"
    )


def prepare_structured_scad(text: str, *, fn: int) -> str:
    fn = validate_fn(fn)
    try:
        return compile_structured_json(text, fn=fn)
    except StructuredSpecError as exc:
        raise ArmAdapterError(str(exc)) from exc


def prepare_arm_scad(arm: str, raw_output: str, *, fn: int) -> str:
    if arm == "direct":
        return prepare_direct_scad(raw_output, fn=fn)
    if arm == "structured":
        return prepare_structured_scad(raw_output, fn=fn)
    raise ArmAdapterError(f"unknown arm: {arm!r}")


def compile_openscad(
    scad_text: str,
    *,
    scad_path: str | Path,
    stl_path: str | Path,
    openscad_binary: str = "openscad",
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """Compile one prepared arm artifact through the shared OpenSCAD CLI boundary."""

    if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or timeout_seconds < 1:
        raise ArmAdapterError("timeout_seconds must be an integer >= 1")
    scad_file = Path(scad_path)
    stl_file = Path(stl_path)
    scad_file.parent.mkdir(parents=True, exist_ok=True)
    stl_file.parent.mkdir(parents=True, exist_ok=True)
    scad_file.write_text(scad_text, encoding="utf-8")
    executable = shutil.which(openscad_binary)
    if executable is None:
        raise ArmAdapterError(f"OpenSCAD executable not found: {openscad_binary}")

    record: dict[str, Any] = {
        "compile_success": False,
        "timed_out": False,
        "returncode": None,
        "stdout": "",
        "scad_sha256": sha256_text(scad_text),
        "artifact_sha256": None,
    }
    try:
        proc = subprocess.run(  # Resolved executable; no shell; paths are separate arguments.  # nosec B603
            [executable, "-o", str(stl_file), str(scad_file)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        record["timed_out"] = True
        record["stdout"] = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        return record

    record["returncode"] = proc.returncode
    record["stdout"] = proc.stdout
    success = proc.returncode == 0 and stl_file.is_file() and stl_file.stat().st_size > 0
    record["compile_success"] = success
    if success:
        record["artifact_sha256"] = hashlib.sha256(stl_file.read_bytes()).hexdigest()
    return record
