"""Compare complete, matched language diagnostics without claiming SOTA or significance."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from . import language_evaluation
from .conversational_parser import EditProposal
from .json_io import read_bounded_utf8, strict_json_loads
from .language_evaluation import EXECUTION_POLICY, RUN_VERSION, score_proposal, validate_challenge
from .project import parse_project

FILES = {"challenge.json", "receipt.json", "results.jsonl", "summary.json"}
MAX_REPORT_BYTES = 16 * 1024 * 1024
METRICS = ("passed", "semantic_exact", "fail_closed", "unsafe_acceptance", "wrong_candidate", "status_exact", "protection_match")


def _read(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Report artifacts must be regular files")
    return read_bounded_utf8(path, max_bytes=MAX_REPORT_BYTES, label="language report")


def load_run(directory: Path) -> dict[str, Any]:
    """Check hashes, case identity, completeness and scores before comparison.

    Re-scoring requires the same scorer implementation. A manifest is a local
    integrity seal, not proof of independent authorship or provider execution.
    """
    manifest = strict_json_loads(_read(directory / "manifest.json"))
    if (not isinstance(manifest, dict) or manifest.get("version") != "neurocad-language-manifest-v1"
            or not isinstance(manifest.get("files"), dict) or set(manifest["files"]) != FILES):
        raise ValueError("A complete language manifest is required")
    texts = {name: _read(directory / name) for name in sorted(FILES)}
    if any(hashlib.sha256(text.encode("utf-8")).hexdigest() != manifest["files"][name] for name, text in texts.items()):
        raise ValueError("Language report integrity mismatch")
    receipt = strict_json_loads(texts["receipt.json"])
    summary = strict_json_loads(texts["summary.json"])
    challenge = validate_challenge(strict_json_loads(texts["challenge.json"]))
    results = [strict_json_loads(line) for line in texts["results.jsonl"].splitlines()]
    if not isinstance(receipt, dict) or not isinstance(summary, dict):
        raise ValueError("Receipt and summary must be objects")  # noqa: TRY004 - malformed artifact, public ValueError contract
    if (receipt.get("version") != RUN_VERSION or receipt.get("outcomes_observed") is not False
            or receipt.get("execution_policy") != EXECUTION_POLICY
            or receipt.get("scorer_sha256") != hashlib.sha256(Path(language_evaluation.__file__).read_bytes()).hexdigest()
            or not isinstance(receipt.get("source_identity"), dict) or not receipt["source_identity"]):
        raise ValueError("Unsupported run or scorer policy; historical runs must retain their own scorer")
    if (summary.get("integrity_valid") is not True or summary.get("source_unchanged") is not True
            or summary.get("dataset_unchanged") is not True or summary.get("outcomes_observed") is not True
            or any(summary.get(key) != value for key, value in receipt.items() if key != "outcomes_observed")
            or receipt.get("dataset_sha256") != manifest["files"]["challenge.json"]):
        raise ValueError("Run identity or completion is invalid")
    cases = challenge["cases"]
    if (len(results) != len(cases) or receipt.get("case_count") != len(cases)
            or summary.get("completed_cases") != len(cases)):
        raise ValueError("Partial runs cannot be compared")
    for case, result in zip(cases, results):
        if (not isinstance(result, dict) or result.get("id") != case["id"]
                or result.get("category") != case["category"] or result.get("expected") != case["expected"]):
            raise ValueError("Case order, identity or labels differ from frozen input")
        flags = (*METRICS, "provider_error", "baseline_unchanged", "history_unchanged", "input_unchanged")
        if any(type(result.get(key)) is not bool for key in flags):
            raise ValueError("Result flags must be booleans")
        if result["input_unchanged"] != (result["baseline_unchanged"] and result["history_unchanged"]):
            raise ValueError("Input integrity flags disagree")
        observed = result.get("observed")
        if result["provider_error"]:
            expected_scores = dict.fromkeys(METRICS, False)
            if observed is not None:
                raise ValueError("Provider errors must not contain a scored proposal")
        else:
            if not isinstance(observed, dict) or observed.get("source") != case["source"]:
                raise ValueError("Observed proposal does not match its prompt")
            try:
                candidate = None if observed["candidate"] is None else parse_project(json.dumps(observed["candidate"], allow_nan=False))
                proposal = EditProposal(
                    source=observed["source"], baseline_sha256=observed["baseline_sha256"],
                    interpreter=observed["interpreter"], status=observed["status"], actions=tuple(observed["actions"]),
                    preserve=tuple(observed["preserve"]), questions=tuple(observed["questions"]),
                    unsupported=tuple(observed["unsupported"]), acknowledged=tuple(observed["acknowledged"]), candidate=candidate,
                )
                project = parse_project(json.dumps(challenge["projects"][case["project"]], allow_nan=False))
                expected_scores = score_proposal(proposal, case["expected"], project)
            except (KeyError, TypeError, ValueError, OverflowError) as exc:
                raise ValueError("Invalid retained proposal") from exc
            for key in ("passed", "semantic_exact", "fail_closed"):
                expected_scores[key] = expected_scores[key] and result["input_unchanged"]
        if any(result[key] != expected_scores[key] for key in METRICS):
            raise ValueError("Retained score does not reproduce against frozen labels")
    counters = {f"{metric}_count": sum(result[metric] for result in results)
                for metric in (*METRICS[:-1], "provider_error")}
    counters["input_mutation_count"] = sum(not result["input_unchanged"] for result in results)
    valid = sum(case["expected"]["status"] == "proposal" for case in cases)
    rejection = len(cases) - valid
    counters.update(valid_intent_cases=valid, rejection_intent_cases=rejection)
    if any(summary.get(key) != value for key, value in counters.items()):
        raise ValueError("Summary counts do not reproduce from complete case records")
    for metric, denominator in (("semantic_exact", valid), ("fail_closed", rejection)):
        rate = counters[f"{metric}_count"] / denominator if denominator else None
        if summary.get(f"{metric}_rate") != rate:
            raise ValueError("Summary rate disagrees with its declared denominator")
    return {"receipt": receipt, "summary": summary, "cases": cases, "results": results,
            "manifest_sha256": hashlib.sha256(_read(directory / "manifest.json").encode("utf-8")).hexdigest()}


def compare_runs(left_path: Path, right_path: Path) -> dict[str, Any]:
    left, right = load_run(left_path), load_run(right_path)
    if left["receipt"]["dataset_sha256"] != right["receipt"]["dataset_sha256"]:
        raise ValueError("Comparison requires the exact same frozen challenge bytes")
    endpoints = {}
    for metric in ("passed", "semantic_exact", "fail_closed", "unsafe_acceptance"):
        pairs = [(case, a, b) for case, a, b in zip(left["cases"], left["results"], right["results"])
                 if (metric not in {"semantic_exact", "fail_closed"}
                     or (case["expected"]["status"] == "proposal") == (metric == "semantic_exact"))]
        cells = {"both_true": 0, "left_only": 0, "right_only": 0, "both_false": 0}
        discordant = []
        for case, a, b in pairs:
            cell = "both_true" if a[metric] and b[metric] else "left_only" if a[metric] else "right_only" if b[metric] else "both_false"
            cells[cell] += 1
            if a[metric] != b[metric]:
                discordant.append({"id": case["id"], "category": case["category"], "left": a[metric], "right": b[metric]})
        endpoints[metric] = {"denominator": len(pairs), **cells,
                             "right_minus_left_rate": (cells["right_only"] - cells["left_only"]) / len(pairs) if pairs else None,
                             "higher_is_better": metric != "unsafe_acceptance", "discordant_cases": discordant}
    return {"version": "neurocad-language-comparison-v1", "dataset_sha256": left["receipt"]["dataset_sha256"],
            "left": {"manifest_sha256": left["manifest_sha256"], "receipt": left["receipt"]},
            "right": {"manifest_sha256": right["manifest_sha256"], "receipt": right["receipt"]}, "endpoints": endpoints,
            "claim_boundary": "Matched development diagnostics only. No SOTA, independent reproduction, significance, cost parity or physical accuracy claim. Case clustering and a prospective statistical protocol are required for inference."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = compare_runs(args.left, args.right)
        with args.output.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(result, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Comparison refused ({type(exc).__name__}); no successful comparison claimed\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
