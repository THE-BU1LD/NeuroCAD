"""Audit the evidence behind the v3 completion checklist without running models."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

MAX_JSON_BYTES = 8 * 1024 * 1024


def read_json(path, expected_sha256=None):
    """Standalone strict reader; do not import the eager application package."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("Evidence JSON exceeds the 8 MiB limit")
    if expected_sha256 is not None and hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Evidence hash mismatch")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"Nonfinite JSON number: {value}")

    def finite(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("JSON number exceeds finite range")
        return result

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=constant, parse_float=finite)
    except RecursionError as exc:
        raise ValueError("JSON exceeds supported nesting") from exc


def same_json(actual, expected):
    """Python equates True with 1 even inside containers; evidence must not."""
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(same_json(actual[k], expected[k]) for k in actual)
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(same_json(a, b) for a, b in zip(actual, expected))
    return actual == expected


def validate_manifest(manifest):
    """Validate containers before evaluating paths, hashes and assertions."""
    if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int:
        raise ValueError("Manifest must be an object with an integer schema_version")
    source = manifest.get("verified_source")
    if not isinstance(source, dict) or not isinstance(source.get("files"), dict):
        raise TypeError("verified_source and its files inventory must be objects")
    if not isinstance(source.get("commit"), str):
        raise TypeError("Source commit must be a string")
    for name, digest in source["files"].items():
        if not isinstance(name, str) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Source inventory requires path/SHA-256 pairs")
    globs = source.get("production_globs", [])
    if not isinstance(globs, list) or any(not isinstance(g, str) or not g or Path(g).is_absolute() or ".." in Path(g).parts for g in globs):
        raise ValueError("Production globs must be relative nonescaping strings")
    items = manifest.get("items")
    if not isinstance(items, list):
        raise TypeError("Checklist items must be an array")
    for item in items:
        if not isinstance(item, dict):
            raise TypeError("Checklist item must be an object")
        for key in ("id", "state", "title", "acceptance"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f"Checklist item needs a nonempty {key}")
        if item["state"] != "DONE":
            for key in ("reason", "next_action"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    raise ValueError(f"Open item needs a nonempty {key}")
        evidence = item.get("evidence", [])
        if not isinstance(evidence, list):
            raise TypeError("Evidence must be an array")
        for record in evidence:
            if not isinstance(record, dict) or not isinstance(record.get("path"), str) or not isinstance(record.get("sha256"), str):
                raise TypeError("Evidence record requires a path and SHA-256")
            assertions = record.get("assertions", [])
            if not isinstance(assertions, list):
                raise TypeError("Assertions must be an array")
            for assertion in assertions:
                if not isinstance(assertion, dict) or not isinstance(assertion.get("pointer"), str) or "equals" not in assertion:
                    raise ValueError("Assertion requires pointer and equals")
    # Also reject nonfinite or non-JSON values passed through the Python API.
    json.dumps(manifest, allow_nan=False)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


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
        if re.search(r"~(?![01])", part):
            raise ValueError("Invalid JSON pointer escape")
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", part):
                raise ValueError("JSON array pointer requires a canonical non-negative index")
            value = value[int(part)]
        elif isinstance(value, dict):
            value = value[part]
        else:
            raise TypeError("JSON pointer cannot traverse a scalar")
    return value


def audit(root, manifest):
    try:
        validate_manifest(manifest)
    except (ValueError, TypeError, RecursionError) as exc:
        return {"schema_version": 1, "audit_status": "FAIL", "complete": False,
                "current_source_matches_verified_inventory": False, "source_drift": [],
                "verified_source_commit": None, "counts": {}, "items": [], "errors": [str(exc)]}
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
                if not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
                    raise ValueError("Evidence hash must be lowercase SHA-256")
                assertions = record.get("assertions", [])
                if not assertions:
                    raise ValueError("Evidence needs semantic assertions, not just file presence")
                data = read_json(path, record["sha256"])
                for assertion in assertions:
                    actual = at_pointer(data, assertion["pointer"])
                    if not same_json(actual, assertion["equals"]):
                        raise ValueError(f"Assertion failed: {assertion['pointer']}")
            except (KeyError, IndexError, TypeError, ValueError, OSError, RecursionError) as exc:
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
        manifest = read_json(inside(args.root, args.manifest))
        result = audit(args.root, manifest)
        text = markdown(manifest, result) if args.markdown and result["audit_status"] == "PASS" else json.dumps(result, indent=2) + "\n"
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
