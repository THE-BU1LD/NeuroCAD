"""Freeze and audit externally collected evidence; never certify its authenticity.

Standard-library only. Does not execute models or contact participants.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

KINDS = {"physical", "reproduction", "usability"}
REQUIRED_ROLES = {
    "physical": {"raw_measurements", "calibration", "apparatus", "prediction", "uncertainty", "input_measurements"},
    "reproduction": {"environment", "installation", "commands", "raw_results", "discrepancies", "independence"},
    "usability": {"session_records", "consent_receipt", "task_outputs", "issues"},
}


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def number(value, *, positive=False):
    return (
        not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and (value > 0 if positive else value >= 0)
    )


def timestamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return result


def artifact(root, item):
    if not isinstance(item, dict):
        raise TypeError("artifact must contain path and sha256")
    relative = Path(item["path"])
    path = (root / relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError("artifact escapes evidence directory")
    if not path.is_file() or digest(path) != item["sha256"]:
        raise ValueError(f"missing or changed artifact: {relative}")
    return path


def validate_plan(plan):
    errors = []
    for field in (
        "study_id",
        "kind",
        "capability",
        "applicability_envelope",
        "exclusions",
        "release_sha256",
        "source_commit",
        "operator_id",
        "reference_provenance",
        "stop_rule",
    ):
        if not plan.get(field):
            errors.append(f"missing {field}")
    if plan.get("kind") not in KINDS:
        errors.append("unsupported kind")
    for field, length in (("source_commit", 40), ("release_sha256", 64)):
        value = plan.get(field, "")
        if not isinstance(value, str) or len(value) != length or any(c not in "0123456789abcdef" for c in value):
            errors.append(f"invalid {field}")
    if plan.get("outcomes_observed") is not False:
        errors.append("outcomes_observed must be false at freeze")
    cases = plan.get("cases", [])
    if not cases or not all(isinstance(c, dict) for c in cases):
        return errors + ["nonempty case list required"]
    ids = [c.get("id") for c in cases]
    if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        errors.append("case IDs must be unique nonempty strings")
    for case in cases:
        if not case.get("procedure") or not case.get("required_artifacts"):
            errors.append(f"{case.get('id')}: procedure and artifact roles required")
        if not REQUIRED_ROLES.get(plan.get("kind"), set()).issubset(set(case.get("required_artifacts", []))):
            errors.append(f"{case.get('id')}: required evidence roles omitted")
        if plan.get("kind") == "physical":
            for field in ("units", "apparatus", "calibration_plan", "uncertainty_budget", "input_measurement_plan"):
                if not case.get(field):
                    errors.append(f"{case.get('id')}: missing {field}")
            for field in ("atol", "rtol", "max_expanded_uncertainty"):
                if not number(case.get(field)):
                    errors.append(f"{case.get('id')}: nonnegative finite {field} required")
            if not number(case.get("coverage_factor"), positive=True):
                errors.append(f"{case.get('id')}: positive coverage_factor required")
    if plan.get("kind") in {"reproduction", "usability"} and (
        not plan.get("implementer_ids") or plan.get("operator_id") in plan.get("implementer_ids", [])
    ):
        errors.append("external operator and implementer identities required and must differ")
    if plan.get("kind") == "usability":
        if (
            not isinstance(plan.get("minimum_participants"), int)
            or isinstance(plan.get("minimum_participants"), bool)
            or plan["minimum_participants"] < 5
        ):
            errors.append("minimum_participants must be at least five")
        if not plan.get("recruitment_criteria") or not plan.get("consent_and_privacy"):
            errors.append("recruitment and consent/privacy plan required")
    return errors


def freeze(plan_path, output):
    plan = read(plan_path)
    errors = validate_plan(plan)
    if errors:
        raise ValueError("; ".join(errors))
    inputs = plan.get("frozen_artifacts", [])
    if not inputs:
        raise ValueError("hash-bound protocol, procedures and reference artifacts required")
    for item in inputs:
        artifact(plan_path.parent, item)
    receipt = {
        "schema_version": 1,
        "status": "FROZEN_PREOUTCOME_DECLARATION",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": digest(plan_path),
        "plan": plan,
        "canonical_plan_sha256": canonical_digest(plan),
        "auditor_sha256": digest(Path(__file__)),
        "boundary": "Author declaration and content hashes; not independent timestamp or external evidence.",
    }
    write_new(output, receipt)
    return receipt


def audit(freeze_path, evidence_path):
    frozen, evidence = read(freeze_path), read(evidence_path)
    plan = frozen["plan"]
    errors = validate_plan(plan)
    comparisons = []
    root = evidence_path.parent
    if frozen.get("canonical_plan_sha256") != canonical_digest(plan):
        errors.append("embedded plan changed after freeze")
    if frozen.get("auditor_sha256") != digest(Path(__file__)):
        errors.append("auditor changed after freeze; use the frozen version")
    if frozen.get("status") != "FROZEN_PREOUTCOME_DECLARATION":
        errors.append("invalid freeze status")
    if evidence.get("freeze_sha256") != digest(freeze_path):
        errors.append("evidence does not bind this freeze")
    if evidence.get("study_id") != plan.get("study_id"):
        errors.append("study identity mismatch")
    if evidence.get("operator_id") != plan.get("operator_id"):
        errors.append("operator identity mismatch")
    if evidence.get("synthetic") is not False:
        errors.append("real externally collected evidence must explicitly declare synthetic=false")
    try:
        if timestamp(evidence["started_at"]) <= timestamp(frozen["frozen_at"]):
            errors.append("collection must start after freeze")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"invalid collection timestamp: {exc}")
    for item in plan.get("frozen_artifacts", []):
        try:
            artifact(root, item)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(str(exc))
    rows = evidence.get("cases", [])
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        return {"status": "INCOMPLETE_OR_INVALID", "errors": errors + ["invalid case records"], "comparisons": []}
    ids = [r.get("id") for r in rows]
    expected = {c["id"] for c in plan["cases"]}
    if len(ids) != len(set(ids)) or set(ids) != expected:
        errors.append("every frozen case must appear exactly once, including failures")
    by_id = {r.get("id"): r for r in rows}
    for case in plan["cases"]:
        row = by_id.get(case["id"], {})
        for role in case.get("required_artifacts", []):
            try:
                artifact(root, row.get("artifacts", {})[role])
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(f"{case['id']}/{role}: {exc}")
        if row.get("status") not in {"PASS", "FAIL", "BLOCKED"}:
            errors.append(f"{case['id']}: missing retained outcome")
        if row.get("status") != "PASS":
            comparisons.append({"id": case["id"], "status": row.get("status", "MISSING")})
            continue
        if plan["kind"] == "physical":
            predicted, measured = row.get("predicted"), row.get("measured")
            valid_values = all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (predicted, measured))
            uncertainty = row.get("expanded_uncertainty")
            if not valid_values or not number(uncertainty):
                errors.append(f"{case['id']}: finite measurements and uncertainty required")
                continue
            if row.get("units") != case["units"] or row.get("coverage_factor") != case["coverage_factor"]:
                errors.append(f"{case['id']}: units or coverage factor mismatch")
            delta = abs(predicted - measured)
            tolerance = case["atol"] + case["rtol"] * abs(measured)
            passes = delta <= tolerance and uncertainty <= case["max_expanded_uncertainty"]
            comparisons.append(
                {
                    "id": case["id"],
                    "absolute_error": delta,
                    "tolerance": tolerance,
                    "expanded_uncertainty": uncertainty,
                    "status": "PASS" if passes else "FAIL",
                }
            )
        elif plan["kind"] == "reproduction":
            for flag in ("clean_install", "outside_source_tree", "no_implementation_contribution", "all_frozen_cases_attempted"):
                if row.get(flag) is not True:
                    errors.append(f"{case['id']}: {flag} not attested")
            comparisons.append({"id": case["id"], "status": "PASS"})
        else:
            people = row.get("participants", [])
            pids = [p.get("id") for p in people]
            if len(people) < plan["minimum_participants"] or len(set(pids)) != len(pids) or not all(pids):
                errors.append(f"{case['id']}: missing or duplicate participants")
            for person in people:
                if person.get("consented") is not True or person.get("eligible") is not True:
                    errors.append(f"{case['id']}: eligibility/consent missing")
                if person.get("id") in plan.get("implementer_ids", []):
                    errors.append(f"{case['id']}: implementer used as intended user")
                for flag in ("completed_without_help", "correct_loads_and_materials", "understands_limits", "distinguishes_screening"):
                    if not isinstance(person.get(flag), bool):
                        errors.append(f"{case['id']}: missing {flag}")
            passes = bool(people) and all(
                all(
                    p.get(f) is True
                    for f in ("completed_without_help", "correct_loads_and_materials", "understands_limits", "distinguishes_screening")
                )
                for p in people
            )
            comparisons.append({"id": case["id"], "status": "PASS" if passes else "FAIL"})
    all_pass = bool(comparisons) and all(c["status"] == "PASS" for c in comparisons)
    return {
        "schema_version": 1,
        "status": "INCOMPLETE_OR_INVALID" if errors else "EVIDENCE_COMPLETE_REVIEW_REQUIRED",
        "all_case_criteria_pass": all_pass and not errors,
        "errors": errors,
        "comparisons": comparisons,
        "scientific_gate_advanced": False,
        "boundary": "Structural and numerical audit only. Human review must establish authenticity, independence, calibration and applicability.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("plan", type=Path)
    f.add_argument("output", type=Path)
    a = sub.add_parser("audit")
    a.add_argument("freeze", type=Path)
    a.add_argument("evidence", type=Path)
    a.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "freeze":
            result = freeze(args.plan, args.output)
        else:
            result = audit(args.freeze, args.evidence)
            write_new(args.output, result)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0 if result.get("status") != "INCOMPLETE_OR_INVALID" else 1
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"status": "REFUSED", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
