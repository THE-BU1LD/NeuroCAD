"""Reproduce the frozen C3D pilot through the maintained CLI, preserving evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path


def hashes(directory: Path) -> dict[str, str]:
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*")) if path.is_file()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New evidence directory; existing paths are refused")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    output = args.output.expanduser().absolute()
    output.mkdir(parents=True, exist_ok=False)
    inputs = output / "editable-inputs"
    shutil.copytree(root / "docs/examples/c3d_revision", inputs)
    shutil.copyfile(root / "tests/fixtures/c3d_revision_integrity_v01.json", output / "frozen-contract.json")
    accepted, revised, rejected = output / "accepted-baseline", output / "accepted-revision", output / "rejected-40mm"
    commands: list[dict[str, object]] = []

    def run(name: str, arguments: list[str], expected: int) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-m", "neurocad_cli", *arguments]
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=120, check=False)
        (output / f"{name}.stdout.json").write_text(result.stdout, encoding="utf-8")
        (output / f"{name}.stderr.txt").write_text(result.stderr, encoding="utf-8")
        commands.append({"command": command, "returncode": result.returncode, "expected_returncode": expected})
        if result.returncode != expected:
            raise RuntimeError(f"{name} exited {result.returncode}; expected {expected}: {result.stderr}")
        return result

    run("baseline", ["feature", "build", str(inputs / "baseline.ncad2.json"),
        "--requirements", str(inputs / "baseline.requirements.json"),
        "--bindings", str(inputs / "baseline.bindings.json"), "--output-dir", str(accepted)], 0)
    before = hashes(accepted)

    def revise_arguments(candidate: str, destination: Path) -> list[str]:
        return ["feature", "revise", str(inputs / "baseline.ncad2.json"), str(inputs / f"{candidate}.ncad2.json"),
            "--baseline-bundle", str(accepted),
            "--baseline-requirements", str(inputs / "baseline.requirements.json"),
            "--baseline-bindings", str(inputs / "baseline.bindings.json"),
            "--candidate-requirements", str(inputs / f"{candidate}.requirements.json"),
            "--candidate-bindings", str(inputs / f"{candidate}.bindings.json"),
            "--output-dir", str(destination)]

    successful = run("revision", revise_arguments("candidate", revised), 0)
    run("infeasible", revise_arguments("infeasible", rejected), 2)
    after = hashes(accepted)
    receipt = json.loads(successful.stdout)
    evidence = receipt["revision_integrity"]["evidence"]
    # Reopen the persisted STEP independently after the CLI process has exited.
    from core.exact_build123d import Build123dBackend
    from core.feature_ir import parse_feature_ir_json
    from core.requirement_ir import parse_requirement_ir_json
    from core.requirement_verification import parse_binding_set_json, verify_exact_requirements

    backend = Build123dBackend()
    shape = backend.bd.import_step(revised / "design.step")
    inspection = backend.inspect(shape)
    bindings = parse_binding_set_json((revised / "requirement-bindings.json").read_text(encoding="utf-8"))
    requirements = parse_requirement_ir_json((revised / "requirements.json").read_text(encoding="utf-8"))
    program = parse_feature_ir_json((inputs / "candidate.ncad2.json").read_text(encoding="utf-8"))
    checks = verify_exact_requirements(requirements, program, inspection, bindings,
        exact_measurements_mm=backend._exact_requirement_measurements(shape, bindings))
    valid = (evidence["passed"] and before == after and not rejected.exists()
             and inspection.valid_brep and inspection.manifold and inspection.solid_count == 1
             and checks.satisfied_for_all_must)
    source_ref = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
    report = {
        "scope": "frozen C3D v0.1 planar wall-thickness revision",
        "passed": valid, "python": sys.version,
        "dependencies": {key: version(key) for key in ("build123d", "cadquery-ocp", "numpy", "trimesh", "jsonschema")},
        "source_commit": source_ref.stdout.strip() if source_ref.returncode == 0 else None,
        "source_sha256": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ("neurocad_cli.py", "core/exact_build123d.py", "core/requirement_verification.py",
                         "scripts/reproduce_c3d_revision.py", "tests/fixtures/c3d_revision_integrity_v01.json")
        },
        "commands": commands, "baseline_unchanged": before == after,
        "baseline_hashes": before, "infeasible_candidate_published": rejected.exists(),
        "step_reopened_inspection": inspection.to_dict(), "step_reopened_requirements": checks.to_dict(),
        "revision_evidence": evidence,
        "claim_boundary": "Bounded engineering evidence only; no general CAD, manufacturability, physical fit, or load-capacity certification.",
    }
    (output / "verification-report.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    (output / "SHA256SUMS.json").write_text(json.dumps(hashes(output), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not valid:
        raise RuntimeError("pilot acceptance failed; evidence retained")
    print(json.dumps({"passed": valid, "output": str(output), "candidate_wall_thickness_mm": evidence["candidate_wall_thickness_mm"]}))


if __name__ == "__main__":
    main()
