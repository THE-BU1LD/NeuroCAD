#!/usr/bin/env python3
"""Development-only Stage 1 plumbing smoke for the VeriCodeGen successor study.

This script uses scripted fixtures, not a language model. It exercises both
predeclared arms through final OpenSCAD -> STL artifacts, shared verification,
retry accounting, provenance hashing, and fail-closed logging. The outputs are
engineering evidence only and must never be interpreted as a scientific result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

from core.design_graph import Component, DesignGraph
from core.scad_export import design_to_scad
from research.vericodegen.verifier import load_mesh, verify_mesh


DEV_TASKS: tuple[dict[str, Any], ...] = (
    {
        "task_id": "DEV-BOX-001",
        "prompt": "Create a centered rectangular box 10 by 8 by 6 units.",
        "kind": "box",
        "geometry": {"kind": "box", "size": [10.0, 8.0, 6.0], "center": True},
        "constraints": {
            "watertight": True,
            "max_components": 1,
            "volume": {"min": 479.0, "max": 481.0},
            "extents": {
                "x": {"min": 9.99, "max": 10.01},
                "y": {"min": 7.99, "max": 8.01},
                "z": {"min": 5.99, "max": 6.01},
            },
        },
        "forced_retry": False,
    },
    {
        "task_id": "DEV-CYL-002",
        "prompt": "Create a centered cylinder of radius 3 and height 10 units.",
        "kind": "cylinder",
        "geometry": {"kind": "cylinder", "radius": 3.0, "height": 10.0, "center": True},
        "constraints": {
            "watertight": True,
            "max_components": 1,
            "volume": {"min": 280.0, "max": 285.0},
            "extents": {
                "x": {"min": 5.95, "max": 6.05},
                "y": {"min": 5.95, "max": 6.05},
                "z": {"min": 9.99, "max": 10.01},
            },
        },
        "forced_retry": False,
    },
    {
        "task_id": "DEV-RETRY-003",
        "prompt": "Create a centered cube with side length 4 units.",
        "kind": "box",
        "geometry": {"kind": "box", "size": [4.0, 4.0, 4.0], "center": True},
        "constraints": {
            "watertight": True,
            "max_components": 1,
            "volume": {"min": 63.5, "max": 64.5},
            "extents": {
                "x": {"min": 3.99, "max": 4.01},
                "y": {"min": 3.99, "max": 4.01},
                "z": {"min": 3.99, "max": 4.01},
            },
        },
        "forced_retry": True,
    },
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _direct_scad(task: dict[str, Any], *, intentionally_invalid: bool) -> str:
    if intentionally_invalid:
        return "$fn = 64;\ncube(size=[4, 4, 4], center=true)\nBROKEN_TOKEN\n"
    geometry = task["geometry"]
    if task["kind"] == "box":
        x, y, z = geometry["size"]
        return f"$fn = 64;\ncube(size=[{x}, {y}, {z}], center=true);\n"
    if task["kind"] == "cylinder":
        return (
            "$fn = 64;\n"
            f"cylinder(r={geometry['radius']}, h={geometry['height']}, center=true);\n"
        )
    raise ValueError(f"unsupported direct development kind: {task['kind']}")


def _structured_scad(task: dict[str, Any], *, intentionally_invalid: bool) -> str:
    geometry = dict(task["geometry"])
    if intentionally_invalid:
        geometry = {"kind": "unsupported_stage1_fixture"}
    design = DesignGraph(title=f"VeriCodeGen Stage 1 {task['task_id']}")
    design.add_component(
        Component(
            name="body",
            params={"geometry": geometry},
            operation="union",
            role="body",
        )
    )
    return design_to_scad(design, fn=64)


def _compile(scad_path: Path, stl_path: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        ["openscad", "-o", str(stl_path), str(scad_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode == 0 and stl_path.is_file() and stl_path.stat().st_size > 0, proc.stdout


def _run_attempt(
    *,
    task: dict[str, Any],
    arm: str,
    attempt: int,
    outdir: Path,
    intentionally_invalid: bool,
) -> dict[str, Any]:
    stem = f"{task['task_id']}-{arm}-attempt{attempt}"
    scad_path = outdir / f"{stem}.scad"
    stl_path = outdir / f"{stem}.stl"
    compile_log_path = outdir / f"{stem}.openscad.log"

    record: dict[str, Any] = {
        "task_id": task["task_id"],
        "prompt": task["prompt"],
        "arm": arm,
        "attempt": attempt,
        "development_fixture": True,
        "scripted_output": True,
        "intentionally_invalid_fixture": intentionally_invalid,
        "compile_success": False,
        "verifier_passed": False,
        "failure_type": None,
    }

    try:
        if arm == "direct":
            scad = _direct_scad(task, intentionally_invalid=intentionally_invalid)
        elif arm == "structured":
            scad = _structured_scad(task, intentionally_invalid=intentionally_invalid)
        else:
            raise ValueError(f"unknown arm: {arm}")
    except Exception as exc:
        record["failure_type"] = "generation_or_structured_compile_error"
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record

    scad_path.write_text(scad, encoding="utf-8")
    record["scad_path"] = str(scad_path)
    record["scad_sha256"] = _sha256(scad_path)

    compiled, compile_log = _compile(scad_path, stl_path)
    compile_log_path.write_text(compile_log, encoding="utf-8")
    record["compile_log_path"] = str(compile_log_path)
    record["compile_success"] = compiled
    if not compiled:
        record["failure_type"] = "openscad_compile_failure"
        return record

    record["artifact_path"] = str(stl_path)
    record["artifact_sha256"] = _sha256(stl_path)

    try:
        mesh = load_mesh(stl_path)
        report = verify_mesh(mesh, task["constraints"])
    except Exception as exc:
        record["failure_type"] = "verifier_error"
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record

    record["verifier_passed"] = bool(report.passed)
    record["verifier_failures"] = list(report.failures)
    record["measurements"] = report.measurements
    if not report.passed:
        record["failure_type"] = "hard_constraint_failure"
    return record


def run_stage1(outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    attempts: list[dict[str, Any]] = []
    finals: list[dict[str, Any]] = []

    for task in DEV_TASKS:
        for arm in ("direct", "structured"):
            max_attempts = 2 if task["forced_retry"] else 1
            final: dict[str, Any] | None = None
            for attempt in range(1, max_attempts + 1):
                intentionally_invalid = bool(task["forced_retry"] and attempt == 1)
                record = _run_attempt(
                    task=task,
                    arm=arm,
                    attempt=attempt,
                    outdir=outdir,
                    intentionally_invalid=intentionally_invalid,
                )
                attempts.append(record)
                if record["compile_success"] and record["verifier_passed"]:
                    final = dict(record)
                    final["retries_used"] = attempt - 1
                    break
            if final is None:
                final = dict(attempts[-1])
                final["retries_used"] = max_attempts - 1
            finals.append(final)

    summary = {
        "stage": "VeriCodeGen Stage 1 development smoke",
        "scientific_evidence": False,
        "claim_boundary": (
            "Scripted development fixtures only; confirms plumbing, shared verification, "
            "retry accounting, and provenance. It is not benchmark/model evidence."
        ),
        "git_commit": os.environ.get("GITHUB_SHA") or os.environ.get("GIT_COMMIT"),
        "python": sys.version,
        "platform": platform.platform(),
        "task_count": len(DEV_TASKS),
        "arms": ["direct", "structured"],
        "final_cells": len(finals),
        "passed_final_cells": sum(bool(row["compile_success"] and row["verifier_passed"]) for row in finals),
        "total_attempts": len(attempts),
        "retry_cells": sum(int(row.get("retries_used", 0) > 0) for row in finals),
    }

    (outdir / "attempts.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in attempts),
        encoding="utf-8",
    )
    (outdir / "finals.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in finals),
        encoding="utf-8",
    )
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    if summary["passed_final_cells"] != summary["final_cells"]:
        raise SystemExit(f"Stage 1 final-cell failure: {summary}")
    if summary["retry_cells"] != 2:
        raise SystemExit(f"Stage 1 retry accounting mismatch: {summary}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="out/vericodegen_stage1")
    args = parser.parse_args()
    summary = run_stage1(Path(args.outdir))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
