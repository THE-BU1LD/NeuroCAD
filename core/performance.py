"""Reproducible local performance characterization for source generation."""

from __future__ import annotations

import hashlib
import math
import platform
import statistics
import sys
import time
import tracemalloc
from typing import Any

from core.ir import validate_program
from core.ir_adapter import design_graph_to_ir
from core.ir_export import program_to_scad
from core.prompt_engine import generate_design
from core.validation import validate_design

STAGES = (
    "parse_and_generate",
    "validate_design",
    "lower_to_ir",
    "validate_ir",
    "emit_scad",
)


def _summary(samples: list[float]) -> dict[str, Any]:
    ordered = sorted(samples)
    count = len(ordered)
    p95_index = max(0, min(count - 1, math.ceil(0.95 * count) - 1))
    mean = statistics.fmean(samples)
    standard_deviation = statistics.stdev(samples) if count > 1 else 0.0
    margin = 1.96 * standard_deviation / math.sqrt(count)
    return {
        "min": ordered[0],
        "median": statistics.median(ordered),
        "p95_nearest_rank": ordered[p95_index],
        "max": ordered[-1],
        "mean": mean,
        "standard_deviation": standard_deviation,
        "mean_95_percent_ci_normal_approximation": [max(0.0, mean - margin), mean + margin],
    }


def _run_pipeline(prompt: str, fn: int) -> tuple[str, dict[str, float], dict[str, int]]:
    timings: dict[str, float] = {}
    total_started = time.perf_counter_ns()

    started = time.perf_counter_ns()
    design = generate_design(prompt)
    timings[STAGES[0]] = (time.perf_counter_ns() - started) / 1e9

    started = time.perf_counter_ns()
    validation = validate_design(design)
    timings[STAGES[1]] = (time.perf_counter_ns() - started) / 1e9
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))

    started = time.perf_counter_ns()
    program = design_graph_to_ir(design)
    timings[STAGES[2]] = (time.perf_counter_ns() - started) / 1e9

    started = time.perf_counter_ns()
    ir_validation = validate_program(program)
    timings[STAGES[3]] = (time.perf_counter_ns() - started) / 1e9
    if not ir_validation.valid:
        details = "; ".join(f"{issue.path}: {issue.code}: {issue.message}" for issue in ir_validation.errors)
        raise ValueError(f"canonical IR is invalid: {details}")

    started = time.perf_counter_ns()
    scad = program_to_scad(program, fn=fn)
    timings[STAGES[4]] = (time.perf_counter_ns() - started) / 1e9
    timings["total"] = (time.perf_counter_ns() - total_started) / 1e9
    counts = {
        "design_components": len(design.components),
        "design_connections": len(design.connections),
        "ir_nodes": len(program.nodes),
        "constraints": len(program.constraints),
        "scad_bytes": len(scad.encode("utf-8")),
    }
    return scad, timings, counts


def profile_generation(
    prompt: str,
    *,
    iterations: int = 20,
    fn: int = 64,
    warmup_iterations: int = 3,
) -> dict[str, Any]:
    """Profile each deterministic compiler stage and retain the raw samples."""

    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4096:
        raise ValueError("prompt must contain from 1 through 4096 characters")
    if isinstance(iterations, bool) or not isinstance(iterations, int) or not 1 <= iterations <= 1000:
        raise ValueError("iterations must be an integer from 1 through 1000")
    if isinstance(warmup_iterations, bool) or not isinstance(warmup_iterations, int) or not 1 <= warmup_iterations <= 100:
        raise ValueError("warmup_iterations must be an integer from 1 through 100")
    if isinstance(fn, bool) or not isinstance(fn, int) or not 3 <= fn <= 1000:
        raise ValueError("fn must be an integer from 3 through 1000")

    normalized_prompt = prompt.strip()
    warmup_hashes: set[str] = set()
    workload: dict[str, int] | None = None
    for _ in range(warmup_iterations):
        scad, _, workload = _run_pipeline(normalized_prompt, fn)
        warmup_hashes.add(hashlib.sha256(scad.encode("utf-8")).hexdigest())
    if len(warmup_hashes) != 1 or workload is None:
        raise RuntimeError("compiler output changed during performance warmup")

    samples: dict[str, list[float]] = {stage: [] for stage in (*STAGES, "total")}
    output_hashes: set[str] = set()
    tracemalloc.start()
    try:
        for _ in range(iterations):
            scad, timings, current_workload = _run_pipeline(normalized_prompt, fn)
            if current_workload != workload:
                raise RuntimeError("compiler workload changed during performance profiling")
            for stage, duration in timings.items():
                samples[stage].append(duration)
            output_hashes.add(hashlib.sha256(scad.encode("utf-8")).hexdigest())
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    deterministic_output = len(output_hashes) == 1 and output_hashes == warmup_hashes
    if not deterministic_output:
        raise RuntimeError("compiler output changed during performance profiling")
    total_seconds = sum(samples["total"])
    output_sha256 = next(iter(output_hashes))
    return {
        "profile_version": "neurocad-performance-v2",
        "scope": (
            "in-process prompt parsing/generation, design validation, canonical IR lowering/validation, "
            "and OpenSCAD source emission; excludes daemon, file I/O, and OpenSCAD kernel"
        ),
        "measurement": {
            "clock": "time.perf_counter_ns",
            "memory_instrumentation": "tracemalloc enabled during recorded iterations",
            "confidence_interval": "two-sided 95% normal approximation for the arithmetic mean",
        },
        "iterations": iterations,
        "warmup_iterations": warmup_iterations,
        "fn": fn,
        "prompt_sha256": hashlib.sha256(normalized_prompt.encode("utf-8")).hexdigest(),
        "deterministic_output": True,
        "output_sha256": output_sha256,
        "workload": workload,
        "latency_seconds": _summary(samples["total"]),
        "stage_latency_seconds": {stage: _summary(samples[stage]) for stage in STAGES},
        "raw_samples_seconds": samples,
        "throughput_per_second": iterations / total_seconds if total_seconds else None,
        "tracemalloc_peak_bytes": peak_bytes,
        "runtime": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
            "platform": platform.platform(),
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
    }
