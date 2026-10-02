"""Frozen-input language evaluation with separate semantic and rejection endpoints."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Protocol

from .conversational_parser import EditProposal, context_hash, parse_conversation
from .json_io import read_bounded_utf8, strict_json_loads
from .language_provider import ChatLanguageProvider
from .project import EnclosureProject, enclosure_spec_to_dict, parse_project, serialize_project

VERSION = "neurocad-language-challenge-v1"
STATUSES = {"proposal", "clarification", "unsupported", "rejected", "unchanged"}
MAX_DATASET_BYTES = 4_194_304


class Interpreter(Protocol):
    def interpret(self, source: str, project: EnclosureProject, *, recent_messages: list[str]) -> EditProposal: ...


def validate_challenge(raw: Any) -> dict[str, Any]:
    """Validate all labels before any inference or output-directory creation."""
    keys = {"version", "provenance", "projects", "cases"}
    if not isinstance(raw, dict) or set(raw) != keys or raw["version"] != VERSION:
        raise ValueError("Challenge requires version, provenance, projects and cases")
    provenance = raw["provenance"]
    if (not isinstance(provenance, dict) or set(provenance) != {"kind", "description"}
            or not isinstance(provenance["kind"], str)
            or provenance["kind"] not in {"constructed-development", "external-annotated"}
            or not isinstance(provenance["description"], str) or not 1 <= len(provenance["description"]) <= 2048):
        raise ValueError("Declare constructed-development or external-annotated provenance and its description")
    projects = raw["projects"]
    if not isinstance(projects, dict) or not 1 <= len(projects) <= 100:
        raise ValueError("Challenge requires 1 through 100 embedded projects")
    parsed = {}
    for key, value in projects.items():
        if not isinstance(key, str) or not 1 <= len(key) <= 128:
            raise ValueError("Project label must contain 1 through 128 characters")
        parsed[key] = parse_project(json.dumps(value, allow_nan=False))
    cases = raw["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 1000:
        raise ValueError("Challenge requires 1 through 1000 cases")
    identifiers = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"id", "category", "project", "source", "history", "expected"}:
            raise ValueError("Case requires id, category, project, source, history and expected")
        for field, maximum in (("id", 128), ("category", 128), ("source", 8192)):
            if not isinstance(case[field], str) or not case[field].strip() or len(case[field]) > maximum:
                raise ValueError(f"Invalid case {field}")
        if case["id"] in identifiers:
            raise ValueError("Case IDs must be unique")
        identifiers.add(case["id"])
        if not isinstance(case["project"], str) or case["project"] not in parsed:
            raise ValueError("Case project must name an embedded project")
        history = case["history"]
        if (not isinstance(history, list) or len(history) > 10
                or any(not isinstance(item, str) or len(item) > 2048 for item in history)):
            raise ValueError("History requires at most 10 strings of at most 2048 characters")
        expected = case["expected"]
        if (not isinstance(expected, dict) or set(expected) != {"status", "spec", "preserve"}
                or not isinstance(expected["status"], str) or expected["status"] not in STATUSES):
            raise ValueError("Expected requires status, complete spec or null, and preserve")
        baseline = enclosure_spec_to_dict(parsed[case["project"]].spec)
        protections = expected["preserve"]
        allowed = set(baseline) - {"version", "units"}
        allowed |= {f"lid.{key}" for key in baseline["lid"]}
        allowed |= {f"cutout:{item['id']}" for item in baseline["cutouts"]}
        if (not isinstance(protections, list) or len(protections) > 32
                or any(not isinstance(field, str) or field not in allowed for field in protections)
                or len(set(protections)) != len(protections)):
            raise ValueError("Expected preservation fields must be unique supported fields")
        if expected["status"] == "proposal":
            if not isinstance(expected["spec"], dict):
                raise ValueError("Successful intent requires the complete expected specification")
            expected_project = parsed[case["project"]].to_dict()
            expected_project.update(spec=expected["spec"], revision=1, changes=[], phrase_mappings=[], source_text=None)
            checked = parse_project(json.dumps(expected_project, allow_nan=False))
            expected["spec"] = enclosure_spec_to_dict(checked.spec)
        elif expected["spec"] is not None:
            raise ValueError("Non-proposal intent must have spec=null")
    return raw


def score_proposal(proposal: EditProposal, expected: dict[str, Any], project: EnclosureProject) -> dict[str, bool]:
    candidate = enclosure_spec_to_dict(proposal.candidate.spec) if proposal.candidate else None
    resolved = proposal.status == "proposal" and candidate is not None
    valid_intent = expected["status"] == "proposal"
    actual_protections = {item["field"] for item in proposal.preserve}
    protection_match = all(field in actual_protections
                           or (field.startswith("cutout:") and "cutouts" in actual_protections)
                           or (field.startswith("lid.") and "lid" in actual_protections)
                           for field in expected["preserve"])
    context_match = proposal.baseline_sha256 == context_hash(project)
    semantic_exact = valid_intent and resolved and candidate == expected["spec"] and protection_match and context_match
    # A transport error is scored separately, never counted as successful rejection.
    fail_closed = not valid_intent and proposal.candidate is None and proposal.status != "proposal" and context_match
    status_exact = proposal.status == expected["status"]
    return {"semantic_exact": semantic_exact, "fail_closed": fail_closed,
            "unsafe_acceptance": not valid_intent and (proposal.candidate is not None or proposal.status == "proposal"),
            "wrong_candidate": valid_intent and resolved and not semantic_exact,
            "status_exact": status_exact, "protection_match": protection_match,
            "passed": (semantic_exact if valid_intent else fail_closed and status_exact)}


def evaluate(challenge_path: Path, output_dir: Path, *, provider: Interpreter | None = None,
             provider_label: str = "local", live_provider: bool = False) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError("Evaluation output must be a new directory")
    if live_provider and provider is None:
        raise ValueError("Live evaluation requires an explicit provider")
    source = read_bounded_utf8(challenge_path, max_bytes=MAX_DATASET_BYTES, label="language challenge")
    challenge = validate_challenge(strict_json_loads(source))
    frozen_hash = hashlib.sha256(source.encode()).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=False)
    # Preserve the exact frozen input, including labels, before observing outcomes.
    (output_dir / "challenge.json").write_text(source, encoding="utf-8")
    receipt = {"version": "neurocad-language-run-v1", "dataset_sha256": frozen_hash,
               "provenance": challenge["provenance"], "provider": provider_label,
               "live_provider_evaluated": live_provider,
               "scorer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "parser_sha256": hashlib.sha256(Path(__file__).with_name("conversational_parser.py").read_bytes()).hexdigest(),
               "provider_adapter_sha256": hashlib.sha256(Path(__file__).with_name("language_provider.py").read_bytes()).hexdigest(),
               "outcomes_observed": False, "case_count": len(challenge["cases"])}
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    results = []
    for index, case in enumerate(challenge["cases"]):
        project = parse_project(json.dumps(challenge["projects"][case["project"]], allow_nan=False))
        before = serialize_project(project)
        started = time.monotonic()
        result: dict[str, Any] = {"id": case["id"], "category": case["category"], "expected": case["expected"],
                                  "history_used": provider is not None, "provider_error": False}
        try:
            # Labels never enter the provider context. No retries or prompt rewriting.
            proposal = (provider.interpret(case["source"], project, recent_messages=case["history"])
                        if provider is not None else parse_conversation(case["source"], project))
            result.update(observed=proposal.to_dict(), **score_proposal(proposal, case["expected"], project))
        except (ValueError, OSError) as exc:
            # Exception type only: endpoint errors can contain credentials or response bodies.
            result.update(observed=None, error_type=type(exc).__name__, provider_error=True,
                          passed=False, semantic_exact=False, fail_closed=False, unsafe_acceptance=False,
                          wrong_candidate=False, status_exact=False, protection_match=False)
        result["baseline_unchanged"] = serialize_project(project) == before
        result["passed"] = result["passed"] and result["baseline_unchanged"]
        result["elapsed_seconds"] = time.monotonic() - started
        results.append(result)
        # Flush each outcome so an interrupted run retains completed failures and receipts.
        with (output_dir / "results.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
    valid = sum(case["expected"]["status"] == "proposal" for case in challenge["cases"])
    rejection = len(results) - valid
    exact = sum(result["semantic_exact"] for result in results)
    closed = sum(result["fail_closed"] for result in results)
    summary = {**receipt, "outcomes_observed": True, "completed_cases": len(results),
               "passed_count": sum(result["passed"] for result in results),
               "valid_intent_cases": valid, "semantic_exact_count": exact,
               "semantic_exact_rate": exact / valid if valid else None,
               "rejection_intent_cases": rejection, "fail_closed_count": closed,
               "fail_closed_rate": closed / rejection if rejection else None,
               "unsafe_acceptance_count": sum(result["unsafe_acceptance"] for result in results),
               "wrong_candidate_count": sum(result["wrong_candidate"] for result in results),
               "provider_error_count": sum(result["provider_error"] for result in results),
               "status_exact_count": sum(result["status_exact"] for result in results),
               "baseline_unchanged": all(result["baseline_unchanged"] for result in results),
               "distinct_sources": len({case["source"] for case in challenge["cases"]}),
               "independent_authorship_verified": False,
               "claim_boundary": "Development diagnostics; external provenance declarations alone do not establish independent or confirmatory evaluation"}
    summary["categories"] = {
        category: {"cases": sum(result["category"] == category for result in results),
                   "passed": sum(result["category"] == category and result["passed"] for result in results),
                   "unsafe_acceptances": sum(result["category"] == category and result["unsafe_acceptance"] for result in results)}
        for category in sorted({case["category"] for case in challenge["cases"]})
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("challenge", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--provider-url")
    parser.add_argument("--model")
    parser.add_argument("--timeout-seconds", type=float, default=30)
    args = parser.parse_args(argv)
    if bool(args.provider_url) != bool(args.model):
        parser.error("--provider-url and --model must be supplied together")
    try:
        provider = (ChatLanguageProvider(endpoint=args.provider_url, model=args.model,
                                        api_key=os.environ.get("NEUROCAD_LANGUAGE_API_KEY", ""),
                                        timeout_seconds=args.timeout_seconds) if args.provider_url else None)
        summary = evaluate(args.challenge, args.output_dir, provider=provider,
                           provider_label=f"chat-completions:{args.model}" if provider else "local", live_provider=provider is not None)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Language evaluation failed ({type(exc).__name__}); no successful result claimed\n")
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["passed_count"] == summary["completed_cases"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
