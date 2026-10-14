"""Audit the evidence behind the v3 completion checklist without running models."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("Evidence path must be relative")
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Evidence path escapes repository")
    return path


def at_pointer(value, pointer):
    if pointer == "":
        return value
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("Expected a JSON pointer")
    for part in pointer[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def audit(root, manifest):
    errors, rows = [], []
    if manifest.get("schema_version") != 1:
        errors.append("Unsupported readiness schema")
    source = manifest.get("verified_source", {})
    if not re.fullmatch(r"[0-9a-f]{40}", source.get("commit", "")):
        errors.append("Verified source requires an exact commit")
    source_matches = True
    source_errors = []
    if not source.get("files"):
        errors.append("Verified source inventory is empty")
        source_matches = False
    for name, expected in source.get("files", {}).items():
        try:
            if sha256(inside(root, name)) != expected:
                source_matches = False
                source_errors.append(name)
        except (OSError, TypeError, ValueError) as exc:
            source_matches = False
            source_errors.append(f"{name}: {exc}")
    if source.get("production_globs"):
        observed = {path.relative_to(root).as_posix() for pattern in source["production_globs"]
                    for path in root.glob(pattern) if path.is_file()}
        expected = set(source.get("files", {}))
        if observed != expected:
            source_matches = False
            source_errors.append({"added": sorted(observed - expected), "removed": sorted(expected - observed)})
    seen = set()
    items = manifest.get("items", [])
    if not items:
        errors.append("Checklist must not be empty")
    for item in items:
        name = item.get("id")
        failures = []
        if not isinstance(name, str) or not name or name in seen:
            failures.append("Missing or duplicate item ID")
        seen.add(str(name))
        state = item.get("state")
        if state not in {"DONE", "BLOCKED", "IN_PROGRESS", "TODO"}:
            failures.append("Unknown item state")
        if not item.get("acceptance") or not item.get("title"):
            failures.append("Missing title or acceptance criterion")
        if state != "DONE" and (not item.get("reason") or not item.get("next_action")):
            failures.append("Open item needs a reason and concrete next action")
        evidence = item.get("evidence", [])
        if state == "DONE" and not evidence:
            failures.append("DONE requires retained evidence")
        for record in evidence:
            try:
                path = inside(root, record["path"])
                if not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) or sha256(path) != record["sha256"]:
                    raise ValueError("Evidence hash mismatch")
                assertions = record.get("assertions", [])
                if not assertions:
                    raise ValueError("Evidence needs semantic assertions, not just file presence")
                data = json.loads(path.read_text(encoding="utf-8"))
                for assertion in assertions:
                    actual = at_pointer(data, assertion["pointer"])
                    if type(actual) is not type(assertion["equals"]) or actual != assertion["equals"]:
                        raise ValueError(f"Assertion failed: {assertion['pointer']}")
            except (KeyError, IndexError, TypeError, ValueError, OSError) as exc:
                failures.append(f"{record.get('path')}: {exc}")
        rows.append({"id": name, "title": item.get("title"), "state": state,
                     "evidence_valid": not failures, "errors": failures})
        errors.extend(f"{name}: {failure}" for failure in failures)
    return {
        "schema_version": 1,
        "audit_status": "PASS" if not errors else "FAIL",
        "verified_source_commit": source.get("commit"),
        "current_source_matches_verified_inventory": source_matches,
        "source_drift": source_errors,
        "complete": bool(rows) and not errors and source_matches and all(r["state"] == "DONE" for r in rows),
        "counts": {state: sum(r["state"] == state for r in rows) for state in ("DONE", "BLOCKED", "IN_PROGRESS", "TODO")},
        "items": rows, "errors": errors,
        "boundary": "Evidence consistency only; not physical validation, independence, authenticity or certification",
    }


def markdown(manifest, result):
    lines = ["# Advanced engineering completion checklist", "",
             f"Evidence audit: **{result['audit_status']}**. Overall completion: **{result['complete']}**.",
             (f"Verified source: `{result['verified_source_commit']}`. Current source matches: "
             f"**{result['current_source_matches_verified_inventory']}**."), "",
             ("Completed means the stated bounded acceptance criterion has retained evidence. "
             "Blocked and concurrent work remain open; software results do not close external gates."), ""]
    for item, row in zip(manifest["items"], result["items"], strict=True):
        mark = "x" if item["state"] == "DONE" and row["evidence_valid"] else " "
        lines.extend([f"- [{mark}] **{item['id']} — {item['title']}** ({item['state']})",
                      f"  Acceptance: {item['acceptance']}"])
        if item["state"] != "DONE":
            lines.extend([f"  Blocker/current state: {item['reason']}", f"  Next action: {item['next_action']}"])
        for record in item.get("evidence", []):
            lines.append(f"  Evidence: `{record['path']}` (SHA-256 `{record['sha256']}`).")
        lines.append("")
    lines += [("Run `python3 scripts/audit_v3_readiness.py` to check the machine-readable inventory. "
              "Use `--require-complete` for a gate that refuses open work or source drift."), "",
              ("Scope: the advanced engineering readiness request. The 109 earlier expansion proposals "
              "remain a separate product backlog; implementing FEA/CFD or inventing external study results "
              "is not implied by this checklist."), ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", default="docs/V3_READINESS_CHECKLIST.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    try:
        manifest = json.loads(inside(args.root, args.manifest).read_text(encoding="utf-8"))
        result = audit(args.root, manifest)
        text = markdown(manifest, result) if args.markdown else json.dumps(result, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(text)
        else:
            print(text, end="")
        return 1 if result["audit_status"] != "PASS" else 3 if args.require_complete and not result["complete"] else 0
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"audit_status": "FAIL", "error": str(exc), "complete": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
