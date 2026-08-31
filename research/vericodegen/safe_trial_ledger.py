"""Fail-closed Stage 2 evaluation entrypoint around the frozen trial ledger.

This module is intentionally small and provider-neutral. It exists to close two
post-merge integrity defects without changing any frozen scientific inputs:

1. reject captures that exceed the frozen cost cap *before* the legacy ledger
   can emit analysis-ready files; and
2. classify structured-arm unknown geometry kinds as unsupported operations
   rather than syntax/compile failures during evaluation.

The historical NeuroCAD typed-parser claim remains falsified. This module does
not call a model provider and does not authorize Stage 2 execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from research.vericodegen import trial_ledger as _ledger
from research.vericodegen.arm_adapter import ArmAdapterError


def classify_adapter_error(exc: ArmAdapterError) -> str:
    """Map adapter contract failures into the frozen failure taxonomy."""

    lowered = str(exc).lower()
    if "unsupported" in lowered or "kind must be one of" in lowered:
        return "unsupported_operation"
    return "syntax_compile_failure"


def _cost_preflight(*, manifest_path: Path, capture_path: Path, outdir: Path) -> None:
    """Reject an over-budget capture before analysis-ready artifacts can exist."""

    manifest = _ledger.load_manifest(manifest_path)
    capture_rows = _ledger.load_capture_jsonl(capture_path)
    total_cost = sum(float(row["estimated_cost_usd"]) for row in capture_rows)
    cost_cap = float(manifest["cost_cap_usd"])
    if total_cost <= cost_cap:
        return

    outdir.mkdir(parents=True, exist_ok=True)
    rejection = {
        "ledger_version": _ledger.LEDGER_VERSION,
        "stage": "stage2_frozen_pilot_offline_evaluation",
        "accepted": False,
        "scientific_evidence": False,
        "reason": "cost_cap_exceeded",
        "manifest_sha256": _ledger.sha256_file(manifest_path),
        "capture_sha256": _ledger.sha256_file(capture_path),
        "total_estimated_cost_usd": total_cost,
        "cost_cap_usd": cost_cap,
    }
    (outdir / "rejection.json").write_text(
        json.dumps(rejection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    raise _ledger.TrialLedgerError(
        f"captured cost ${total_cost:.6f} exceeds frozen cost cap ${cost_cap:.6f}"
    )


def evaluate_capture(**kwargs: Any) -> dict[str, Any]:
    """Run the frozen ledger only after the integrity preflight succeeds."""

    manifest_path = Path(kwargs["manifest_path"])
    capture_path = Path(kwargs["capture_path"])
    outdir = Path(kwargs["outdir"])
    _cost_preflight(
        manifest_path=manifest_path,
        capture_path=capture_path,
        outdir=outdir,
    )

    original_classifier = _ledger._classify_adapter_error
    _ledger._classify_adapter_error = classify_adapter_error
    try:
        return _ledger.evaluate_capture(**kwargs)
    finally:
        _ledger._classify_adapter_error = original_classifier


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--benchmark-manifest", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--pilot-selection", type=Path, required=True)
    parser.add_argument("--structured-schema", type=Path, required=True)
    parser.add_argument("--verifier", type=Path, required=True)
    parser.add_argument("--analysis-plan", type=Path, required=True)
    parser.add_argument("--prompt-receipt", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument(
        "--skip-git-head-check",
        action="store_true",
        help="development-only: do not require repository HEAD to equal the frozen manifest",
    )
    args = parser.parse_args()

    summary = evaluate_capture(
        manifest_path=args.manifest,
        benchmark_manifest_path=args.benchmark_manifest,
        benchmark_path=args.benchmark,
        pilot_selection_path=args.pilot_selection,
        structured_schema_path=args.structured_schema,
        verifier_path=args.verifier,
        analysis_plan_path=args.analysis_plan,
        prompt_receipt_path=args.prompt_receipt,
        capture_path=args.capture,
        repository_root=args.repository_root,
        outdir=args.outdir,
        require_git_head=not args.skip_git_head_check,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
