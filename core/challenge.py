"""Strict evaluator for frozen prompt challenge sets.

Challenge sets may contain both accepted prompts with semantic signatures and
prompts that must be rejected.  This is deliberately separate from the generated
benchmark so a stored dataset is never silently regenerated or overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess  # nosec B404
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from text_to_cad import TextToCAD

from .artifacts import write_text_atomic
from .benchmark import program_signature, semantic_signatures_equal

CHALLENGE_VERSION = "neurocad-prompt-challenge-v1"
ALLOWED_SPLITS = frozenset({"development", "validation", "test"})


def _execution_provenance() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    source = Path(__file__).resolve()
    try:
        commit = subprocess.run(  # nosec B603 B607
            ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True, timeout=10
        ).stdout.strip()
        state = subprocess.run(  # nosec B603 B607
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        dirty: bool | None = bool(state)
        state_sha256: str | None = hashlib.sha256(state.encode("utf-8")).hexdigest()
    except (OSError, subprocess.SubprocessError):
        commit, dirty, state_sha256 = None, None, None
    return {
        "git_commit": commit,
        "git_dirty": dirty,
        "git_status_sha256": state_sha256,
        "evaluator_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }


@dataclass(frozen=True)
class ChallengeCase:
    case_id: str
    split: str
    family: str
    prompt: str
    expected_status: str
    expected: dict[str, Any] | None


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_challenge(path: Path) -> list[ChallengeCase]:
    """Load and validate immutable JSONL cases without repairing bad records."""

    path = Path(path)
    if not path.is_file():
        raise ValueError(f"challenge dataset does not exist: {path}")
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("challenge dataset is limited to 4 MiB")
    cases: list[ChallengeCase] = []
    allowed = {"case_id", "split", "family", "prompt", "expected_status", "expected"}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank challenge record at line {line_number}")
        try:
            raw = json.loads(line, object_pairs_hook=_strict_object, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"invalid challenge JSON at line {line_number}: {exc}") from exc
        if not isinstance(raw, dict) or set(raw) != allowed:
            raise ValueError(f"challenge record {line_number} must contain exactly {sorted(allowed)}")
        if any(not isinstance(raw[name], str) or not raw[name].strip() for name in ("case_id", "split", "family", "prompt")):
            raise ValueError(f"challenge record {line_number} has an empty identifier, split, family, or prompt")
        if raw["split"] not in ALLOWED_SPLITS:
            raise ValueError(f"challenge record {line_number} has unsupported split {raw['split']!r}")
        if raw["expected_status"] not in {"accept", "reject"}:
            raise ValueError(f"challenge record {line_number} expected_status must be accept or reject")
        expected = raw["expected"]
        if raw["expected_status"] == "accept" and (not isinstance(expected, dict) or not expected):
            raise ValueError(f"accepted challenge record {line_number} requires a semantic signature")
        if raw["expected_status"] == "reject" and expected is not None:
            raise ValueError(f"rejected challenge record {line_number} must use null expected")
        cases.append(ChallengeCase(**raw))
    if not cases:
        raise ValueError("challenge dataset must not be empty")
    ids = [case.case_id for case in cases]
    prompts = [" ".join(case.prompt.casefold().split()) for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("challenge case IDs must be unique")
    if len(prompts) != len(set(prompts)):
        raise ValueError("normalized challenge prompts must be unique")
    if {case.split for case in cases} != ALLOWED_SPLITS:
        raise ValueError("challenge dataset must contain development, validation, and test cases")
    return cases


def run_challenge(cases: list[ChallengeCase], *, dataset_sha256: str) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for case in cases:
        try:
            document = TextToCAD().build(case.prompt)
            accepted = document.validation.valid
            actual = program_signature(document.require_program()) if accepted else None
            errors = list(document.validation.errors)
        except (KeyError, TypeError, ValueError) as exc:
            accepted = False
            actual = None
            errors = [str(exc)]
        passed = (
            (not accepted)
            if case.expected_status == "reject"
            else accepted and semantic_signatures_equal(case.expected, actual)
        )
        records.append(
            {
                "case_id": case.case_id,
                "split": case.split,
                "family": case.family,
                "prompt": case.prompt,
                "expected_status": case.expected_status,
                "expected": case.expected,
                "accepted": accepted,
                "actual": actual,
                "errors": errors,
                "passed": passed,
            }
        )
    by_split = {}
    for split in sorted(ALLOWED_SPLITS):
        subset = [record for record in records if record["split"] == split]
        by_split[split] = {"cases": len(subset), "passed": sum(record["passed"] for record in subset)}
    return {
        "challenge_version": CHALLENGE_VERSION,
        "evidence_class": "development evidence; audit-authored after implementation inspection; not independent or confirmatory",
        "dataset_sha256": dataset_sha256,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": _execution_provenance(),
        "cases": len(records),
        "passed": sum(record["passed"] for record in records),
        "by_split": by_split,
        "records": records,
        "failures": [record for record in records if not record["passed"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate a frozen NeuroCAD prompt challenge JSONL")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    dataset = args.dataset.resolve()
    output = args.output.resolve()
    if dataset == output:
        parser.error("dataset and output paths must differ")
    if output.exists():
        parser.error(f"output already exists: {output}")
    payload = dataset.read_bytes()
    results = run_challenge(load_challenge(dataset), dataset_sha256=hashlib.sha256(payload).hexdigest())
    write_text_atomic(output, json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"cases": results["cases"], "passed": results["passed"], "output": str(output)}, sort_keys=True))
    return 0 if results["passed"] == results["cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
