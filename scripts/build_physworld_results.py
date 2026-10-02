"""Compile artifact-backed Physical World AI case receipts into paper-ready results.

This tool intentionally fails closed. A result cell cannot be emitted as PASS/FAIL
unless the receipt says the dimension is applicable and points to retained evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

DIMENSIONS = ("visual_plausibility", "geometry_validity", "revision_integrity", "meshability")
TERMINAL = {"pass", "fail"}
VALID = TERMINAL | {"not_run", "na"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_dimension(case_id: str, name: str, value: Any, *, strict: bool) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{case_id}: {name} must be an object")
    applicable = value.get("applicable")
    status = value.get("status")
    evidence = value.get("evidence", [])
    if not isinstance(applicable, bool):
        raise ValueError(f"{case_id}: {name}.applicable must be boolean")
    if status not in VALID:
        raise ValueError(f"{case_id}: {name}.status must be one of {sorted(VALID)}")
    if not isinstance(evidence, list) or not all(isinstance(x, str) and x.strip() for x in evidence):
        raise ValueError(f"{case_id}: {name}.evidence must be a list of non-empty strings")
    if not applicable:
        if status != "na":
            raise ValueError(f"{case_id}: non-applicable {name} must use status=na")
        if evidence:
            raise ValueError(f"{case_id}: non-applicable {name} must not carry outcome evidence")
    else:
        if status in TERMINAL and not evidence:
            raise ValueError(f"{case_id}: {name} {status} requires retained evidence")
        if strict and status not in TERMINAL:
            raise ValueError(f"{case_id}: strict mode requires terminal result for applicable {name}")
    return {"applicable": applicable, "status": status, "evidence": evidence}


def validate_receipt(path: Path, *, strict: bool) -> dict[str, Any]:
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: receipt must be an object")
    for key in ("schema_version", "case_id", "title", "source_identity", "baseline_sha256", "provenance"):
        if key not in data:
            raise ValueError(f"{path}: missing required key {key}")
    if data["schema_version"] != "physworld-evidence-v1":
        raise ValueError(f"{path}: unsupported schema_version")
    case_id = data["case_id"]
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError(f"{path}: case_id must be non-empty")
    digest = data["baseline_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
        raise ValueError(f"{case_id}: baseline_sha256 must be a 64-character hex digest")
    provenance = data["provenance"]
    if not isinstance(provenance, dict):
        raise ValueError(f"{case_id}: provenance must be an object")
    for key in ("tool_versions", "commands", "units"):
        if key not in provenance:
            raise ValueError(f"{case_id}: provenance missing {key}")
    if not isinstance(provenance["tool_versions"], dict) or not provenance["tool_versions"]:
        raise ValueError(f"{case_id}: tool_versions must be non-empty")
    if not isinstance(provenance["commands"], list):
        raise ValueError(f"{case_id}: commands must be a list")
    if not isinstance(provenance["units"], str) or not provenance["units"].strip():
        raise ValueError(f"{case_id}: units must be non-empty")

    dimensions = {name: validate_dimension(case_id, name, data.get(name), strict=strict)
                  for name in DIMENSIONS}

    derived = data.get("derived_artifacts", [])
    if not isinstance(derived, list):
        raise ValueError(f"{case_id}: derived_artifacts must be a list")
    for index, item in enumerate(derived):
        if not isinstance(item, dict):
            raise ValueError(f"{case_id}: derived_artifacts[{index}] must be an object")
        if not item.get("path") or not item.get("sha256"):
            raise ValueError(f"{case_id}: derived_artifacts[{index}] requires path and sha256")
        digest = item["sha256"]
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"{case_id}: invalid derived artifact sha256")

    return {
        **data,
        "receipt_path": path.as_posix(),
        "receipt_sha256": sha256(path),
        "dimensions": dimensions,
    }


def cell(dimension: dict[str, Any]) -> str:
    status = dimension["status"]
    return {"pass": "PASS", "fail": "FAIL", "not_run": "NOT RUN", "na": "N/A"}[status]


def compile_results(receipts: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    rows = []
    summary_cases = []
    for receipt in sorted(receipts, key=lambda r: r["case_id"]):
        d = receipt["dimensions"]
        note = receipt.get("notes", "").replace("|", "\\|")
        rows.append(
            f"| {receipt['case_id']} — {receipt['title']} | {cell(d['visual_plausibility'])} | "
            f"{cell(d['geometry_validity'])} | {cell(d['revision_integrity'])} | "
            f"{cell(d['meshability'])} | {note} |"
        )
        summary_cases.append({
            "case_id": receipt["case_id"],
            "title": receipt["title"],
            "source_identity": receipt["source_identity"],
            "baseline_sha256": receipt["baseline_sha256"],
            "receipt_path": receipt["receipt_path"],
            "receipt_sha256": receipt["receipt_sha256"],
            "results": {name: d[name]["status"] for name in DIMENSIONS},
        })
    markdown = (
        "# Physical World AI artifact-backed results\n\n"
        "Generated from retained case receipts. PASS/FAIL cells require explicit evidence references.\n\n"
        "| Case | Visual plausibility | Geometry validity | Revision integrity | Meshability | Notes |\n"
        "|---|---|---|---|---|---|\n"
        + "\n".join(rows) + "\n"
    )
    summary = {
        "schema_version": "physworld-results-v1",
        "case_count": len(summary_cases),
        "cases": summary_cases,
    }
    return markdown, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts", type=Path, help="Directory containing *.json evidence receipts")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--strict", action="store_true",
                        help="Require every applicable dimension to have a terminal PASS/FAIL result")
    args = parser.parse_args()

    paths = sorted(args.receipts.glob("*.json"))
    if not paths:
        raise SystemExit("no JSON receipts found")
    receipts = [validate_receipt(path, strict=args.strict) for path in paths]
    ids = [receipt["case_id"] for receipt in receipts]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate case_id found")

    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    markdown, summary = compile_results(receipts)
    (output / "RESULTS_TABLE.md").write_text(markdown, encoding="utf-8")
    (output / "results-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    hashes = {
        name: sha256(output / name)
        for name in ("RESULTS_TABLE.md", "results-summary.json")
    }
    (output / "SHA256SUMS.json").write_text(
        json.dumps(hashes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"cases": len(receipts), "output": str(output), "strict": args.strict}))


if __name__ == "__main__":
    main()
