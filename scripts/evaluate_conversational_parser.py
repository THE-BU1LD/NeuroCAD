"""Retain local constructed regression outcomes; never claim broad NLP accuracy."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.conversational_parser import parse_conversation
from core.json_io import read_bounded_utf8, strict_json_loads
from core.project import read_project, semantic_diff, serialize_project


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "docs/examples/conversation/evaluation-v1.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists() or args.output_dir.is_symlink():
        raise ValueError("Evaluation output must be a new directory")
    text = read_bounded_utf8(args.dataset, max_bytes=262144, label="conversation evaluation")
    dataset = strict_json_loads(text)
    if not isinstance(dataset, dict) or dataset.get("version") != "neurocad-conversation-regression-v1":
        raise ValueError("Unsupported evaluation dataset")
    baseline = args.dataset.parent / dataset["baseline"]
    project = read_project(baseline)
    before = serialize_project(project)
    cases = dataset["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 1000:
        raise ValueError("Evaluation needs 1 through 1000 cases")
    results = []
    for case in cases:
        proposal = parse_conversation(case["source"], project)
        passed = proposal.status == case["expected_status"]
        if proposal.candidate is not None:
            expected = case["expected_wall_mm"]
            passed = passed and isinstance(expected, (int, float)) and math.isclose(proposal.candidate.spec.wall_mm, expected, abs_tol=1e-9)
            passed = passed and all(change["field"] == "wall_mm" for change in semantic_diff(project, proposal.candidate))
        else:
            passed = passed and case["expected_wall_mm"] is None
        passed = passed and serialize_project(project) == before
        results.append({"id": case["id"], "passed": passed, "expected": case, "observed": proposal.to_dict()})
    summary = {
        "passed": all(result["passed"] for result in results), "cases": len(results),
        "passed_count": sum(result["passed"] for result in results),
        "unique_source_count": len({case["source"] for case in cases}),
        "dataset_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "baseline_file_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
        "baseline_unchanged": serialize_project(project) == before,
        "claim_boundary": dataset["claim"], "live_provider_evaluated": False,
    }
    args.output_dir.mkdir(parents=True)
    for name, value in (("results.json", results), ("summary.json", summary)):
        (args.output_dir / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
