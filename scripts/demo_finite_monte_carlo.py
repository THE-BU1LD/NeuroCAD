"""Retain a bounded numerical demonstration; no manufacturing observations."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from core.scientific_kernel import monte_carlo_propagate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    report = {"scope": "generated arithmetic demonstration only", "samples": [], "cases": []}
    try:
        for name, values in [("large_constant", [1e308] * 8), ("opposite_finite", [-1e308, 1e308])]:
            iterator = iter(values)
            result = monte_carlo_propagate(lambda _, iterator=iterator: next(iterator), (0.0,), ((0.0,),), samples=len(values), seed=41)
            report["cases"].append({"case": name, "raw_outputs": values, "report": result})

        def linear(draw):
            value = float(draw[0] + 2 * draw[1])
            report["samples"].append({"input": draw.tolist(), "output": value})
            return value

        result = monte_carlo_propagate(linear, (2.0, -3.0), ((1.0, 0.25), (0.25, 2.0)), samples=8, seed=79)
        report["cases"].append({"case": "seeded_linear", "report": result})
        report["status"] = "COMPLETED"
    except BaseException as exc:
        report.update(status="FAILED", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        root = Path(__file__).resolve().parents[1]
        report["source_sha256"] = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in ["core/scientific_kernel.py", "scripts/demo_finite_monte_carlo.py"]}
        report["wall_seconds"] = time.perf_counter() - started
        with (args.output / "report.json").open("x") as file:
            json.dump(report, file, indent=2, allow_nan=False)
            file.write("\n")
    print(json.dumps({"status": report["status"], "cases": len(report["cases"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
