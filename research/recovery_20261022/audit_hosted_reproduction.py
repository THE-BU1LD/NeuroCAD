"""Audit the retained hosted Physics v2 reproduction without executing a case.

Requires Python 3.10+ and the frozen source Git object. This reads only retained
artifacts and executes only five pure analysis functions extracted from the
hash-verified frozen study source. Output is append-only; --check writes nothing.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import statistics
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RECOVERY = "research/recovery_20261022"
HOSTED = f"{RECOVERY}/hosted-reproduction"
V2 = "research/physics_v2"
ORIGINAL = f"{V2}/runs/NC-PHYS-V2-CONFIRM-001"
COMMIT = "786ba9ba5c2249a710529c3b07bf82d4e29c7f36"
ARCHIVE_SHA256 = "4c8c9e7af18fcaed4a88d3ecd0bfa00d9b5161ae898ee20c7840d17e2220d217"
ENVIRONMENT_FIELDS = {"elapsed_ms", "verify_elapsed_ms", "report_bytes", "binding_sha256"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pretty(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def load(path: Path) -> Any:
    return json.loads(path.read_bytes())


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_bytes().splitlines() if line.strip()]


def git_blob(root: Path, name: str) -> bytes:
    return subprocess.run(["git", "show", f"{COMMIT}:{name}"], cwd=root,
                          check=True, capture_output=True).stdout


def frozen_analysis(source: bytes, records: list[dict[str, Any]]) -> dict[str, Any]:
    names = {"wilson_interval", "exact_mcnemar_p", "_endpoint", "_combined_endpoint", "analyze"}
    selected = [node for node in ast.parse(source).body
                if isinstance(node, ast.FunctionDef) and node.name in names]
    require({node.name for node in selected} == names, "frozen analysis functions missing")
    namespace: dict[str, Any] = {"math": math, "Counter": Counter, "defaultdict": defaultdict,
                                 "Any": Any, "STUDY_VERSION": "nc-physics-v2-study-v1"}
    # No runner, case evaluator, imports, resource gate, or main block is loaded.
    exec(compile(ast.Module(body=selected, type_ignores=[]), "frozen-analysis-only", "exec"), namespace)  # noqa: S102 - Hash-verified, named pure functions only.
    return namespace["analyze"](records)


def differences(left: Any, right: Any, path: str = "") -> list[str]:
    if isinstance(left, dict) and isinstance(right, dict):
        result = []
        for key in sorted(left.keys() | right.keys()):
            name = f"{path}.{key}" if path else key
            result.extend(differences(left[key], right[key], name)
                          if key in left and key in right else [name])
        return result
    return [] if left == right else [path]


def environment_check(lock: bytes, freeze_text: str, log: str) -> dict[str, Any]:
    normalize = lambda name: re.sub(r"[-_.]+", "-", name).lower()
    pins = {normalize(name): version for name, version in
            re.findall(r"^([A-Za-z0-9_.-]+)==([^ ;\\\n]+)", lock.decode(), re.MULTILINE)}
    observed = {normalize(name): version for name, version in
                re.findall(r"^([A-Za-z0-9_.-]+)==([^\n]+)$", freeze_text, re.MULTILINE)}
    # The only platform-conditional lock entry is Windows-only colorama.
    conditional = [line for line in lock.decode().splitlines() if ";" in line and "==" in line]
    require(len(conditional) == 1 and conditional[0].startswith("colorama==")
            and "os_name == 'nt' or sys_platform == 'win32'" in conditional[0],
            "review changed dependency markers before auditing")
    expected = {name: version for name, version in pins.items() if name not in {"colorama", "pip"}}
    require(observed == expected, "environment receipt differs from frozen Linux lock pins")
    require(f"{COMMIT}#egg=neurocad_research" in freeze_text, "editable source identity missing")
    installed = [line for line in log.splitlines() if "Successfully installed " in line]
    require(any(f" pip-{pins['pip']} " in f" {line} " for line in installed), "locked pip installation absent")
    require("No broken requirements found." in log, "pip check success absent from job log")
    return {"frozen_lock_sha256": sha256(lock), "matching_environment_pins": len(expected),
            "packages": dict(sorted(observed.items())), "pip_version_from_install_log": pins["pip"],
            "pip_omitted_from_default_freeze": True, "platform_exclusion": "colorama (Windows only)",
            "pip_check_recorded_success": True,
            "boundary": "Version receipt and retained installation log; not a binary attestation."}


def audit(root: Path) -> dict[str, Any]:
    hosted = root / HOSTED
    archive = root / f"{HOSTED}.zip"
    require(sha256(archive.read_bytes()) == ARCHIVE_SHA256, "GitHub artifact archive digest mismatch")
    inventory = {}
    with zipfile.ZipFile(archive) as packed:
        entries = [entry for entry in packed.infolist() if not entry.is_dir()]
        require(len({entry.filename for entry in entries}) == len(entries), "duplicate archive paths")
        for entry in entries:
            name = PurePosixPath(entry.filename)
            require(not name.is_absolute() and ".." not in name.parts
                    and name.as_posix() == entry.filename, "unsafe archive path")
            path = hosted / name
            require(path.is_file() and not path.is_symlink(), f"missing extracted file: {name}")
            content = packed.read(entry)
            require(path.read_bytes() == content, f"extraction differs: {name}")
            inventory[str(name)] = {"bytes": len(content), "sha256": sha256(content)}
    actual_files = {path.relative_to(hosted).as_posix() for path in hosted.rglob("*") if path.is_file()}
    require(actual_files == set(inventory), "unexpected or missing extracted files")

    declaration = load(hosted / "declaration.json")
    ledger = load(hosted / "CONFIRMATORY_EXECUTION.json")
    manifest = load(hosted / "run/manifest.json")
    metrics = load(hosted / "run/metrics.json")
    freeze_path = root / V2 / "frozen/freeze.json"
    cases_path = root / V2 / "frozen/NC-PHYS-V2-CONFIRM.jsonl"
    freeze = load(freeze_path)
    cases = rows(cases_path)
    original_ledger = load(root / V2 / "CONFIRMATORY_EXECUTION.json")
    original_manifest = load(root / ORIGINAL / "manifest.json")
    original_metrics = load(root / ORIGINAL / "metrics.json")
    original_rows = rows(root / ORIGINAL / "raw_results.jsonl")
    hosted_rows = rows(hosted / "run/raw_results.jsonl")
    frozen_sources = {name: git_blob(root, name) for name in freeze["source_hashes"]}
    source_hashes = {name: sha256(content) for name, content in frozen_sources.items()}
    require(source_hashes == freeze["source_hashes"] == manifest["source_hashes"]
            == declaration["frozen_source_hashes"] == original_manifest["source_hashes"],
            "frozen source hash identity mismatch")
    require(freeze_path.read_bytes() == git_blob(root, f"{V2}/frozen/freeze.json"), "freeze differs from Git blob")
    require(cases_path.read_bytes() == git_blob(root, f"{V2}/frozen/NC-PHYS-V2-CONFIRM.jsonl"),
            "case file differs from Git blob")
    canonical_cases = json.dumps(cases, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    byte_hash, semantic_hash = sha256(cases_path.read_bytes()), sha256(canonical_cases)
    require(byte_hash == freeze["cases_file_sha256"] == declaration["cases_sha256"], "case byte digest mismatch")
    require(semantic_hash == freeze["cases_semantic_sha256"] == manifest["cases_sha256"]
            == original_manifest["cases_sha256"], "canonical case digest mismatch")
    freeze_hash = sha256(freeze_path.read_bytes())
    require(freeze_hash == ledger["freeze_sha256"] == original_ledger["freeze_sha256"]
            == declaration["freeze_sha256"], "freeze digest mismatch")
    for directory, run_ledger, run_manifest in ((hosted / "run", ledger, manifest),
                                               (root / ORIGINAL, original_ledger, original_manifest)):
        require(sha256((directory / "manifest.json").read_bytes()) == run_ledger["manifest_sha256"],
                "manifest/ledger digest mismatch")
        require(sha256((directory / "metrics.json").read_bytes()) == run_ledger["metrics_sha256"]
                == run_manifest["metrics_sha256"], "metrics digest mismatch")
        require(sha256((directory / "raw_results.jsonl").read_bytes()) == run_manifest["raw_results_sha256"],
                "raw result digest mismatch")
        require(run_ledger["status"] == "EXECUTED_ONCE" and run_manifest["git_commit"] == COMMIT,
                "execution ledger or source revision mismatch")
    require(declaration["source_commit"] == COMMIT and declaration["attempt_limit"] == 1,
            "reproduction declaration mismatch")
    require(declaration["classification"] == "INTERNAL_CROSS_ENVIRONMENT_REPRODUCTION"
            and declaration["primary_outcomes_already_observed"] is True
            and declaration["independent_party"] is False, "misclassified reproduction")
    require(load(hosted / "execution.txt") == {"manifest": manifest, "metrics": metrics},
            "console execution record differs from artifacts")
    expected_status = "?? research/physics_v2/CONFIRMATORY_EXECUTION.json"
    require((hosted / "git-status-after.txt").read_text().strip() == expected_status
            == manifest["git_status"], "unexpected frozen checkout changes")
    require(manifest["resource_receipt"]["admitted"] is True
            and manifest["resource_receipt"]["disk_floor_mib"] == 2048.0
            and manifest["resource_receipt"]["disk_free_mib"] >= 2048.0
            and manifest["resource_receipt"]["memory_floor_mib"] == 512.0
            and manifest["resource_receipt"]["free_plus_speculative_mib"] >= 512.0, "resource admission mismatch")

    require(len(cases) == len(original_rows) == len(hosted_rows) == 216, "incorrect matrix size")
    require(len({case["task_id"] for case in cases}) == 216, "duplicate frozen case IDs")
    for reference, original, result in zip(cases, original_rows, hosted_rows):
        require(all(reference[key] == original[key] == result[key]
                    for key in ("task_id", "family", "model", "expected")), "case identity/order changed")
        require(set(result["arms"]) == {"full", "hash_only", "unbound"}, "arm identities changed")
        require("execution_error" not in result, "study execution error recorded")
    changed = Counter(field for left, right in zip(hosted_rows, original_rows)
                      for field in differences(left, right))
    require(all(field.startswith("arms.") and field.rsplit(".", 1)[-1] in ENVIRONMENT_FIELDS
                for field in changed), "retained contract outcome differs from original")
    scorer_source = frozen_sources[f"{V2}/study.py"]
    for records, retained, directory in ((hosted_rows, metrics, hosted / "run"),
                                         (original_rows, original_metrics, root / ORIGINAL)):
        recomputed = frozen_analysis(scorer_source, records)
        require(recomputed == retained, "frozen metrics reanalysis differs")
        require(pretty(recomputed) == (directory / "metrics.json").read_bytes(),
                "frozen metrics do not regenerate byte-for-byte")
    require(metrics["endpoints"] == original_metrics["endpoints"] and len(metrics["endpoints"]) == 13,
            "endpoint dictionaries differ")
    require(ledger["disposition"] == metrics["disposition"] == "SUPPORTED_WITHIN_CONTROLLED_CONTRACT",
            "unexpected reproduction disposition")
    timing = {}
    for arm in ("full", "hash_only", "unbound"):
        values = sorted(row["arms"][arm]["elapsed_ms"] for row in hosted_rows
                        if row["arms"][arm].get("elapsed_ms") is not None)
        timing[arm] = {**metrics["timing_diagnostics"][arm], "conventional_median_ms": statistics.median(values)}
    sizes = [row["arms"]["full"]["report_bytes"] for row in hosted_rows if "report_bytes" in row["arms"]["full"]]
    size_delta = Counter(left["arms"]["full"]["report_bytes"] - right["arms"]["full"]["report_bytes"]
                         for left, right in zip(hosted_rows, original_rows) if "report_bytes" in left["arms"]["full"])

    suites = ET.parse(hosted / "tests.xml").getroot().findall("testsuite")
    require(len(suites) == 1, "review changed test report structure")
    suite = suites[0]
    testcases = list(suite.iter("testcase"))
    skips = [{"class": case.get("classname"), "name": case.get("name"),
              "message": case.find("skipped").get("message"), "detail": case.find("skipped").text}
             for case in testcases if case.find("skipped") is not None]
    totals = {key: int(suite.get(key, "0")) for key in ("tests", "skipped", "errors", "failures")}
    require(totals == {"tests": 1212, "skipped": 9, "errors": 0, "failures": 0}
            and len(testcases) == 1212 and len(skips) == 9
            and not any(case.find("failure") is not None or case.find("error") is not None for case in testcases),
            "test summary and individual records disagree")
    require("1203 passed, 9 skipped in 66.56s" in (hosted / "tests.txt").read_text(), "test console summary mismatch")
    log_path = root / RECOVERY / "hosted-job-log.txt"
    environment = environment_check(frozen_sources["requirements-research.lock"],
                                    (hosted / "environment.txt").read_text(), log_path.read_text())
    retained_inputs = [f"{V2}/frozen/freeze.json", f"{V2}/frozen/NC-PHYS-V2-CONFIRM.jsonl",
                       f"{V2}/CONFIRMATORY_EXECUTION.json", f"{ORIGINAL}/manifest.json",
                       f"{ORIGINAL}/metrics.json", f"{ORIGINAL}/raw_results.jsonl", f"{RECOVERY}/hosted-job-log.txt"]
    return {
        "schema_version": "neurocad-hosted-reproduction-audit-v1", "status": "PASS",
        "audit_mode": "READ_ONLY_ARTIFACT_VALIDATION_AND_REANALYSIS_NO_CASE_EXECUTION",
        "classification": declaration["classification"], "primary_outcomes_already_observed": True,
        "independent_party": False, "execution_provider": "GitHub Actions", "kaggle_execution": False,
        "github": {"run_id": 39726824693, "artifact_id": 12402399676,
                   "run_url": "https://github.com/THE-BU1LD/NeuroCAD/actions/runs/39726824693",
                   "workflow_commit": declaration["workflow_commit"], "attempt_limit": 1,
                   "metadata_basis": "GitHub run/artifact identifiers and archive digest retrieved by the coordinating session."},
        "archive": {"path": f"{HOSTED}.zip", "sha256": ARCHIVE_SHA256,
                    "extracted_file_count": len(inventory), "all_extracted_bytes_match": True,
                    "files": inventory},
        "retained_input_sha256": {name: sha256((root / name).read_bytes()) for name in retained_inputs},
        "source_identity": {"execution_commit": COMMIT, "freeze_source_commit": freeze["source_commit"],
                            "checked_git_blob_count": len(source_hashes), "source_hashes": source_hashes,
                            "all_git_blob_hashes_match_freeze_and_both_manifests": True,
                            "post_run_git_status": expected_status},
        "case_identity": {"unique_records": 216, "frozen_jsonl_byte_sha256": byte_hash,
                          "canonical_case_list_sha256": semantic_hash,
                          "hash_definition": "JSONL file bytes versus SHA256(json.dumps(parsed_case_list, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')).",
                          "file_and_canonical_hashes_recomputed": True, "original_and_hosted_order_match_freeze": True,
                          "family_counts": dict(sorted(Counter(case["family"] for case in cases).items())),
                          "model_counts": dict(sorted(Counter(case["model"] for case in cases).items()))},
        "run_integrity": {"freeze_sha256": freeze_hash, "raw_results_sha256": manifest["raw_results_sha256"],
                          "metrics_sha256": manifest["metrics_sha256"], "manifest_sha256": ledger["manifest_sha256"],
                          "ledger_status": ledger["status"], "original_runner_phase_unchanged": manifest["phase"],
                          "ledger_manifest_raw_metrics_digest_chain_matches": True,
                          "both_metrics_files_regenerated_byte_identically": True},
        "results": {"case_count": 216, "case_arm_observations": 648, "execution_errors": [],
                    "disposition": metrics["disposition"], "all_13_endpoint_dictionaries_equal_original": True,
                    "endpoints": metrics["endpoints"],
                    "paired_full_vs_unbound_post_mutation": metrics["paired_full_vs_unbound_post_mutation"],
                    "all_retained_outcome_error_fields_equal_original": True,
                    "differences_by_field": dict(sorted(changed.items())),
                    "cross_host_comparison_boundary": "Raw records retain contract verdicts and within-run determinism flags, not full numerical analytical reports. Cross-host numerical report identity is not established."},
        "engineering_preflight": {**totals, "passed": len(testcases) - len(skips),
                                  "junit_seconds": float(suite.get("time", "0")),
                                  "console_seconds": 66.56, "skipped_records": skips,
                                  "scope": "Full frozen tests/ invocation; optional build123d and gmsh coverage skipped. Three skipped entries are module collection skips."},
        "environment": {"python": manifest["python"], "platform": manifest["platform"],
                        "resource_receipt": manifest["resource_receipt"], "dependency_receipt": environment},
        "diagnostics": {"successful_evaluation_timing_ms": timing,
                        "receipt_size_bytes": {**metrics["report_size_bytes"], "conventional_median": statistics.median(sizes)},
                        "receipt_size_delta_from_original": {str(k): v for k, v in sorted(size_delta.items())},
                        "output_path_length_delta": len(ledger["output"]) - len(original_ledger["output"]),
                        "interpretation": "All 120 full receipts are 56 bytes shorter, consistent with the 56-character shorter retained project-output prefix and the source's embedded absolute project path. Binding hashes also include that path. No cross-host speed comparison is claimed.",
                        "median_convention": "Frozen median is the upper middle order statistic; conventional medians are separately labeled post-outcome diagnostics."},
        "claim_boundary": ["One internal cross-environment reproduction of known outcomes; not independent confirmation.",
                           "The original and reproduced matrices contain the same 216 cases; do not double the sample size.",
                           "Original terminal dispositions, ledgers, source and cases remain unchanged.",
                           "Original runner phase remains confirmatory; the wrapper declaration supplies the reproduction classification.",
                           "No physical measurements, intended-user study, independent language evaluation, or Kaggle result.",
                           "Hashes verify retained identity and consistency, not a cryptographic execution attestation."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--output", type=Path, help="Create a new report, refusing overwrite.")
    destination.add_argument("--check", type=Path, help="Validate an existing report without writing.")
    args = parser.parse_args()
    report = audit(args.root.resolve())
    content = pretty(report)
    if args.check:
        require(args.check.read_bytes() == content, "audit report differs from recomputed evidence")
        print("PASS: hosted reproduction audit regenerated byte-for-byte.")
    else:
        with args.output.open("xb") as stream:
            stream.write(content)
        print(f"PASS: wrote {args.output}")
    print("216 identical case verdict records; 13 matching endpoints; frozen tests 1203 passed, 9 skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
