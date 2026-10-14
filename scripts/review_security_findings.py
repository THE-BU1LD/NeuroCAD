"""Apply exact, source-bound reviews to retained Bandit findings.

Never skip scanning a file or a rule. Any new finding, source drift, severity
change, missing scan result or stale review fails the gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def adjudicate(report, review, root):
    errors = []
    if report.get("errors"):
        errors.append("Bandit reported files it could not scan")
    if not isinstance(report.get("results"), list) or not report.get("metrics"):
        return {"status": "FAIL", "errors": errors + ["missing full scanner results/metrics"]}
    allowed = {}
    for item in review["findings"]:
        key = (item["path"], item["test_id"], item["line"])
        if key in allowed:
            errors.append("duplicate review")
        source = (root / item["path"]).resolve()
        if not source.is_relative_to(root.resolve()) or not source.is_file():
            errors.append("review path is missing or outside the repository")
            continue
        if hashlib.sha256(source.read_bytes()).hexdigest() != item["source_sha256"]:
            errors.append(f"review source changed: {item['path']}")
        allowed[key] = item
    observed = set()
    for item in report["results"]:
        path = Path(item["filename"]).resolve()
        if not path.is_relative_to(root.resolve()):
            errors.append("scanner path escapes repository")
            continue
        key = (str(path.relative_to(root.resolve())), item["test_id"], item["line_number"])
        approved = allowed.get(key)
        if key in observed:
            errors.append("duplicate scanner finding")
        observed.add(key)
        if approved is None or item["issue_severity"] != "LOW" or item["issue_confidence"] != "HIGH":
            errors.append(f"unreviewed finding: {key}")
    if observed != set(allowed):
        errors.append("scanner findings differ from the exact reviewed set")
    return {"status": "FAIL" if errors else "PASS", "reviewed_findings": len(observed), "errors": errors,
            "scope": "Exact reviewed informational findings only; all source remains scanned."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    review = json.loads((root / "docs/security/FROZEN_HARNESS_REVIEW.json").read_text(encoding="utf-8"))
    result = adjudicate(json.loads(args.report.read_text(encoding="utf-8")), review, root)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
