"""Build the self-contained, frozen Kaggle execution notebook."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any

DATASET_PATHS = (
    "samples/abstract.parquet",
    "samples/detailed.parquet",
    "cadtests/abstract.parquet",
    "cadtests/detailed.parquet",
)
EXPECTED_INPUT_SHA256 = {
    "neurocad-source.tar.gz": "a504d7ec532d318fddd9c03d4bf81a3957a99b36692c5c6a199a1149d37ef5c5",
    "cadtestbench-source.tar.gz": "70e1881242984ac10bff800838e1c32b003a4f0a4a45b8cf9531d0445153b5e5",
    "requirements-hosted.lock": "31cf03a57f39be995e0958e8b6cc845a5de83f60844e0694446e470378c3145c",
    "dataset/samples/abstract.parquet": "67a5779bc5114ce4db6bc9be89bf22c25e707bc83e7431214cddfac23f980536",
    "dataset/samples/detailed.parquet": "76b2d20def7946e1e3216b72a8acb83825c489c373b23ac514b77885ae275b37",
    "dataset/cadtests/abstract.parquet": "7ffa58d245c4975e4365bccd2acbaaf2c0622241223cf170bdc952a8e5563713",
    "dataset/cadtests/detailed.parquet": "470a47347653fbea969a9b8f1d415bb21cf6ee2a2c1ed46613752ef275b2773a",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _code_cell(source: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def _markdown_cell(source: str) -> dict[str, Any]:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def build_notebook(
    *,
    source_archive: Path,
    evaluator_archive: Path,
    dataset_root: Path,
    requirements: Path,
    execution_manifest: Path,
) -> dict[str, Any]:
    payload_paths = {
        "neurocad-source.tar.gz": source_archive,
        "cadtestbench-source.tar.gz": evaluator_archive,
        "requirements-hosted.lock": requirements,
        "execution_manifest.json": execution_manifest,
    }
    for relative in DATASET_PATHS:
        payload_paths[f"dataset/{relative}"] = dataset_root / relative

    payload: dict[str, str] = {}
    hashes: dict[str, str] = {}
    for name, path in payload_paths.items():
        data = path.read_bytes()
        payload[name] = base64.b64encode(data).decode("ascii")
        hashes[name] = _sha256(data)
        expected = EXPECTED_INPUT_SHA256.get(name)
        if expected is not None and hashes[name] != expected:
            raise ValueError(f"frozen input hash mismatch for {name}: {hashes[name]}")

    setup_source = f'''from __future__ import annotations
import base64, hashlib, json, pathlib, shutil, subprocess, sys, tarfile

PAYLOAD = {json.dumps(payload, sort_keys=True)}
EXPECTED_SHA256 = {json.dumps(hashes, sort_keys=True, indent=2)}
ROOT = pathlib.Path("/kaggle/working/nc_cadtestbench_v1")
if ROOT.exists():
    raise RuntimeError(f"refusing to replace existing frozen root: {{ROOT}}")
PAYLOAD_ROOT = ROOT / "payload"
PAYLOAD_ROOT.mkdir(parents=True)
for name, encoded in PAYLOAD.items():
    path = PAYLOAD_ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    data = base64.b64decode(encoded, validate=True)
    observed = hashlib.sha256(data).hexdigest()
    if observed != EXPECTED_SHA256[name]:
        raise RuntimeError(f"payload hash mismatch for {{name}}: {{observed}}")
    path.write_bytes(data)
print(json.dumps({{"payload_sha256": EXPECTED_SHA256}}, indent=2, sort_keys=True))
'''
    install_source = '''def safe_extract(archive_path, destination):
    destination = destination.resolve()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            if member.issym() or member.islnk():
                raise RuntimeError(f"links are forbidden in frozen archives: {member.name}")
            target = (destination / member.name).resolve()
            if destination != target and destination not in target.parents:
                raise RuntimeError(f"unsafe archive member: {member.name}")
        archive.extractall(destination)

NEUROCAD_ROOT = ROOT / "neurocad"
EVALUATOR_ROOT = ROOT / "cadtestbench"
safe_extract(PAYLOAD_ROOT / "neurocad-source.tar.gz", NEUROCAD_ROOT)
safe_extract(PAYLOAD_ROOT / "cadtestbench-source.tar.gz", EVALUATOR_ROOT)

install_log = ROOT / "environment_install.log"
with install_log.open("w", encoding="utf-8") as log:
    dependency_install = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-input", "-r", str(PAYLOAD_ROOT / "requirements-hosted.lock")],
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if dependency_install.returncode == 0:
        evaluator_install = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-input", "--no-deps", str(EVALUATOR_ROOT)],
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    else:
        evaluator_install = None
if dependency_install.returncode != 0 or evaluator_install is None or evaluator_install.returncode != 0:
    print(install_log.read_text(encoding="utf-8"))
    raise RuntimeError("frozen environment installation failed; retained environment_install.log")
print("FROZEN_ENVIRONMENT_INSTALLED")
'''
    run_source = '''environment_receipt = ROOT / "environment_receipt.txt"
with environment_receipt.open("w", encoding="utf-8") as receipt:
    subprocess.run([sys.executable, "--version"], stdout=receipt, stderr=subprocess.STDOUT, text=True, check=True)
    subprocess.run([sys.executable, "-m", "pip", "freeze", "--all"], stdout=receipt, stderr=subprocess.STDOUT, text=True, check=True)

output_root = ROOT / "results"
run_log = ROOT / "execution.log"
command = [
    sys.executable,
    str(NEUROCAD_ROOT / "research/cadtestbench_v1/run_hosted.py"),
    "--dataset-root",
    str(PAYLOAD_ROOT / "dataset"),
    "--output-root",
    str(output_root),
]
with run_log.open("w", encoding="utf-8") as log:
    completed = subprocess.run(command, cwd=NEUROCAD_ROOT, stdout=log, stderr=subprocess.STDOUT, text=True, check=False)
print(f"FROZEN_EXECUTION_RETURN_CODE={completed.returncode}")
if completed.returncode != 0:
    print(run_log.read_text(encoding="utf-8")[-20000:])
    raise RuntimeError("frozen execution failed; retained execution.log and partial result tree")
print(run_log.read_text(encoding="utf-8")[-20000:])
'''
    package_source = '''for path in (PAYLOAD_ROOT / "execution_manifest.json", ROOT / "environment_install.log", ROOT / "environment_receipt.txt", ROOT / "execution.log"):
    if not path.is_file():
        raise RuntimeError(f"required retained evidence missing: {path}")
bundle_base = pathlib.Path("/kaggle/working/neurocad_nc_cadtestbench_v1_results")
bundle_path = pathlib.Path(shutil.make_archive(str(bundle_base), "gztar", ROOT))
bundle_sha256 = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
print(f"RESULT_BUNDLE={bundle_path}")
print(f"RESULT_BUNDLE_BYTES={bundle_path.stat().st_size}")
print(f"RESULT_BUNDLE_SHA256={bundle_sha256}")
print("NC_CADTESTBENCH_V1_COMPLETE")
'''
    return {
        "cells": [
            _markdown_cell(
                "# NeuroCAD NC-CADTESTBENCH-V1 — frozen first execution\n\n"
                "This notebook executes the pinned deterministic NeuroCAD implementation against all 200 abstract and all 200 detailed CADTestBench conditions. Rejections remain failures. It is a public external benchmark successor, not the unopened blind NC-EXT-EVAL-V0 study, and it does not rehabilitate the falsified historical typed-parser causal claim.\n"
            ),
            _code_cell(setup_source),
            _code_cell(install_source),
            _code_cell(run_source),
            _code_cell(package_source),
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "kaggle": {
                "accelerator": "none",
                "dataSources": [],
                "isGpuEnabled": False,
                "isInternetEnabled": True,
                "language": "python",
                "sourceType": "notebook",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--evaluator-archive", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--requirements", type=Path, required=True)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    notebook = build_notebook(
        source_archive=args.source_archive,
        evaluator_archive=args.evaluator_archive,
        dataset_root=args.dataset_root,
        requirements=args.requirements,
        execution_manifest=args.execution_manifest,
    )
    args.output.write_text(
        json.dumps(notebook, indent=1, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
