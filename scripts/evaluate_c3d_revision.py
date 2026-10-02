"""Run the frozen constructed C3D regression suite and retain every outcome.

Fixed Python module commands use separate argv entries without a shell.
This evaluates a bounded verifier, not a trained model or external CAD designs.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess  # nosec B404
import sys
from importlib.metadata import distributions, version
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.feature_ir import parse_feature_ir_json
from core.json_io import strict_json_loads
from core.requirement_ir import parse_requirement_ir_json
from core.requirement_verification import feature_ir_sha256, requirement_ir_sha256

EXAMPLES = ROOT / "docs/examples/c3d_revision"
MUTATIONS = {"none", "move_cutout", "resize_cutout", "remove_cutout", "change_width",
             "change_height", "change_depth", "wrong_wall_requirement",
             "change_frozen_requirement", "stale_binding"}


def read_json(path: Path) -> Any:
    return strict_json_loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def hashes(directory: Path) -> dict[str, str]:
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob("*")) if p.is_file()}


def dependency_versions() -> dict[str, str]:
    result = {name: version(name) for name in ("build123d", "jsonschema", "numpy", "trimesh")}
    # OCP ships under the original name or split proxy/novtk distributions.
    for distribution in distributions():
        name = distribution.metadata["Name"] or ""
        if name.lower().replace("_", "-").startswith("cadquery-ocp"):
            result[name] = distribution.version
    return result


def candidate_inputs(case: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    program = copy.deepcopy(read_json(EXAMPLES / "candidate.ncad2.json"))
    requirements = copy.deepcopy(read_json(EXAMPLES / "candidate.requirements.json"))
    bindings = copy.deepcopy(read_json(EXAMPLES / "candidate.bindings.json"))
    wall = case["wall_mm"]
    program["parameters"][0]["value"] = wall
    entities = program["features"][0]["parameters"]["entities"]
    entities[1]["width"], entities[1]["height"] = 80 - 2 * wall, 60 - 2 * wall
    mutation = case["mutation"]
    if mutation == "move_cutout":
        entities[2]["center"][1] = 11.0
    elif mutation == "resize_cutout":
        entities[2]["radius"] = 0.5
    elif mutation == "remove_cutout":
        entities.pop()
    elif mutation == "change_width":
        entities[0]["width"] = 81.0
    elif mutation == "change_height":
        entities[0]["height"] = 61.0
    elif mutation == "change_depth":
        program["features"][1]["parameters"]["distance"] = 21.0
    requested_wall = 4.0 if mutation == "wrong_wall_requirement" else wall
    wall_text = f"{requested_wall:g} mm"
    requirements["source"] = f"Keep width exactly 80 mm and set wall thickness to {wall_text}."
    wall_requirement = requirements["requirements"][1]
    wall_requirement["source_text"] = wall_text
    wall_requirement["source_end"] = wall_requirement["source_start"] + len(wall_text)
    wall_requirement["value"]["value"] = requested_wall
    if mutation == "change_frozen_requirement":
        # Same source width with a relaxed tolerance is an unauthorized contract edit.
        requirements["requirements"][0]["value"]["tolerance"] = 1.0
    bindings["requirement_ir_sha256"] = requirement_ir_sha256(
        parse_requirement_ir_json(json.dumps(requirements)))
    if wall < 30:
        bindings["feature_ir_sha256"] = feature_ir_sha256(parse_feature_ir_json(json.dumps(program)))
    # Impossible dimensions remain raw negative-test intent, never accepted IR.
    if mutation == "stale_binding":
        bindings["feature_ir_sha256"] = "0" * 64
    return program, requirements, bindings


def rejection_matches(returncode: int, stderr: str, tokens: list[str], published: bool) -> bool:
    return returncode == 2 and not published and any(token in stderr for token in tokens)


def command(output: Path, name: str, module: str, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    argv = [sys.executable, "-m", module, *arguments]
    # Current interpreter and fixed modules; paths are data, never shell syntax.
    try:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=180, check=False)  # nosec B603
    except subprocess.TimeoutExpired as exc:
        # Timeout output may be bytes even with text=True; retain it as evidence.
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout or ""
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr or ""
        result = subprocess.CompletedProcess(argv, 124, stdout, stderr + "\nERROR: execution timeout; command not completed")
    (output / f"{name}.stdout.txt").write_text(result.stdout, encoding="utf-8")
    (output / f"{name}.stderr.txt").write_text(result.stderr, encoding="utf-8")
    write_json(output / f"{name}.execution.json", {"argv": argv, "returncode": result.returncode})
    return result


def reopened_checks(bundle: Path, program_path: Path) -> dict[str, Any]:
    from core.exact_build123d import Build123dBackend
    from core.requirement_verification import parse_binding_set_json, verify_exact_requirements

    backend = Build123dBackend()
    shape = backend.bd.import_step(bundle / "design.step")
    inspection = backend.inspect(shape)
    program = parse_feature_ir_json(program_path.read_text(encoding="utf-8"))
    requirements = parse_requirement_ir_json((bundle / "requirements.json").read_text(encoding="utf-8"))
    bindings = parse_binding_set_json((bundle / "requirement-bindings.json").read_text(encoding="utf-8"))
    checks = verify_exact_requirements(requirements, program, inspection, bindings,
        exact_measurements_mm=backend._exact_requirement_measurements(shape, bindings))
    return {"inspection": inspection.to_dict(), "requirements": checks.to_dict(),
            "passed": inspection.valid_brep and inspection.manifold and inspection.solid_count == 1
                      and checks.satisfied_for_all_must}


def evaluate(output: Path, *, mesh: bool = False) -> dict[str, Any]:
    from core.exact_backend import require_exact_backend

    require_exact_backend("build123d")
    manifest_path = EXAMPLES / "evaluation-v1.json"
    manifest = read_json(manifest_path)
    output.mkdir(parents=True, exist_ok=False)
    (output / "frozen-evaluation.json").write_bytes(manifest_path.read_bytes())
    baseline_inputs = output / "baseline-inputs"
    baseline_inputs.mkdir()
    for suffix in ("ncad2.json", "requirements.json", "bindings.json"):
        name = f"baseline.{suffix}"
        (baseline_inputs / name).write_bytes((EXAMPLES / name).read_bytes())
    baseline = output / "accepted-baseline"
    built = command(output, "baseline", "neurocad_cli", ["feature", "build",
        str(EXAMPLES / "baseline.ncad2.json"), "--requirements", str(EXAMPLES / "baseline.requirements.json"),
        "--bindings", str(EXAMPLES / "baseline.bindings.json"), "--output-dir", str(baseline)])
    if built.returncode:
        raise RuntimeError(f"Baseline construction failed; no evaluation score: {built.stderr}")
    original = hashes(baseline)
    results = []
    for case in manifest["cases"]:
        if case["mutation"] not in MUTATIONS:
            raise ValueError("Frozen manifest contains an unsupported mutation")
        workspace = output / case["id"]
        workspace.mkdir()
        for name, payload in zip(("candidate.ncad2.json", "requirements.json", "bindings.json"),
                                 candidate_inputs(case), strict=True):
            write_json(workspace / name, payload)
        destination = workspace / "accepted-revision"
        result = command(workspace, "revision", "neurocad_cli", ["feature", "revise",
            str(EXAMPLES / "baseline.ncad2.json"), str(workspace / "candidate.ncad2.json"),
            "--baseline-bundle", str(baseline), "--baseline-requirements", str(EXAMPLES / "baseline.requirements.json"),
            "--baseline-bindings", str(EXAMPLES / "baseline.bindings.json"),
            "--candidate-requirements", str(workspace / "requirements.json"),
            "--candidate-bindings", str(workspace / "bindings.json"), "--output-dir", str(destination)])
        published = destination.exists()
        unchanged = hashes(baseline) == original
        row: dict[str, Any] = {**case, "returncode": result.returncode, "published": published,
                               "baseline_unchanged": unchanged, "error": result.stderr.strip()}
        if case["expected_accept"]:
            passed = result.returncode == 0 and published
            if passed:
                row["reopened_step"] = reopened_checks(destination, workspace / "candidate.ncad2.json")
                row["revision_integrity"] = read_json(destination / "revision-integrity.json")
                passed = row["reopened_step"]["passed"] and row["revision_integrity"]["evidence"]["passed"]
        else:
            passed = rejection_matches(result.returncode, result.stderr, case["error_tokens"], published)
        row["passed"] = bool(passed and unchanged)
        results.append(row)
        write_json(workspace / "result.json", row)
    mesh_result: dict[str, Any] = {"requested": mesh, "status": "not_run", "passed": None}
    if mesh:
        source = output / "wall_3p0mm/accepted-revision/design.step"
        mesh_run = command(output, "mesh", "core.mesh_cli", ["step", str(source),
            "--max-size", "3", "--min-size", "0.5", "--output-dir", str(output / "mesh-bundle")])
        mesh_result = {"requested": True, "status": "passed" if mesh_run.returncode == 0 else "failed",
                       "passed": mesh_run.returncode == 0, "returncode": mesh_run.returncode,
                       "error": mesh_run.stderr.strip()}
        if mesh_run.returncode == 0:
            mesh_result["receipt"] = read_json(output / "mesh-bundle/meshing-receipt.json")
            mesh_result["execution"] = read_json(output / "mesh-bundle/execution-receipt.json")
            mesh_result["passed"] = (
                mesh_result["receipt"]["source_step_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
                and mesh_result["receipt"]["mesh_sha256"] == hashlib.sha256(
                    (output / "mesh-bundle/design.msh").read_bytes()).hexdigest()
                and mesh_result["execution"]["status"] == "success"
            )
            mesh_result["status"] = "passed" if mesh_result["passed"] else "failed"
    report = {"version": manifest["version"], "scope": manifest["scope"],
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                          for name in ("scripts/evaluate_c3d_revision.py", "neurocad_cli.py", "core/exact_build123d.py",
                                       "core/requirement_verification.py", "tests/fixtures/c3d_revision_integrity_v01.json")},
        "dependencies": dependency_versions(),
        "case_count": len(results), "passed_count": sum(row["passed"] for row in results),
        "expected_accept_count": sum(row["expected_accept"] for row in results),
        "expected_reject_count": sum(not row["expected_accept"] for row in results),
        "baseline_unchanged": hashes(baseline) == original, "cases": results, "meshing": mesh_result,
        "passed": all(row["passed"] for row in results) and (not mesh or mesh_result["passed"] is True),
        "claim_boundary": "Constructed verifier regression only; no learned-model generalization, Cubit integration, manufacturing, physics or safety certification."}
    write_json(output / "evaluation-report.json", report)
    write_json(output / "SHA256SUMS.json", hashes(output))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New evidence directory")
    parser.add_argument("--mesh", action="store_true", help="Also require a separate real Gmsh mesh result")
    args = parser.parse_args()
    report = evaluate(args.output.expanduser().absolute(), mesh=args.mesh)
    print(json.dumps({"passed": report["passed"], "cases": report["case_count"],
                      "passed_count": report["passed_count"], "meshing": report["meshing"]["status"]}))
    raise SystemExit(0 if report["passed"] else 2)


if __name__ == "__main__":
    main()
