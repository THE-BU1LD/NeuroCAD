"""Reproducible local performance characterization for source generation."""

from __future__ import annotations

import hashlib
import platform
import statistics
import sys
import time
import tracemalloc
from typing import Any

from text_to_cad import TextToCAD


def profile_generation(prompt: str, *, iterations: int = 20, fn: int = 64) -> dict[str, Any]:
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4096:
        raise ValueError("prompt must contain from 1 through 4096 characters")
    if isinstance(iterations, bool) or not isinstance(iterations, int) or not 1 <= iterations <= 1000:
        raise ValueError("iterations must be an integer from 1 through 1000")
    if isinstance(fn, bool) or not isinstance(fn, int) or not 3 <= fn <= 1000:
        raise ValueError("fn must be an integer from 3 through 1000")

    generator = TextToCAD(fn=fn)
    warmup = generator.build(prompt.strip())
    if not warmup.validation.valid:
        raise ValueError("; ".join(warmup.validation.errors))

    timings: list[float] = []
    output_hashes: set[str] = set()
    tracemalloc.start()
    try:
        for _ in range(iterations):
            started = time.perf_counter()
            document = generator.build(prompt.strip())
            timings.append(time.perf_counter() - started)
            if not document.validation.valid:
                raise RuntimeError("a previously valid prompt became invalid during profiling")
            output_hashes.add(hashlib.sha256(document.scad.encode("utf-8")).hexdigest())
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    ordered = sorted(timings)
    p95_index = max(0, min(len(ordered) - 1, (95 * len(ordered) + 99) // 100 - 1))
    total = sum(timings)
    return {
        "profile_version": "neurocad-performance-v1",
        "scope": "in-process prompt parsing, validation, IR, and OpenSCAD source generation; excludes daemon and OpenSCAD kernel",
        "iterations": iterations,
        "fn": fn,
        "prompt_sha256": hashlib.sha256(prompt.strip().encode("utf-8")).hexdigest(),
        "deterministic_output": len(output_hashes) == 1,
        "output_sha256": next(iter(output_hashes)),
        "latency_seconds": {
            "min": min(timings),
            "median": statistics.median(timings),
            "p95_nearest_rank": ordered[p95_index],
            "max": max(timings),
            "mean": statistics.fmean(timings),
        },
        "throughput_per_second": iterations / total if total else None,
        "tracemalloc_peak_bytes": peak_bytes,
        "runtime": {"python": platform.python_version(), "executable": sys.executable, "platform": platform.platform()},
    }
