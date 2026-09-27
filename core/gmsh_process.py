"""Supervise one native Gmsh worker; only the parent publishes its bundle.

This is a worker-wait timeout, not a RAM/CPU quota, process-tree sandbox, or
whole-command deadline. The direct GmshBackend API remains in-process.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess  # Fixed interpreter argv, never a shell.  # nosec B404
import sys
import tempfile
import time
from dataclasses import fields
from pathlib import Path
from typing import Any

from .gmsh_backend import (
    GMSH_RECEIPT_VERSION,
    MAX_STEP_BYTES,
    GmshBackend,
    GmshMeshReceipt,
    _finite_positive,
    _sha256,
    _snapshot_step,
)
from .gmsh_integrity import (
    COORD_ABS_TOL_MM,
    COORD_REL_TOL,
    GmshMeshingError,
    publish_directory_noreplace,
)
from .json_io import read_bounded_utf8, strict_json_loads

DEFAULT_TIMEOUT_SECONDS = 120.0
MAX_TIMEOUT_SECONDS = 3600.0
MAX_WORKER_JSON_BYTES = 64 * 1024
MAX_WORKER_MESH_BYTES = 512 * 1024 * 1024
EXECUTION_RECEIPT_VERSION = "neurocad-gmsh-worker-execution-v1"


def _validate_timeout(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("timeout_seconds must be a finite number from 0.1 through 3600")
    try:
        seconds = float(value)
    except OverflowError as exc:
        raise ValueError("timeout_seconds must be a finite number from 0.1 through 3600") from exc
    if not math.isfinite(seconds) or not 0.1 <= seconds <= MAX_TIMEOUT_SECONDS:
        raise ValueError("timeout_seconds must be a finite number from 0.1 through 3600")
    return seconds


def _worker_command(source: Path, bundle: Path, minimum: float, maximum: float) -> list[str]:
    # Pin import resolution to this installed source, not a caller's working
    # directory containing an unrelated (or hostile) package named core.
    bootstrap = (
        "import sys; sys.path[0] = sys.argv.pop(1); "
        "from core.gmsh_process import _worker_main; raise SystemExit(_worker_main())"
    )
    return [sys.executable, "-c", bootstrap, str(Path(__file__).resolve().parents[1]),
            str(source), str(bundle), str(minimum), str(maximum)]


def _run_worker(command: list[str], timeout_seconds: float) -> int:
    # No pipes can fill or accumulate unbounded native logs. Kill only our child.
    with subprocess.Popen(  # Internal Python worker and separate argv entries.  # nosec B603
        command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, shell=False,
    ) as process:
        try:
            return process.wait(timeout=timeout_seconds)
        except BaseException:
            # Reap before the caller removes the worker's private workspace.
            try:
                process.kill()
            finally:
                process.wait()
            raise


def _worker_error(workspace: Path, returncode: int) -> str:
    fallback = f"Gmsh worker exited with code {returncode}; no mesh bundle was published"
    path = workspace / "worker-error.json"
    if path.is_symlink() or not path.is_file():
        return fallback
    try:
        error = strict_json_loads(read_bounded_utf8(path, max_bytes=MAX_WORKER_JSON_BYTES, label="worker error"))
    except (OSError, UnicodeError, ValueError):
        return fallback
    if not isinstance(error, dict) or not isinstance(error.get("message"), str):
        return fallback
    # repr escapes terminal control characters and limits the surfaced message.
    return f"{fallback}: {error['message'][:2048]!r}"


def _verified_receipt(
    bundle: Path, source_hash: str, source_bytes: int, minimum: float, maximum: float,
) -> GmshMeshReceipt:
    if bundle.is_symlink() or not bundle.is_dir():
        raise GmshMeshingError("successful Gmsh worker did not produce a regular bundle directory")
    if {path.name for path in bundle.iterdir()} != {"design.msh", "meshing-receipt.json"}:
        raise GmshMeshingError("Gmsh worker bundle has missing or unexpected files")
    mesh_path, receipt_path = bundle / "design.msh", bundle / "meshing-receipt.json"
    for path in (mesh_path, receipt_path):
        if path.is_symlink() or not path.is_file():
            raise GmshMeshingError("Gmsh worker bundle must contain only regular files")
    mesh_bytes = mesh_path.stat().st_size
    if not 0 < mesh_bytes <= MAX_WORKER_MESH_BYTES:
        raise GmshMeshingError(f"worker mesh must contain 1 through {MAX_WORKER_MESH_BYTES} bytes")
    try:
        payload = strict_json_loads(read_bounded_utf8(
            receipt_path, max_bytes=MAX_WORKER_JSON_BYTES, label="worker meshing receipt",
        ))
    except (UnicodeError, ValueError) as exc:
        raise GmshMeshingError("Gmsh worker receipt is not bounded strict UTF-8 JSON") from exc
    expected_fields = {field.name for field in fields(GmshMeshReceipt)} | {"receipt_version"}
    if not isinstance(payload, dict) or set(payload) != expected_fields:
        raise GmshMeshingError("Gmsh worker receipt fields do not match the supported schema")
    expected = {
        "receipt_version": GMSH_RECEIPT_VERSION,
        "backend": "gmsh", "mesh_path": "design.msh",
        "source_step_sha256": source_hash, "source_step_bytes": source_bytes,
        "mesh_bytes": mesh_bytes, "mesh_sha256": _sha256(mesh_path),
        "mesh_size_min_mm": minimum, "mesh_size_max_mm": maximum,
        "roundtrip_verification": "nodes-connectivity-physical-membership-v1",
        "roundtrip_coordinate_abs_tol_mm": COORD_ABS_TOL_MM,
        "roundtrip_coordinate_rel_tol": COORD_REL_TOL,
    }
    if any(payload[key] != value or isinstance(payload[key], bool) for key, value in expected.items()):
        raise GmshMeshingError("Gmsh worker receipt does not match its source, settings or mesh bytes")
    count_fields = (
        "source_step_bytes", "mesh_bytes", "volume_entity_count", "boundary_surface_count",
        "node_count", "volume_element_count", "roundtrip_node_count", "roundtrip_volume_element_count",
    )
    if any(type(payload[key]) is not int or payload[key] <= 0 for key in count_fields):
        raise GmshMeshingError("Gmsh worker receipt counts must be positive integers")
    if (payload["node_count"] != payload["roundtrip_node_count"]
            or payload["volume_element_count"] != payload["roundtrip_volume_element_count"]):
        raise GmshMeshingError("Gmsh worker receipt roundtrip counts disagree")
    for key in ("physical_groups", "roundtrip_physical_groups"):
        groups = payload[key]
        if (not isinstance(groups, list) or not all(isinstance(item, str) and item for item in groups)
                or "domain" not in groups or "boundary" not in groups):
            raise GmshMeshingError("Gmsh worker receipt is missing valid physical groups")
    if payload["physical_groups"] != payload["roundtrip_physical_groups"]:
        raise GmshMeshingError("Gmsh worker receipt roundtrip groups disagree")
    for key in ("backend_version", "claim_boundary"):
        if not isinstance(payload[key], str) or not payload[key]:
            raise GmshMeshingError("Gmsh worker receipt metadata must be non-empty strings")
    qualities = (payload["min_sicn"], payload["mean_sicn"])
    if qualities != (None, None):
        if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in qualities):
            raise GmshMeshingError("Gmsh worker receipt quality must be positive finite numbers or both null")
        try:
            valid_quality = all(math.isfinite(item) and item > 0 for item in qualities)
        except OverflowError:
            valid_quality = False
        if not valid_quality or (qualities[0] > qualities[1] and not math.isclose(qualities[0], qualities[1], rel_tol=1e-12)):
            raise GmshMeshingError("Gmsh worker receipt quality must be finite, positive and ordered")
    values = dict(payload)
    values.pop("receipt_version")
    values["physical_groups"] = tuple(values["physical_groups"])
    values["roundtrip_physical_groups"] = tuple(values["roundtrip_physical_groups"])
    return GmshMeshReceipt(**values)


class GmshProcessBackend:
    """Run native import/generation/verification in a disposable child process."""

    def __init__(self, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = _validate_timeout(timeout_seconds)

    def mesh_step(
        self, source_step: Path, output_dir: Path, *,
        max_size_mm: float, min_size_mm: float | None = None,
    ) -> GmshMeshReceipt:
        timeout = _validate_timeout(self.timeout_seconds)
        maximum = _finite_positive(max_size_mm, name="max_size_mm")
        minimum = _finite_positive(
            max(0.01, maximum / 5.0) if min_size_mm is None else min_size_mm, name="min_size_mm",
        )
        if minimum > maximum:
            raise ValueError("min_size_mm cannot exceed max_size_mm")
        source_input, destination_input = source_step.expanduser(), output_dir.expanduser()
        if source_input.is_symlink() or not source_input.is_file():
            raise FileNotFoundError(f"STEP source is missing or not a regular file: {source_input}")
        if not 0 < source_input.stat().st_size <= MAX_STEP_BYTES:
            raise GmshMeshingError(f"STEP source size must be from 1 through {MAX_STEP_BYTES} bytes")
        if destination_input.exists() or destination_input.is_symlink():
            raise FileExistsError(f"output directory already exists: {destination_input}")
        source, destination = source_input.resolve(), destination_input.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".neurocad-gmsh-worker-", dir=destination.parent) as temporary:
            workspace = Path(temporary)
            snapshot, bundle = workspace / "source.step", workspace / "bundle"
            source_bytes, source_hash = _snapshot_step(source, snapshot)
            started = time.monotonic()
            try:
                returncode = _run_worker(_worker_command(snapshot, bundle, minimum, maximum), timeout)
            except subprocess.TimeoutExpired as exc:
                raise GmshMeshingError(
                    f"Gmsh worker exceeded {timeout:g} seconds and was terminated; no mesh bundle was published"
                ) from exc
            elapsed = time.monotonic() - started
            if returncode != 0:
                raise GmshMeshingError(_worker_error(workspace, returncode))
            receipt = _verified_receipt(bundle, source_hash, source_bytes, minimum, maximum)
            execution = {
                "receipt_version": EXECUTION_RECEIPT_VERSION, "status": "success",
                "supervisor": "single-worker-subprocess", "worker_returncode": returncode,
                "timeout_seconds": timeout, "worker_elapsed_seconds": elapsed,
                "source_step_sha256": source_hash, "mesh_sha256": receipt.mesh_sha256,
                "meshing_receipt_sha256": _sha256(bundle / "meshing-receipt.json"),
                "claim_boundary": "worker-wait timeout only; not RAM/CPU quotas, process-tree isolation or a whole-command deadline",
            }
            (bundle / "execution-receipt.json").write_text(
                json.dumps(execution, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8",
            )
            if {path.name for path in workspace.iterdir()} != {"source.step", "bundle"}:
                raise GmshMeshingError("Gmsh worker left unexpected workspace files")
            # The no-replace primitive requires sibling directories. Promote the
            # validated files inside our private directory before publishing it.
            snapshot.unlink()
            for name in ("design.msh", "meshing-receipt.json", "execution-receipt.json"):
                (bundle / name).rename(workspace / name)
            bundle.rmdir()
            publish_directory_noreplace(workspace, destination)
            return receipt


def _worker_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Internal NeuroCAD Gmsh worker")
    parser.add_argument("source", type=Path)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("minimum", type=float)
    parser.add_argument("maximum", type=float)
    args = parser.parse_args(argv)
    try:
        GmshBackend().mesh_step(args.source, args.bundle, min_size_mm=args.minimum, max_size_mm=args.maximum)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        # This path is inside the supervisor-owned workspace, not the destination.
        error = {"error_type": type(exc).__name__, "message": str(exc)[:2048]}
        (args.bundle.parent / "worker-error.json").write_text(
            json.dumps(error, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8",
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_worker_main())
