"""Post-outcome artifact audit that never re-executes a study case."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

EXPECTED_FAMILIES = {
    "geometry_input_contradiction": 24,
    "load_input_contradiction": 24,
    "material_input_contradiction": 24,
    "non_geometric_mutation": 24,
    "post_result_geometry_mutation": 48,
    "stale_expected_hash": 24,
    "valid": 48,
}
EXPECTED_ENDPOINTS = {
    "valid_full_acceptance": (48, 48),
    "valid_full_determinism": (48, 48),
    "full_geometry_input_detection": (24, 24),
    "full_material_input_detection": (24, 24),
    "full_load_input_detection": (24, 24),
    "full_stale_expected_hash_detection": (24, 24),
    "hash_only_semantic_non_detection": (72, 72),
    "unbound_semantic_non_detection": (72, 72),
    "full_post_mutation_detection": (48, 48),
    "hash_only_post_mutation_detection": (48, 48),
    "unbound_post_mutation_non_detection": (48, 48),
    "full_non_geometric_specificity": (24, 24),
    "hash_only_non_geometric_specificity": (24, 24),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def audit(run_dir: Path, freeze_path: Path, ledger_path: Path) -> dict[str, Any]:
    raw_path = run_dir / "raw_results.jsonl"
    metrics_path = run_dir / "metrics.json"
    manifest_path = run_dir / "manifest.json"
    metrics = _object(metrics_path)
    manifest = _object(manifest_path)
    freeze = _object(freeze_path)
    ledger = _object(ledger_path)
    records = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    _require(ledger.get("status") == "EXECUTED_ONCE", "execution ledger is not final")
    _require(ledger.get("freeze_sha256") == _sha256(freeze_path), "freeze hash differs from execution ledger")
    _require(ledger.get("manifest_sha256") == _sha256(manifest_path), "manifest hash differs from execution ledger")
    _require(ledger.get("metrics_sha256") == _sha256(metrics_path), "metrics hash differs from execution ledger")
    _require(manifest.get("raw_results_sha256") == _sha256(raw_path), "raw-results hash differs from manifest")
    _require(manifest.get("metrics_sha256") == _sha256(metrics_path), "metrics hash differs from manifest")
    _require(manifest.get("phase") == "confirmatory", "manifest is not confirmatory")
    _require(manifest.get("case_count") == 216 == len(records), "confirmatory case count is not 216")
    _require(manifest.get("cases_sha256") == freeze.get("cases_semantic_sha256"), "case semantic hashes differ")
    _require(manifest.get("source_hashes") == freeze.get("source_hashes"), "source hashes differ from freeze")
    _require(len({record.get("task_id") for record in records}) == 216, "raw task IDs are not unique")
    _require(
        dict(sorted(Counter(record.get("family") for record in records).items())) == EXPECTED_FAMILIES,
        "raw family counts differ from the frozen matrix",
    )
    _require(not any("execution_error" in record for record in records), "raw records contain an execution error")

    for record in records:
        family = record["family"]
        arms = record["arms"]
        if family == "valid":
            _require(arms["full"].get("accepted") is True, "valid full arm was rejected")
            _require(arms["full"].get("deterministic") is True, "valid full arm was nondeterministic")
        elif family in {"geometry_input_contradiction", "material_input_contradiction", "load_input_contradiction"}:
            _require(arms["full"].get("detected") is True, "full arm missed a semantic contradiction")
            _require(arms["hash_only"].get("detected") is False, "hash-only arm claimed a semantic detection")
            _require(arms["unbound"].get("detected") is False, "unbound arm claimed a semantic detection")
        elif family == "stale_expected_hash":
            _require(arms["full"].get("detected") is True, "full arm missed a stale expected hash")
            _require(arms["hash_only"].get("detected") is True, "hash-only arm missed a stale expected hash")
        elif family == "post_result_geometry_mutation":
            _require(arms["full"].get("detected") is True, "full arm missed post-result geometry drift")
            _require(arms["hash_only"].get("detected") is True, "hash-only arm missed post-result geometry drift")
            _require(arms["unbound"].get("detected") is False, "unbound arm claimed geometry freshness detection")
        elif family == "non_geometric_mutation":
            _require(arms["full"].get("current") is True, "full arm falsely invalidated non-geometric change")
            _require(arms["hash_only"].get("current") is True, "hash-only arm falsely invalidated non-geometric change")

    for name, expected in EXPECTED_ENDPOINTS.items():
        endpoint = metrics["endpoints"][name]
        observed = (int(endpoint["successes"]), int(endpoint["total"]))
        _require(observed == expected, f"endpoint {name} differs: {observed} != {expected}")

    _require(metrics.get("disposition") == "SUPPORTED_WITHIN_CONTROLLED_CONTRACT", "unexpected disposition")
    return {
        "schema_version": "nc-physics-v2-post-outcome-audit-v1",
        "status": "PASS",
        "case_execution_performed": False,
        "case_count": len(records),
        "family_counts": EXPECTED_FAMILIES,
        "endpoint_count": len(EXPECTED_ENDPOINTS),
        "disposition": metrics["disposition"],
        "freeze_sha256": _sha256(freeze_path),
        "manifest_sha256": _sha256(manifest_path),
        "metrics_sha256": _sha256(metrics_path),
        "raw_results_sha256": _sha256(raw_path),
        "boundary": "internal post-outcome artifact audit; not independent reproduction or external validation",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("refusing to overwrite an existing audit receipt")
    receipt = audit(args.run_dir, args.freeze, args.ledger)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
