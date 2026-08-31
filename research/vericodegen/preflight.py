"""Offline preflight receipt for all frozen VeriCodeGen Stage 2 methodology artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from research.vericodegen.prompt_freeze import freeze_prompt_bundle
from research.vericodegen.stage2_manifest import MANIFEST_VERSION, validate_manifest


ARTIFACT_PATHS = {
    "benchmark_schema": "research/vericodegen/benchmark_schema.json",
    "structured_schema": "research/vericodegen/structured_output.schema.json",
    "verifier": "research/vericodegen/verifier.py",
    "analysis_plan": "research/vericodegen/analysis_plan_v1.json",
    "prompt_bundle": "research/vericodegen/prompt_bundle_v1.json",
    "stage2_manifest_template": "research/vericodegen/stage2_run_manifest.example.json",
}


class PreflightError(ValueError):
    """Raised when research methodology artifacts are missing or not safely frozen."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PreflightError(f"{path} must contain a JSON object")
    return value


def build_preflight_receipt(root: str | Path, *, prompt_output_dir: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    resolved = {name: root_path / relative for name, relative in ARTIFACT_PATHS.items()}
    missing = [str(path) for path in resolved.values() if not path.is_file()]
    if missing:
        raise PreflightError("missing methodology artifacts:\n- " + "\n- ".join(missing))

    analysis_plan = _load_object(resolved["analysis_plan"])
    if analysis_plan.get("analysis_version") != "vericodegen-analysis-v1":
        raise PreflightError("analysis plan version is not frozen to vericodegen-analysis-v1")
    if analysis_plan.get("scientific_evidence") is not False or analysis_plan.get("outcomes_observed") is not False:
        raise PreflightError("analysis plan must remain pre-outcome and non-evidentiary")

    stage2_template = _load_object(resolved["stage2_manifest_template"])
    if stage2_template.get("manifest_version") != MANIFEST_VERSION:
        raise PreflightError("Stage 2 template is not on the current manifest protocol version")
    if stage2_template.get("authorized") is not False:
        raise PreflightError("Stage 2 template must remain authorized=false")
    structural_errors = validate_manifest(stage2_template, require_authorized=False)
    # The blank template is expected to be incomplete, but its safety booleans must already be correct.
    forbidden_template_errors = [
        error
        for error in structural_errors
        if "retain_" in error
        or "same_attempt_limit_both_arms" in error
        or "human_correction_allowed" in error
        or "scientific_evidence" in error
    ]
    if forbidden_template_errors:
        raise PreflightError("Stage 2 template safety defaults invalid:\n- " + "\n- ".join(forbidden_template_errors))

    prompt_receipt = freeze_prompt_bundle(
        resolved["prompt_bundle"],
        repository_root=root_path,
        output_dir=prompt_output_dir,
    )

    hashes = {name: _sha256(path) for name, path in resolved.items()}
    return {
        "preflight_version": "vericodegen-preflight-v1",
        "scientific_evidence": False,
        "outcomes_observed": False,
        "stage2_authorized": False,
        "stage2_manifest_version": MANIFEST_VERSION,
        "git_commit": os.environ.get("GITHUB_SHA") or os.environ.get("GIT_COMMIT"),
        "artifact_sha256": hashes,
        "prompt_receipt": prompt_receipt,
        "ready_for_external_execution": False,
        "next_gate": (
            "A human-reviewed frozen benchmark, deterministic pilot selection, exact provider/model, "
            "decoding policy, call ceiling, cost cap, environment, and explicit authorized=true manifest "
            "are still required before Stage 2 execution."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--prompt-output-dir", type=Path, default=Path("out/vericodegen_preflight/prompts"))
    parser.add_argument("--output", type=Path, default=Path("out/vericodegen_preflight/preflight_receipt.json"))
    args = parser.parse_args()

    receipt = build_preflight_receipt(args.root, prompt_output_dir=args.prompt_output_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
