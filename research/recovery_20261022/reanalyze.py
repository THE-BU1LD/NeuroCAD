"""Reanalyze retained NeuroCAD artifacts without executing any study case.

This standard-library-only program writes a new report, or compares a retained
report using --check. It never changes historical sources, protocols or results.
Report generation is not a fresh experiment or external independent validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
V2 = "research/physics_v2"
V2_RUN = f"{V2}/runs/NC-PHYS-V2-CONFIRM-001"
COMPILER_RUN = "research/runs/NC-REPRO-508EC40"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def object_at(root: Path, name: str) -> dict[str, Any]:
    value = json.loads((root / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {name}")
    return value


def records_at(root: Path, name: str) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in (root / name).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"expected JSON object records: {name}")
    return rows


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def wilson(successes: int, total: int) -> list[float]:
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def endpoint(rows: list[dict[str, Any]], families: tuple[str, ...], arm: str,
             field: str, expected: bool) -> dict[str, Any]:
    selected = [row for row in rows if row["family"] in families]
    count = sum(row["arms"][arm].get(field) is expected for row in selected)
    require(bool(selected), f"empty endpoint: {families}, {arm}, {field}")
    return {"successes": count, "total": len(selected), "rate": count / len(selected),
            "wilson_95_descriptive": wilson(count, len(selected))}


def retained_compiler_hashes(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    failures = []
    matches = 0
    entries = manifest["artifact_sha256"]
    for name, expected in sorted(entries.items()):
        relative = PurePosixPath(name)
        require(not relative.is_absolute() and ".." not in relative.parts
                and relative.as_posix() == name and "\\" not in name, "unsafe manifest path")
        path = root / COMPILER_RUN / name
        if path.is_symlink() or not path.is_file():
            failures.append({"path": name, "error": "missing or not a regular file"})
        else:
            actual = digest(path)
            if actual == expected:
                matches += 1
            else:
                failures.append({"path": name, "error": "sha256 mismatch",
                                 "expected_sha256": expected, "actual_sha256": actual})
    return {"status": "PASS" if not failures else "FAIL", "listed": len(entries),
            "matched": matches, "failures": failures,
            "scope": "Listed retained bytes only; hash agreement does not establish independence or physical validity."}


def analyze(root: Path) -> dict[str, Any]:
    ledger = object_at(root, f"{V2}/CONFIRMATORY_EXECUTION.json")
    freeze = object_at(root, f"{V2}/frozen/freeze.json")
    manifest = object_at(root, f"{V2_RUN}/manifest.json")
    metrics = object_at(root, f"{V2_RUN}/metrics.json")
    cases = records_at(root, f"{V2}/frozen/NC-PHYS-V2-CONFIRM.jsonl")
    rows = records_at(root, f"{V2_RUN}/raw_results.jsonl")
    for name, expected in (
        (f"{V2}/frozen/freeze.json", ledger["freeze_sha256"]),
        (f"{V2}/frozen/NC-PHYS-V2-CONFIRM.jsonl", freeze["cases_file_sha256"]),
        (f"{V2_RUN}/manifest.json", ledger["manifest_sha256"]),
        (f"{V2_RUN}/metrics.json", ledger["metrics_sha256"]),
        (f"{V2_RUN}/raw_results.jsonl", manifest["raw_results_sha256"]),
    ):
        require(digest(root / name) == expected, f"retained Physics v2 hash mismatch: {name}")
    require(ledger["status"] == "EXECUTED_ONCE", "original ledger is not final")
    require(manifest["source_hashes"] == freeze["source_hashes"], "frozen source declarations differ")
    require(manifest["metrics_sha256"] == ledger["metrics_sha256"], "metrics digest declarations differ")
    require(len(rows) == len(cases) == 216, "original matrix does not contain 216 cases")
    require(len({row["task_id"] for row in rows}) == 216, "duplicate raw task IDs")
    require({row["task_id"] for row in rows} == {case["task_id"] for case in cases}, "raw/frozen case IDs differ")
    require(not any("execution_error" in row for row in rows), "original run records execution errors")
    case_families = Counter(case["family"] for case in cases)
    require(Counter(row["family"] for row in rows) == case_families, "raw/frozen family counts differ")
    semantic = ("geometry_input_contradiction", "material_input_contradiction", "load_input_contradiction")
    definitions = {
        "valid_full_acceptance": (("valid",), "full", "accepted", True),
        "valid_full_determinism": (("valid",), "full", "deterministic", True),
        "full_geometry_input_detection": ((semantic[0],), "full", "detected", True),
        "full_material_input_detection": ((semantic[1],), "full", "detected", True),
        "full_load_input_detection": ((semantic[2],), "full", "detected", True),
        "full_stale_expected_hash_detection": (("stale_expected_hash",), "full", "detected", True),
        "hash_only_semantic_non_detection": (semantic, "hash_only", "detected", False),
        "unbound_semantic_non_detection": (semantic, "unbound", "detected", False),
        "full_post_mutation_detection": (("post_result_geometry_mutation",), "full", "detected", True),
        "hash_only_post_mutation_detection": (("post_result_geometry_mutation",), "hash_only", "detected", True),
        "unbound_post_mutation_non_detection": (("post_result_geometry_mutation",), "unbound", "detected", False),
        "full_non_geometric_specificity": (("non_geometric_mutation",), "full", "current", True),
        "hash_only_non_geometric_specificity": (("non_geometric_mutation",), "hash_only", "current", True),
    }
    endpoints = {name: endpoint(rows, *definition) for name, definition in definitions.items()}
    for name, value in endpoints.items():
        recorded = metrics["endpoints"][name]
        require((value["successes"], value["total"]) == (recorded["successes"], recorded["total"]),
                f"endpoint count mismatch: {name}")
        require(all(math.isclose(a, b, rel_tol=0, abs_tol=1e-14)
                    for a, b in zip(value["wilson_95_descriptive"], recorded["wilson_95"])),
                f"descriptive interval mismatch: {name}")
    mutations = [row for row in rows if row["family"] == "post_result_geometry_mutation"]
    full_only = sum(row["arms"]["full"]["detected"] and not row["arms"]["unbound"]["detected"] for row in mutations)
    unbound_only = sum(row["arms"]["unbound"]["detected"] and not row["arms"]["full"]["detected"] for row in mutations)
    n = full_only + unbound_only
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(min(full_only, unbound_only) + 1)) / 2**n) if n else 1.0
    pair = {"full_only": full_only, "unbound_only": unbound_only, "exact_two_sided_mcnemar_p": p}
    require(pair == metrics["paired_full_vs_unbound_post_mutation"], "paired comparison differs from retained metrics")
    timing = {}
    for arm in ("full", "hash_only", "unbound"):
        observations = sorted(row["arms"][arm]["elapsed_ms"] for row in rows
                              if row["arms"][arm].get("elapsed_ms") is not None)
        timing[arm] = {"count": len(observations), "upper_median_ms": observations[len(observations) // 2],
                       "conventional_median_ms": statistics.median(observations),
                       "p95_ms": observations[math.ceil(0.95 * len(observations)) - 1], "maximum_ms": max(observations)}
        require(timing[arm]["upper_median_ms"] == metrics["timing_diagnostics"][arm]["median_ms"], "timing mismatch")
    sizes = sorted(row["arms"]["full"]["report_bytes"] for row in rows if row["arms"]["full"].get("report_bytes") is not None)
    compiler_manifest = object_at(root, f"{COMPILER_RUN}/manifest.json")
    compiler_results = object_at(root, f"{COMPILER_RUN}/metrics/results.json")
    systems = {}
    for name, system in compiler_results["experiments"]["NC-EXP-001"]["systems"].items():
        predictions = system["records"]
        require(len({row["task_id"] for row in predictions}) == len(predictions), "duplicate compiler task IDs")
        systems[name] = {"overall": {"passed": sum(row["passed"] is True for row in predictions), "total": len(predictions)},
                         "splits": {split: {"passed": sum(row["passed"] is True for row in predictions if row["split"] == split),
                                            "total": sum(row["split"] == split for row in predictions)}
                                    for split in ("train", "validation", "test")}}
    inputs = (f"{V2}/CONFIRMATORY_EXECUTION.json", f"{V2}/frozen/freeze.json", f"{V2}/frozen/NC-PHYS-V2-CONFIRM.jsonl",
              f"{V2_RUN}/manifest.json", f"{V2_RUN}/metrics.json", f"{V2_RUN}/raw_results.jsonl",
              f"{COMPILER_RUN}/manifest.json", f"{COMPILER_RUN}/metrics/results.json")
    return {
        "schema_version": "nc-retained-evidence-reanalysis-v1",
        "mode": "REANALYSIS_ONLY_NO_CASE_EXECUTION",
        "input_sha256": {name: digest(root / name) for name in inputs},
        "physics_v2": {
            "original_execution_commit": manifest["git_commit"], "original_platform": manifest["platform"],
            "case_count": len(rows), "family_counts": dict(sorted(case_families.items())),
            "model_counts": dict(sorted(Counter(case["model"] for case in cases).items())),
            "status": "SUPPORTED_WITHIN_CONTROLLED_CONTRACT" if all(v["successes"] == v["total"] for v in endpoints.values()) else "MIXED",
            "endpoints": endpoints, "paired_full_vs_unbound_post_mutation": pair,
            "timing_successful_evaluations_only": timing,
            "receipt_size_bytes": {"count": len(sizes), "upper_median": sizes[len(sizes) // 2],
                                   "conventional_median": statistics.median(sizes), "maximum": max(sizes)},
            "source_declarations_match_freeze": True,
            "source_declaration_boundary": "Equality of retained manifest and freeze declarations; inspect the frozen checkout to verify source bytes.",
            "interpretation": "Fixed synthetic contract conformance; no physical or independent external validation. Intervals are descriptive.",
        },
        "compiler": {
            "classification": "MIXED_TERMINAL", "systems": systems,
            "retained_artifact_integrity": retained_compiler_hashes(root, compiler_manifest),
            "interpretation": "Project-generated grammar conformance. Retrieval overall includes training tasks; prefer split-specific numbers.",
        },
        "median_convention": "Frozen analyzer uses upper middle order statistic. Conventional medians shown as separate post-outcome descriptive reanalysis.",
        "boundaries": ["No case was executed.", "No original result was overwritten.",
                       "Historical typed-parser causal claim remains falsified.", "No Kaggle execution is established by these macOS manifests."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", type=Path, help="New output JSON path; existing files are refused.")
    destination.add_argument("--check", type=Path, help="Compare computed canonical JSON with an existing report.")
    args = parser.parse_args()
    report = analyze(args.root.resolve())
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.check is not None:
        require(args.check.read_bytes() == text.encode("utf-8"), "reanalysis differs from retained report")
        print("Reanalysis matches retained report byte-for-byte.")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        print(f"Wrote {args.output}")
    integrity = report["compiler"]["retained_artifact_integrity"]
    print(f"Compiler artifact integrity: {integrity['status']} ({integrity['matched']}/{integrity['listed']} matching).")
    print("This was artifact reanalysis, not a new experiment or independent replication.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
