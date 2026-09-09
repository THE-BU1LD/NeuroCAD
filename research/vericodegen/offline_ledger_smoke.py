"""Development-only real-OpenSCAD smoke for the frozen offline trial ledger.

No model or provider is called. The script constructs a tiny scripted fixture,
freezes/hash-pins its methodology bytes, evaluates captured direct/structured
outputs, deliberately exercises one retry per arm, and proves the ledger can feed
the predeclared paired analysis without dropping failed attempts.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess  # Git/OpenSCAD use resolved executables and fixed shell-free argv.  # nosec B404
from pathlib import Path
from typing import Any

from research.vericodegen.analysis import analyze_rows
from research.vericodegen.analysis import load_jsonl as load_analysis_jsonl
from research.vericodegen.benchmark_freeze import benchmark_jsonl, build_manifest
from research.vericodegen.prompt_freeze import freeze_prompt_bundle
from research.vericodegen.safe_trial_ledger import evaluate_capture
from research.vericodegen.stage2_manifest import SAFE_EVALUATION_ENTRYPOINT
from research.vericodegen.trial_ledger import CAPTURE_VERSION, sha256_file

ROOT = Path(__file__).resolve().parents[2]


class OfflineSmokeError(RuntimeError):
    """Raised when an offline smoke prerequisite cannot be proven."""


def _git_head() -> str:
    executable = shutil.which("git")
    if executable is None:
        raise OfflineSmokeError("cannot resolve an immutable source revision: git executable not found")
    try:
        proc = subprocess.run(  # Resolved executable and fixed argument vector.  # nosec B603
            [executable, "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OfflineSmokeError(f"cannot resolve an immutable source revision: {exc}") from exc
    revision = proc.stdout.strip()
    if proc.returncode != 0 or not revision:
        detail = proc.stderr.strip() or "git rev-parse returned no revision"
        raise OfflineSmokeError(
            "offline ledger smoke requires a real Git checkout so its authorized development manifest "
            f"can be pinned to HEAD: {detail}"
        )
    return revision


def _openscad_version() -> str:
    executable = shutil.which("openscad")
    if executable is None:
        raise OfflineSmokeError("OpenSCAD is required for the offline ledger smoke")
    proc = subprocess.run(  # Resolved executable and fixed argument vector.  # nosec B603
        [executable, "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )
    return proc.stdout.strip() or "OpenSCAD unknown"


def _task(number: int, family: str) -> dict[str, Any]:
    return {
        "prompt_id": f"VCG-{number:03d}",
        "prompt_text": (
            f"Development fixture {number}: create one centered watertight cube with side length "
            "exactly four millimeters and no additional geometry."
        ),
        "task_family": family,
        "required_relations": ["single-centered-body"],
        "hard_constraints": {
            "watertight": True,
            "max_components": 1,
            "volume": {"min": 63.5, "max": 64.5},
            "extents": {
                "x": {"min": 3.99, "max": 4.01},
                "y": {"min": 3.99, "max": 4.01},
                "z": {"min": 3.99, "max": 4.01},
            },
        },
        "semantic_rubric": [
            {
                "criterion": "development_fixture_identity",
                "description": "Contains exactly the requested single cube fixture.",
            }
        ],
        "notes": "SCRIPTED DEVELOPMENT FIXTURE ONLY; not held-out benchmark evidence.",
    }


def _structured_cube() -> str:
    return json.dumps(
        {
            "spec_version": "vericodegen-structured-v1",
            "title": "development-cube",
            "components": [
                {
                    "name": "body",
                    "geometry": {"kind": "box", "size": [4, 4, 4], "center": True},
                }
            ],
            "connections": [],
        },
        sort_keys=True,
    )


def _capture_row(
    prompt_id: str,
    arm: str,
    attempt: int,
    raw_output: str,
) -> dict[str, Any]:
    return {
        "capture_version": CAPTURE_VERSION,
        "prompt_id": prompt_id,
        "seed": 20260831,
        "arm": arm,
        "attempt": attempt,
        "generation_status": "completed",
        "raw_output": raw_output,
        "generated_tokens": 20 + attempt,
        "wall_clock_seconds": 0.01 * attempt,
        "estimated_cost_usd": 0.001,
        "provider_request_id": f"offline-fixture-{prompt_id}-{arm}-{attempt}",
    }


def run_smoke(outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    frozen = outdir / "frozen"
    frozen.mkdir(parents=True, exist_ok=True)

    tasks = [
        _task(1, "in_distribution"),
        _task(2, "compositional"),
        _task(3, "ood_constraint_stress"),
    ]
    benchmark_path = frozen / "development_benchmark.jsonl"
    benchmark_path.write_text(benchmark_jsonl(tasks), encoding="utf-8")

    benchmark_schema = ROOT / "research/vericodegen/benchmark_schema.json"
    benchmark_manifest = build_manifest(
        tasks,
        schema_sha256=sha256_file(benchmark_schema),
        benchmark_filename=benchmark_path.name,
    )
    benchmark_manifest_path = frozen / "development_benchmark.manifest.json"
    benchmark_manifest_path.write_text(
        json.dumps(benchmark_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    pilot_selection = {
        "selection_version": "vericodegen-development-fixture-selection-v1",
        "development_fixture": True,
        "pilot_task_ids": [task["prompt_id"] for task in tasks],
        "benchmark_sha256": sha256_file(benchmark_path),
    }
    pilot_selection_path = frozen / "development_pilot_selection.json"
    pilot_selection_path.write_text(
        json.dumps(pilot_selection, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    prompt_dir = frozen / "prompts"
    prompt_receipt = freeze_prompt_bundle(
        ROOT / "research/vericodegen/prompt_bundle_v1.json",
        repository_root=ROOT,
        output_dir=prompt_dir,
    )
    prompt_receipt_path = prompt_dir / "prompt_receipt_v1.json"

    structured_schema = ROOT / "research/vericodegen/structured_output.schema.json"
    verifier = ROOT / "research/vericodegen/verifier.py"
    analysis_plan = ROOT / "research/vericodegen/analysis_plan_v1.json"
    git_head = _git_head()

    manifest = {
        "manifest_version": "vericodegen-stage2-v2",
        "stage": "stage2_frozen_pilot",
        "authorized": True,
        "scientific_evidence": False,
        "evaluation_entrypoint": SAFE_EVALUATION_ENTRYPOINT,
        "benchmark_manifest_sha256": sha256_file(benchmark_manifest_path),
        "pilot_selection_sha256": sha256_file(pilot_selection_path),
        "structured_schema_sha256": sha256_file(structured_schema),
        "verifier_sha256": sha256_file(verifier),
        "analysis_plan_sha256": sha256_file(analysis_plan),
        "pilot_task_ids": [task["prompt_id"] for task in tasks],
        "provider": "offline-scripted-fixture-provider",
        "model": "offline-scripted-fixture-model-v1",
        "decoding": {
            "temperature": 0.0,
            "top_p": 1.0,
            "max_output_tokens": 512,
            "seeds": [20260831],
        },
        "retry_policy": {
            "max_attempts": 2,
            "feedback_policy": "Development fixture only: same machine-failure retry budget for both arms.",
            "same_attempt_limit_both_arms": True,
            "human_correction_allowed": False,
        },
        "prompt_templates": {
            "direct_sha256": prompt_receipt["direct_sha256"],
            "structured_sha256": prompt_receipt["structured_sha256"],
            "receipt_sha256": sha256_file(prompt_receipt_path),
        },
        "environment": {
            "openscad_version": _openscad_version(),
            "openscad_fn": 64,
            "compile_timeout_seconds": 60,
        },
        "retention_policy": {
            "retain_raw_outputs": True,
            "retain_failed_trials": True,
            "retain_compile_logs": True,
        },
        "git_commit": git_head,
        "cost_cap_usd": 0.10,
        "estimated_max_calls": 12,
        "notes": "SCRIPTED OFFLINE DEVELOPMENT FIXTURE. No external provider/model call occurred.",
    }
    manifest_path = frozen / "authorized_development_stage2.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    valid_direct = "cube(size=[4,4,4], center=true);"
    invalid_direct = "cube(size=[4,4,4], center=true"
    valid_structured = _structured_cube()
    invalid_structured = json.dumps(
        {
            "spec_version": "vericodegen-structured-v1",
            "title": "invalid-development-fixture",
            "components": [{"name": "body", "geometry": {"kind": "unsupported"}}],
        },
        sort_keys=True,
    )

    captures: list[dict[str, Any]] = []
    for task in tasks[:2]:
        captures.append(_capture_row(task["prompt_id"], "direct", 1, valid_direct))
        captures.append(_capture_row(task["prompt_id"], "structured", 1, valid_structured))
    captures.extend(
        [
            _capture_row("VCG-003", "direct", 1, invalid_direct),
            _capture_row("VCG-003", "direct", 2, valid_direct),
            _capture_row("VCG-003", "structured", 1, invalid_structured),
            _capture_row("VCG-003", "structured", 2, valid_structured),
        ]
    )
    capture_path = frozen / "captured_attempts.jsonl"
    capture_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in captures),
        encoding="utf-8",
    )

    evaluation_dir = outdir / "evaluation"
    summary = evaluate_capture(
        manifest_path=manifest_path,
        benchmark_manifest_path=benchmark_manifest_path,
        benchmark_path=benchmark_path,
        pilot_selection_path=pilot_selection_path,
        structured_schema_path=structured_schema,
        verifier_path=verifier,
        analysis_plan_path=analysis_plan,
        prompt_receipt_path=prompt_receipt_path,
        capture_path=capture_path,
        repository_root=ROOT,
        outdir=evaluation_dir,
        require_git_head=True,
    )
    if summary["captured_attempts"] != 8:
        raise RuntimeError(f"offline ledger smoke expected 8 captured attempts: {summary}")
    if summary["final_cells"] != 6 or summary["hvr_pass_cells"] != 6:
        raise RuntimeError(f"offline ledger smoke expected 6/6 final HVR cells: {summary}")
    if summary["scientific_evidence"] is not False:
        raise RuntimeError("development ledger smoke must remain non-evidentiary")

    evaluated_attempts = [
        json.loads(line)
        for line in (evaluation_dir / "attempts_evaluated.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    failed_attempts = [row for row in evaluated_attempts if not row["hvr"]]
    if len(failed_attempts) != 2:
        raise RuntimeError(f"expected exactly two retained failed retry attempts; got {len(failed_attempts)}")

    finals = load_analysis_jsonl(evaluation_dir / "finals_for_analysis.jsonl")
    analysis = analyze_rows(finals, bootstrap_replicates=500, bootstrap_seed=20260831)
    if analysis["paired_units"] != 3:
        raise RuntimeError(f"expected three paired analysis units: {analysis}")
    if analysis["primary"]["direct_hvr"] != 1.0 or analysis["primary"]["structured_hvr"] != 1.0:
        raise RuntimeError(f"expected both development fixture arms HVR=1.0: {analysis}")

    receipt = {
        "smoke_version": "vericodegen-offline-ledger-smoke-v1",
        "scientific_evidence": False,
        "provider_calls": 0,
        "captured_attempts": summary["captured_attempts"],
        "retained_failed_attempts": len(failed_attempts),
        "final_cells": summary["final_cells"],
        "hvr_pass_cells": summary["hvr_pass_cells"],
        "paired_units": analysis["paired_units"],
        "direct_hvr": analysis["primary"]["direct_hvr"],
        "structured_hvr": analysis["primary"]["structured_hvr"],
        "ledger_tip_sha256": summary["ledger_tip_sha256"],
        "capture_sha256": summary["capture_sha256"],
        "finals_sha256": summary["finals_for_analysis_sha256"],
        "claim_boundary": "Scripted offline integration evidence only; no scientific treatment effect is claimed.",
    }
    (outdir / "smoke_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path("out/vericodegen_offline_ledger_smoke"))
    args = parser.parse_args()
    try:
        receipt = run_smoke(args.outdir)
    except OfflineSmokeError as exc:
        parser.error(str(exc))
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
