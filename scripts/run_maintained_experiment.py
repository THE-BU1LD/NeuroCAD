#!/usr/bin/env python3
"""Run NeuroCAD's smallest maintained experiment with a provenance receipt.

The current maintained experiment is the VeriCodeGen Stage-1 scripted plumbing
smoke. It is engineering evidence only, not model-performance evidence.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=repo, text=True, stderr=subprocess.STDOUT
    ).strip()


def openscad_version() -> str:
    executable = shutil.which("openscad")
    if not executable:
        raise SystemExit("OpenSCAD is required for the maintained Stage-1 experiment.")
    proc = subprocess.run(
        [executable, "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
    )
    if proc.returncode != 0:
        raise SystemExit(f"Could not read OpenSCAD version: {proc.stdout.strip()}")
    return proc.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the maintained NeuroCAD experiment and emit a machine-readable provenance receipt."
    )
    parser.add_argument(
        "--outdir",
        help="Result directory. Defaults to out/maintained_experiment/<UTC timestamp>.",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    commit = git(repo, "rev-parse", "HEAD")
    dirty = bool(git(repo, "status", "--porcelain"))
    if dirty:
        raise SystemExit(
            "Refusing to run the maintained experiment from a dirty checkout; commit or stash changes first."
        )

    timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    timestamp_text = timestamp.isoformat().replace("+00:00", "Z")
    timestamp_slug = timestamp.strftime("%Y%m%dT%H%M%SZ")
    outdir = (
        Path(args.outdir).expanduser().resolve()
        if args.outdir
        else (repo / "out" / "maintained_experiment" / timestamp_slug)
    )
    stage_out = outdir / "vericodegen_stage1"
    outdir.mkdir(parents=True, exist_ok=False)

    experiment_source = repo / "research" / "vericodegen" / "dev_smoke.py"
    command = [
        sys.executable,
        "-m",
        "research.vericodegen.dev_smoke",
        "--outdir",
        str(stage_out),
    ]
    stdout_path = outdir / "stdout.log"
    stderr_path = outdir / "stderr.log"

    env = dict(__import__("os").environ)
    env["GIT_COMMIT"] = commit
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr:
        proc = subprocess.run(command, cwd=repo, env=env, text=True, stdout=stdout, stderr=stderr, check=False)

    summary_path = stage_out / "summary.json"
    attempts_path = stage_out / "attempts.jsonl"
    finals_path = stage_out / "finals.jsonl"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else None

    artifacts: dict[str, dict[str, str | None]] = {}
    for label, path in {
        "summary": summary_path,
        "attempts": attempts_path,
        "finals": finals_path,
        "stdout": stdout_path,
        "stderr": stderr_path,
    }.items():
        artifacts[label] = {
            "path": str(path.relative_to(repo)) if path.is_relative_to(repo) else str(path),
            "sha256": sha256(path) if path.exists() else None,
        }

    receipt = {
        "schema_version": 1,
        "experiment_id": "vericodegen-stage1-scripted-plumbing-smoke-v1",
        "scientific_evidence": False,
        "claim_boundary": (
            "Scripted Stage-1 fixtures only. This run verifies maintained experiment plumbing, "
            "shared verification, retry accounting, and provenance; it does not establish model "
            "performance, VeriCodeGen superiority, external validation, or revive the falsified typed-parser mechanism."
        ),
        "timestamp_utc": timestamp_text,
        "git_commit": commit,
        "git_dirty": dirty,
        "command": shlex.join(command),
        "working_directory": str(repo),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "openscad_version": openscad_version(),
        "config": {
            "source": str(experiment_source.relative_to(repo)),
            "source_sha256": sha256(experiment_source),
            "seed_policy": "deterministic scripted fixtures; no stochastic seed is used",
            "seeds": [],
        },
        "exit_status": proc.returncode,
        "metrics": summary,
        "artifacts": artifacts,
    }
    receipt_path = outdir / "run_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(receipt, indent=2, sort_keys=True))
    print(f"receipt={receipt_path}")
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    if summary is None:
        raise SystemExit("Maintained experiment did not produce summary.json")


if __name__ == "__main__":
    main()
