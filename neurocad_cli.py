from __future__ import annotations

import argparse
import importlib
import json
import platform
import sys
import tempfile
from pathlib import Path

from core.artifacts import (
    compile_scad,
    compile_scad_verified,
    design_manifest,
    find_openscad,
    verify_stl,
    write_manifest,
    write_text_atomic,
)
from core.benchmark import generate_benchmark, run_benchmark, save_benchmark_results, write_benchmark
from core.ir import CADProgram, program_bounds, program_bounds_are_exact
from core.ir_export import program_to_scad
from core.ir_parser import parse_ir_json, serialize_ir_json
from core.program_evaluation import evaluate_program
from text_to_cad import TextToCAD

__version__ = "0.5.0a6"
MAX_IR_INPUT_BYTES = 1_048_576


def _program_extents(program: CADProgram) -> list[float] | None:
    if not program_bounds_are_exact(program):
        return None
    lower, upper = program_bounds(program)
    return [upper[index] - lower[index] for index in range(3)]


def _resolved_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _paths_collide(left: Path, right: Path) -> bool:
    if left == right:
        return True
    try:
        return left.exists() and right.exists() and left.samefile(right)
    except OSError:
        return False


def _require_distinct_paths(**paths: Path | None) -> None:
    present = [(name, path) for name, path in paths.items() if path is not None]
    for index, (left_name, left) in enumerate(present):
        for right_name, right in present[index + 1 :]:
            if _paths_collide(left, right):
                raise ValueError(f"artifact paths must be distinct: {left_name} and {right_name} both resolve to {left}")


def _require_new_path(path: Path, *, label: str) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"{label} already exists; choose a new path: {path}")


def _require_new_paths(*, force: bool, **paths: Path | None) -> None:
    if force:
        return
    for label, path in paths.items():
        if path is not None:
            _require_new_path(path, label=label.replace("_", " "))


def _prompt(parts: list[str]) -> str:
    value = " ".join(parts).strip()
    if not value:
        raise SystemExit("A non-empty engineering prompt is required.")
    if len(value) > 4096:
        raise SystemExit("Engineering prompts are limited to 4096 characters.")
    return value


def _fn(value: str) -> int:
    parsed = int(value)
    if not 3 <= parsed <= 1000:
        raise argparse.ArgumentTypeError("fn must be between 3 and 1000")
    return parsed


def _positive_timeout(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("timeout must be a positive number of seconds")
    return parsed


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def _show_errors(errors: list[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)


def cmd_doctor(_: argparse.Namespace) -> int:
    checks: list[tuple[str, bool, str]] = []
    checks.append(("python>=3.10", sys.version_info >= (3, 10), platform.python_version()))
    for package in ("numpy", "trimesh"):
        try:
            module = importlib.import_module(package)
            version = getattr(module, "__version__", "installed")
            checks.append((package, True, str(version)))
        except ImportError as exc:
            checks.append((package, False, str(exc)))

    try:
        generator = TextToCAD()
        doc = generator.build("a 120 x 80 x 4 mm plate with four 4 mm holes")
        scad = doc.scad
        checks.append(("generation-smoke", bool(scad.strip()), f"{len(scad)} chars"))
        checks.append(("semantic-validation", doc.validation.valid, "; ".join(doc.validation.errors) or "valid"))
    except Exception as exc:  # noqa: BLE001 - doctor must report a broken installation instead of crashing
        checks.append(("generation-smoke", False, str(exc)))

    failed = False
    for name, ok, detail in checks:
        state = "OK" if ok else "FAIL"
        print(f"[{state}] {name}: {detail}")
        failed = failed or not ok
    print(f"[INFO] openscad: {find_openscad() or 'not installed (required only for STL/compiled validation)'}")
    return 1 if failed else 0


def _build(prompt_parts: list[str], fn: int):
    prompt = _prompt(prompt_parts)
    doc = TextToCAD(fn=fn).build(prompt)
    if not doc.validation.valid:
        _show_errors(doc.validation.errors)
        raise SystemExit(2)
    doc.require_program()
    for warning in doc.validation.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    return doc


def _generate(prompt_parts: list[str], output: Path, fn: int):
    doc = _build(prompt_parts, fn)
    path = output
    TextToCAD(output_path=str(path), fn=fn).export(doc.prompt)
    if not path.exists() or path.stat().st_size == 0:
        raise SystemExit("NeuroCAD generated an empty output file.")
    return path, doc


def cmd_create(args: argparse.Namespace) -> int:
    output = _resolved_path(args.output)
    manifest = _resolved_path(args.manifest) if args.manifest else None
    _require_distinct_paths(output=output, manifest=manifest)
    _require_new_paths(force=args.force, output=output, manifest=manifest)
    path, doc = _generate(args.prompt, output, args.fn)
    if manifest is not None:
        write_manifest(manifest, doc.design, doc.validation, doc.program, doc.ir_validation)
    print(path)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    doc = _build(args.prompt, args.fn)
    path = _resolved_path(args.output or f"generated.{args.format}")
    manifest = _resolved_path(args.manifest) if args.manifest else None
    _require_distinct_paths(output=path, manifest=manifest)
    _require_new_paths(force=args.force, output=path, manifest=manifest)
    if args.format == "scad":
        TextToCAD(output_path=str(path), fn=args.fn).export(doc.prompt)
    elif args.format == "json":
        write_manifest(path, doc.design, doc.validation, doc.program, doc.ir_validation)
    else:
        with tempfile.TemporaryDirectory(prefix="neurocad-") as temporary:
            source = Path(temporary) / "design.scad"
            TextToCAD(output_path=str(source), fn=args.fn).export(doc.prompt)
            _, verification = compile_scad_verified(
                source,
                path,
                timeout=args.timeout,
                expected_extents_mm=_program_extents(doc.require_program()),
            )
        print(json.dumps({"mesh_verification": verification}, sort_keys=True), file=sys.stderr)
    if manifest is not None:
        write_manifest(manifest, doc.design, doc.validation, doc.program, doc.ir_validation)
    print(path)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    prompt = _prompt(args.prompt)
    doc = TextToCAD(fn=args.fn).build(prompt)
    if args.compile and doc.validation.valid:
        try:
            with tempfile.TemporaryDirectory(prefix="neurocad-validate-") as temporary:
                source = Path(temporary) / "design.scad"
                mesh = Path(temporary) / "design.stl"
                TextToCAD(output_path=str(source), fn=args.fn).export(prompt)
                compile_scad(source, mesh, timeout=args.timeout)
                verification = verify_stl(mesh, expected_extents_mm=_program_extents(doc.require_program()))
        except RuntimeError as exc:
            doc.validation.error(f"compiled validation failed: {exc}")
        else:
            doc.design.metadata["mesh_verification"] = verification
    if args.json:
        print(json.dumps(design_manifest(doc.design, doc.validation, doc.program, doc.ir_validation), indent=2, sort_keys=True))
    elif not doc.validation.valid:
        print("INVALID", file=sys.stderr)
        _show_errors(doc.validation.errors)
    else:
        for warning in doc.validation.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        print("VALID")
    if not doc.validation.valid:
        return 1
    return 0


def cmd_ir(args: argparse.Namespace) -> int:
    doc = _build(args.prompt, args.fn)
    output = _resolved_path(args.output)
    _require_new_paths(force=args.force, output=output)
    write_text_atomic(output, serialize_ir_json(doc.require_program()))
    print(output)
    return 0


def _read_structured_input(value: str) -> str:
    if value == "-":
        if hasattr(sys.stdin, "buffer"):
            raw = sys.stdin.buffer.read(MAX_IR_INPUT_BYTES + 1)
        else:
            raw = sys.stdin.read(MAX_IR_INPUT_BYTES + 1).encode("utf-8")
    else:
        with Path(value).expanduser().resolve().open("rb") as handle:
            raw = handle.read(MAX_IR_INPUT_BYTES + 1)
    if len(raw) > MAX_IR_INPUT_BYTES:
        raise ValueError("canonical IR input is limited to 1 MiB")
    return raw.decode("utf-8")


def cmd_compile(args: argparse.Namespace) -> int:
    output = _resolved_path(args.output or f"compiled.{args.format}")
    input_path = None if args.input == "-" else _resolved_path(args.input)
    _require_distinct_paths(input=input_path, output=output)
    _require_new_paths(force=args.force, output=output)
    program = parse_ir_json(_read_structured_input(args.input))
    if args.format == "json":
        write_text_atomic(output, serialize_ir_json(program))
    elif args.format == "scad":
        write_text_atomic(output, program_to_scad(program, fn=args.fn))
    else:
        with tempfile.TemporaryDirectory(prefix="neurocad-compile-") as temporary:
            source = Path(temporary) / "program.scad"
            write_text_atomic(source, program_to_scad(program, fn=args.fn))
            _, verification = compile_scad_verified(
                source,
                output,
                timeout=args.timeout,
                expected_extents_mm=_program_extents(program),
            )
        print(json.dumps({"mesh_verification": verification}, sort_keys=True), file=sys.stderr)
    print(output)
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    if args.ir:
        program = parse_ir_json(_read_structured_input(args.ir))
    else:
        program = _build(args.prompt, args.fn).require_program()
    print(json.dumps(evaluate_program(program).to_dict(), indent=2, sort_keys=True))
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    dataset = _resolved_path(args.dataset)
    output = _resolved_path(args.output)
    _require_distinct_paths(dataset=dataset, results=output)
    _require_new_paths(force=args.force, dataset=dataset, results=output)
    tasks = generate_benchmark(seed=args.seed)
    write_benchmark(dataset, tasks)
    results = run_benchmark(tasks, seed=args.seed)
    save_benchmark_results(output, results)
    print(json.dumps({"dataset": str(dataset), "results": str(output), "task_count": len(tasks)}, sort_keys=True))
    return 0


def cmd_research(args: argparse.Namespace) -> int:
    from core.research_suite import ResearchConfig, run_research_suite

    config = ResearchConfig(
        seed=args.seed,
        compiler_tasks=args.compiler_tasks,
        ir_programs=args.ir_programs,
        invalid_cases=args.invalid_cases,
        edit_cases=args.edit_cases,
        constraint_ablation_cases=args.constraint_ablation_cases,
        kernel_samples=args.kernel_samples,
        fn=args.fn,
        openscad_timeout_seconds=args.timeout,
    )
    output = _resolved_path(args.output)
    results = run_research_suite(output, config, require_kernel=args.require_kernel, run_id=args.run_id)
    kernel = results["experiments"]["NC-EXP-006"]
    print(
        json.dumps(
            {
                "output": str(output),
                "run_id": results["run_id"],
                "kernel_status": kernel["status"],
                "results": str(output / "metrics" / "results.json"),
            },
            sort_keys=True,
        )
    )
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    from core.demo_server import serve_demo

    serve_demo(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
        allow_remote=args.allow_remote,
    )
    return 0


def cmd_enclosure_interpret(args: argparse.Namespace) -> int:
    from core.natural_language import interpret_enclosure
    from core.project import write_project
    from core.workflow import project_from_interpretation

    source = _prompt(args.prompt)
    interpretation = interpret_enclosure(source)
    output = _resolved_path(args.output) if args.output else None
    project_output = _resolved_path(args.project_output) if args.project_output else None
    _require_distinct_paths(interpretation=output, project=project_output)
    if output is not None:
        _require_new_path(output, label="interpretation output")
    if project_output is not None:
        _require_new_path(project_output, label="project output")
    project = project_from_interpretation(args.project_id, interpretation) if interpretation.ready and project_output is not None else None
    encoded = json.dumps(interpretation.to_dict(), indent=2, sort_keys=True) + "\n"
    if output is None:
        print(encoded, end="")
    else:
        write_text_atomic(output, encoded)
        print(output)
    if project is not None and project_output is not None:
        write_project(project_output, project)
        print(project_output)
    elif project_output is not None:
        _show_errors([issue.message for issue in interpretation.issues])
    return 0 if interpretation.ready else 2


def cmd_enclosure_build(args: argparse.Namespace) -> int:
    from core.project import read_project
    from core.workflow import build_project_bundle

    project_path = _resolved_path(args.project)
    output = _resolved_path(args.output_dir)
    if project_path == output or project_path in output.parents:
        raise ValueError("output bundle must not contain or replace the source project")
    project = read_project(project_path)
    bundle = build_project_bundle(
        project,
        output,
        compile_stl=args.stl,
        fn=args.fn,
        timeout=args.timeout,
    )
    print(json.dumps(bundle.manifest, indent=2, sort_keys=True))
    return 0


def cmd_enclosure_verify(args: argparse.Namespace) -> int:
    from core.workflow import verify_project_bundle

    report = verify_project_bundle(_resolved_path(args.bundle))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def cmd_enclosure_preflight(args: argparse.Namespace) -> int:
    from core.manufacturing import fabrication_preflight
    from core.project import read_project

    project = read_project(_resolved_path(args.project))
    calibration_profile = _read_calibration_profile(args.calibration) if args.calibration else None
    report = fabrication_preflight(
        project.spec,
        density_g_cm3=args.density,
        material_cost_per_kg=args.material_cost,
        calibration_profile=calibration_profile,
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.valid else 2


def cmd_enclosure_edit(args: argparse.Namespace) -> int:
    from core.edit_language import edit_project_from_text
    from core.json_io import strict_json_loads
    from core.project import read_project, semantic_diff, update_project, write_project

    source = _resolved_path(args.project)
    output = _resolved_path(args.output)
    _require_distinct_paths(input=source, output=output)
    _require_new_path(output, label="project revision")
    project = read_project(source)
    if args.instruction is not None:
        if args.value is not None:
            raise ValueError("--value cannot be combined with --instruction")
        edited = edit_project_from_text(project, args.instruction, reason=args.reason)
    else:
        if args.value is None:
            raise ValueError("--value is required with --field")
        if args.reason is None:
            raise ValueError("--reason is required with --field")
        if len(args.value.encode("utf-8")) > 65_536:
            raise ValueError("edit value is limited to 64 KiB")
        value = strict_json_loads(args.value)
        edited = update_project(project, args.field, value, reason=args.reason)
    write_project(output, edited)
    print(json.dumps({"output": str(output), "revision": edited.revision, "changes": semantic_diff(project, edited)}, indent=2))
    return 0


def cmd_calibration_fit(args: argparse.Namespace) -> int:
    from core.calibration import (
        MAX_CALIBRATION_JSON_BYTES,
        fit_calibration_profile,
        parse_calibration_dataset,
        serialize_calibration_profile,
    )

    source = _resolved_path(args.dataset)
    output = _resolved_path(args.output)
    _require_distinct_paths(input=source, output=output)
    _require_new_path(output, label="calibration profile")
    raw = source.read_bytes()
    if len(raw) > MAX_CALIBRATION_JSON_BYTES:
        raise ValueError("calibration dataset exceeds the 1 MiB input limit")
    dataset = parse_calibration_dataset(raw.decode("utf-8"))
    profile = fit_calibration_profile(dataset)
    write_text_atomic(output, serialize_calibration_profile(profile) + "\n")
    print(output)
    return 0


def cmd_calibration_inspect(args: argparse.Namespace) -> int:
    from core.calibration import MAX_CALIBRATION_JSON_BYTES, parse_calibration_profile

    source = _resolved_path(args.profile)
    raw = source.read_bytes()
    if len(raw) > MAX_CALIBRATION_JSON_BYTES:
        raise ValueError("calibration profile exceeds the 1 MiB input limit")
    profile = parse_calibration_profile(raw.decode("utf-8"))
    print(json.dumps(profile.to_dict(), indent=2, sort_keys=True, allow_nan=False))
    return 0


def _read_calibration_profile(path_value: str):
    from core.calibration import MAX_CALIBRATION_JSON_BYTES, parse_calibration_profile

    source = _resolved_path(path_value)
    raw = source.read_bytes()
    if len(raw) > MAX_CALIBRATION_JSON_BYTES:
        raise ValueError("calibration profile exceeds the 1 MiB input limit")
    return parse_calibration_profile(raw.decode("utf-8"))


def cmd_calibration_plan(args: argparse.Namespace) -> int:
    from core.calibration import plan_calibration_application
    from core.project import read_project

    project = read_project(_resolved_path(args.project))
    profile = _read_calibration_profile(args.profile)
    plan = plan_calibration_application(project, profile)
    print(json.dumps(plan.to_dict(), indent=2, sort_keys=True, allow_nan=False))
    return 0


def cmd_calibration_apply_clearance(args: argparse.Namespace) -> int:
    from core.calibration import apply_calibrated_clearance
    from core.project import read_project, semantic_diff, write_project

    source = _resolved_path(args.project)
    profile_path = _resolved_path(args.profile)
    output = _resolved_path(args.output)
    _require_distinct_paths(project=source, profile=profile_path, output=output)
    _require_new_path(output, label="project revision")
    project = read_project(source)
    profile = _read_calibration_profile(str(profile_path))
    edited = apply_calibrated_clearance(project, profile, reason=args.reason)
    write_project(output, edited)
    print(
        json.dumps(
            {
                "output": str(output),
                "revision": edited.revision,
                "changes": semantic_diff(project, edited),
                "calibration_profile_id": profile.dataset.profile_id,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def cmd_integrations_list(args: argparse.Namespace) -> int:
    from core.integrations import default_registry

    registry = default_registry()
    selected = tuple(args.application) if args.application else None
    payload = {
        "applications": [adapter.to_dict() for adapter in registry.describe(selected)],
        "external_operation_performed": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_integrations_export(args: argparse.Namespace) -> int:
    from core.enclosure import build_enclosure
    from core.integrations import export_openscad_bundle, write_neutral_manifest
    from core.project import read_project

    project_path = _resolved_path(args.project)
    destination = _resolved_path(args.output_dir)
    manifest_path = _resolved_path(args.manifest) if args.manifest else None
    _require_distinct_paths(project=project_path, destination=destination, manifest=manifest_path)
    if manifest_path is not None:
        _require_new_path(manifest_path, label="neutral manifest")
    if manifest_path is not None and (manifest_path == destination or destination in manifest_path.parents):
        raise ValueError("the neutral manifest must be outside the new exchange bundle")
    project = read_project(project_path)
    build = build_enclosure(project.spec)
    bundle = export_openscad_bundle(
        build,
        destination,
        fn=args.fn,
        compile_meshes=args.stl,
        timeout=args.timeout,
    )
    if manifest_path is not None:
        write_neutral_manifest(manifest_path, build, bundle=bundle, targets=args.application)
    print(json.dumps(bundle.manifest, indent=2, sort_keys=True))
    return 0


def _read_exchange_bundle(directory_value: str):
    from core.integrations import ExchangeBundle
    from core.json_io import strict_json_loads

    root = _resolved_path(directory_value)
    manifest_path = root / "manifest.json"
    raw = manifest_path.read_bytes()
    if len(raw) > MAX_IR_INPUT_BYTES:
        raise ValueError("exchange manifest exceeds the 1 MiB input limit")
    manifest = strict_json_loads(raw.decode("utf-8"))
    if not isinstance(manifest, dict):
        raise TypeError("exchange manifest must be a JSON object")
    return ExchangeBundle(root=root, manifest_path=manifest_path, manifest=manifest)


def cmd_integrations_handoff(args: argparse.Namespace) -> int:
    from core.integrations import write_application_handoff

    bundle = _read_exchange_bundle(args.bundle)
    output = _resolved_path(args.output)
    _require_distinct_paths(bundle=bundle.root, manifest=bundle.manifest_path, output=output)
    _require_new_path(output, label="handoff receipt")
    write_application_handoff(output, args.application, bundle)
    print(output)
    return 0


def cmd_integrations_verify(args: argparse.Namespace) -> int:
    from core.integrations import verify_exchange_bundle

    bundle = _read_exchange_bundle(args.bundle)
    report = verify_exchange_bundle(bundle)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def cmd_integrations_kicad_request(args: argparse.Namespace) -> int:
    from core.integrations import write_kicad_extraction_request

    board = _resolved_path(args.board)
    output = _resolved_path(args.output)
    _require_distinct_paths(board=board, output=output)
    _require_new_path(output, label="KiCad extraction request")
    write_kicad_extraction_request(output, board)
    print(output)
    return 0


def cmd_integrations_kicad_extract(args: argparse.Namespace) -> int:
    from core.integrations import write_kicad_file_receipt

    board = _resolved_path(args.board)
    review = _resolved_path(args.review)
    output = _resolved_path(args.output)
    _require_distinct_paths(board=board, review=review, output=output)
    _require_new_path(output, label="KiCad extraction receipt")
    write_kicad_file_receipt(output, board, review)
    print(output)
    return 0


def cmd_integrations_kicad_bind(args: argparse.Namespace) -> int:
    from core.integrations import write_bound_kicad_extraction

    draft = _resolved_path(args.draft)
    source_board = _resolved_path(args.source_board)
    output = _resolved_path(args.output)
    _require_distinct_paths(draft=draft, source_board=source_board, output=output)
    _require_new_path(output, label="bound KiCad receipt")
    write_bound_kicad_extraction(output, draft, source_board)
    print(output)
    return 0


def cmd_integrations_kicad_inspect(args: argparse.Namespace) -> int:
    from core.integrations import read_kicad_handoff

    receipt = _resolved_path(args.receipt)
    source_board = _resolved_path(args.source_board)
    _require_distinct_paths(receipt=receipt, source_board=source_board)
    board = read_kicad_handoff(receipt, source_board=source_board)
    pcb = board.to_pcb_spec()
    payload = {
        "board": board.to_dict(),
        "pcb_spec": {
            "size_mm": list(pcb.size_mm),
            "origin_xy_mm": list(pcb.origin_xy_mm),
            "mounting_holes_xy_mm": [list(position) for position in pcb.mounting_holes_xy_mm],
            "component_height_mm": pcb.component_height_mm,
        },
        "source_hash_verified": board.source_hash_verified,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_integrations_kicad_apply(args: argparse.Namespace) -> int:
    from core.integrations import apply_kicad_board_to_project, read_kicad_handoff
    from core.project import read_project, write_project

    project_path = _resolved_path(args.project)
    receipt = _resolved_path(args.receipt)
    source_board = _resolved_path(args.source_board)
    output = _resolved_path(args.output)
    _require_distinct_paths(
        project=project_path,
        receipt=receipt,
        source_board=source_board,
        output=output,
    )
    _require_new_path(output, label="revised project")
    project = read_project(project_path)
    board = read_kicad_handoff(receipt, source_board=source_board)
    application = apply_kicad_board_to_project(project, board, reason=args.reason)
    write_project(output, application.project)
    payload = application.to_dict()
    payload["output"] = str(output)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neurocad",
        description="Strict dimensioned prompts to validated millimetre-based OpenSCAD geometry.",
    )
    parser.add_argument("--version", action="version", version=f"NeuroCAD {__version__}")
    sub = parser.add_subparsers(dest="command")

    doctor = sub.add_parser("doctor", help="Check the local NeuroCAD installation")
    doctor.set_defaults(func=cmd_doctor)

    create = sub.add_parser("create", help="Generate OpenSCAD from an engineering prompt")
    create.add_argument("prompt", nargs="+", help="Engineering prompt")
    create.add_argument("-o", "--output", default="generated.scad", help="New SCAD path; existing files are refused")
    create.add_argument("--fn", type=_fn, default=96)
    create.add_argument("--manifest", help="Also write a JSON design/validation manifest")
    create.add_argument("--force", action="store_true", help="Explicitly replace existing output and manifest files")
    create.set_defaults(func=cmd_create)

    validate = sub.add_parser("validate", help="Parse and validate that a prompt produces a design")
    validate.add_argument("prompt", nargs="+", help="Engineering prompt")
    validate.add_argument("--fn", type=_fn, default=96)
    validate.add_argument("--compile", action="store_true", help="Compile and verify a watertight STL with OpenSCAD")
    validate.add_argument("--timeout", type=_positive_timeout, default=120, help="OpenSCAD timeout in seconds")
    validate.add_argument("--json", action="store_true", help="Print the design and validation manifest as JSON")
    validate.set_defaults(func=cmd_validate)

    export = sub.add_parser("export", help="Export generated geometry")
    export.add_argument("prompt", nargs="+", help="Engineering prompt")
    export.add_argument("-o", "--output", help="New artifact path; existing files are refused")
    export.add_argument("--format", choices=["scad", "stl", "json"], default="scad")
    export.add_argument("--fn", type=_fn, default=96)
    export.add_argument("--timeout", type=_positive_timeout, default=120, help="OpenSCAD timeout in seconds")
    export.add_argument("--manifest", help="Also write a JSON design/validation manifest")
    export.add_argument("--force", action="store_true", help="Explicitly replace existing output and manifest files")
    export.set_defaults(func=cmd_export)

    ir_parser = sub.add_parser("ir", help="Parse a supported prompt and emit canonical NeuroCAD IR JSON")
    ir_parser.add_argument("prompt", nargs="+", help="Engineering prompt")
    ir_parser.add_argument("-o", "--output", default="program.ncad.json", help="New IR path; existing files are refused")
    ir_parser.add_argument("--fn", type=_fn, default=96)
    ir_parser.add_argument("--force", action="store_true", help="Explicitly replace an existing output file")
    ir_parser.set_defaults(func=cmd_ir)

    compile_parser = sub.add_parser("compile", help="Validate and compile canonical NeuroCAD IR JSON")
    compile_parser.add_argument("input", help="IR JSON file, or - for stdin")
    compile_parser.add_argument("-o", "--output", help="New artifact path; existing files are refused")
    compile_parser.add_argument("--format", choices=["json", "scad", "stl"], default="scad")
    compile_parser.add_argument("--fn", type=_fn, default=96)
    compile_parser.add_argument("--timeout", type=_positive_timeout, default=120)
    compile_parser.add_argument("--force", action="store_true", help="Explicitly replace an existing output file")
    compile_parser.set_defaults(func=cmd_compile)

    evaluate_parser = sub.add_parser("evaluate", help="Measure a prompt or canonical IR program")
    evaluate_source = evaluate_parser.add_mutually_exclusive_group(required=True)
    evaluate_source.add_argument("--ir", help="Canonical IR JSON file, or - for stdin")
    evaluate_source.add_argument("--prompt", nargs="+", help="Supported engineering prompt")
    evaluate_parser.add_argument("--fn", type=_fn, default=96)
    evaluate_parser.set_defaults(func=cmd_evaluate)

    benchmark_parser = sub.add_parser("benchmark", help="Generate and run the deterministic engineering benchmark")
    benchmark_parser.add_argument("--seed", type=int, default=20260902)
    benchmark_parser.add_argument("--dataset", default="research/benchmarks/neurocad_benchmark_v1.jsonl")
    benchmark_parser.add_argument("--output", default="research/results/neurocad_benchmark_v1.json")
    benchmark_parser.add_argument("--force", action="store_true", help="Explicitly replace existing dataset and result files")
    benchmark_parser.set_defaults(func=cmd_benchmark)

    research_parser = sub.add_parser("research", help="Run and freeze the controlled NeuroCAD research suite")
    research_parser.add_argument("--output", default="research/runs/NC-RUN-2026-09-03-FULL")
    research_parser.add_argument("--run-id", default="NC-RUN-2026-09-03-FULL")
    research_parser.add_argument("--seed", type=int, default=20260902)
    research_parser.add_argument("--compiler-tasks", type=_positive_int, default=240)
    research_parser.add_argument("--ir-programs", type=_positive_int, default=1000)
    research_parser.add_argument("--invalid-cases", type=_positive_int, default=240)
    research_parser.add_argument("--edit-cases", type=_positive_int, default=200)
    research_parser.add_argument("--constraint-ablation-cases", type=_positive_int, default=200)
    research_parser.add_argument("--kernel-samples", type=_positive_int, default=240)
    research_parser.add_argument("--fn", type=_fn, default=48)
    research_parser.add_argument("--timeout", type=_positive_timeout, default=120)
    research_parser.add_argument("--require-kernel", action="store_true")
    research_parser.set_defaults(func=cmd_research)

    demo_parser = sub.add_parser("demo", help="Run the local NeuroCAD prompt/IR demo")
    demo_parser.add_argument("--host", default="127.0.0.1")
    demo_parser.add_argument("--port", type=int, default=8765)
    demo_parser.add_argument("--no-browser", action="store_true")
    demo_parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Explicitly allow the unauthenticated demo to bind beyond loopback",
    )
    demo_parser.set_defaults(func=cmd_demo)

    enclosure_parser = sub.add_parser("enclosure", help="Create, validate, edit, and build typed enclosure projects")
    enclosure_actions = enclosure_parser.add_subparsers(dest="enclosure_action", required=True)

    enclosure_interpret = enclosure_actions.add_parser("interpret", help="Interpret explicit enclosure clauses")
    enclosure_interpret.add_argument("prompt", nargs="+", help="Semicolon-delimited enclosure requirements")
    enclosure_interpret.add_argument("-o", "--output", help="Write the auditable interpretation JSON")
    enclosure_interpret.add_argument("--project-output", help="Write a project file only when interpretation is complete")
    enclosure_interpret.add_argument("--project-id", default="enclosure-project")
    enclosure_interpret.set_defaults(func=cmd_enclosure_interpret)

    enclosure_build = enclosure_actions.add_parser("build", help="Build a new collision-refusing enclosure artifact bundle")
    enclosure_build.add_argument("project", help="NeuroCAD enclosure project JSON")
    enclosure_build.add_argument("--output-dir", required=True, help="A new output directory; existing paths are refused")
    enclosure_build.add_argument("--stl", action="store_true", help="Compile and request-level verify body/lid STL files")
    enclosure_build.add_argument("--fn", type=_fn, default=64)
    enclosure_build.add_argument("--timeout", type=_positive_timeout, default=120)
    enclosure_build.set_defaults(func=cmd_enclosure_build)

    enclosure_verify = enclosure_actions.add_parser(
        "verify", help="Rebuild and verify every source and artifact in an enclosure bundle"
    )
    enclosure_verify.add_argument("bundle", help="Existing enclosure bundle directory")
    enclosure_verify.set_defaults(func=cmd_enclosure_verify)

    enclosure_preflight = enclosure_actions.add_parser("preflight", help="Run exact and disclosed heuristic fabrication checks")
    enclosure_preflight.add_argument("project", help="NeuroCAD enclosure project JSON")
    enclosure_preflight.add_argument("--density", type=float, help="Optional material density in g/cm^3")
    enclosure_preflight.add_argument("--material-cost", type=float, help="Optional material cost per kg; requires density")
    enclosure_preflight.add_argument("--calibration", help="Optional evidence-backed calibration profile JSON")
    enclosure_preflight.set_defaults(func=cmd_enclosure_preflight)

    enclosure_edit = enclosure_actions.add_parser("edit", help="Create a new project revision with a semantic edit")
    enclosure_edit.add_argument("project", help="Source NeuroCAD enclosure project JSON")
    enclosure_edit_source = enclosure_edit.add_mutually_exclusive_group(required=True)
    enclosure_edit_source.add_argument("--instruction", help="One complete natural-language edit instruction")
    enclosure_edit_source.add_argument("--field", help="Supported semantic field path")
    enclosure_edit.add_argument("--value", help="New value encoded as strict JSON; required with --field")
    enclosure_edit.add_argument("--reason", help="Reason retained in revision history; defaults to the instruction")
    enclosure_edit.add_argument("-o", "--output", required=True, help="New project revision path")
    enclosure_edit.set_defaults(func=cmd_enclosure_edit)

    calibration_parser = sub.add_parser("calibration", help="Fit and inspect evidence-bounded printer calibration")
    calibration_actions = calibration_parser.add_subparsers(dest="calibration_action", required=True)
    calibration_fit = calibration_actions.add_parser("fit", help="Fit a profile from measured coupon observations")
    calibration_fit.add_argument("dataset", help="Strict calibration dataset JSON")
    calibration_fit.add_argument("-o", "--output", required=True, help="New calibrated profile JSON")
    calibration_fit.set_defaults(func=cmd_calibration_fit)
    calibration_inspect = calibration_actions.add_parser("inspect", help="Recompute and inspect a calibrated profile")
    calibration_inspect.add_argument("profile", help="Calibrated profile JSON")
    calibration_inspect.set_defaults(func=cmd_calibration_inspect)
    calibration_plan = calibration_actions.add_parser("plan", help="Plan explicit CAD and slicer calibration actions")
    calibration_plan.add_argument("project", help="NeuroCAD enclosure project JSON")
    calibration_plan.add_argument("profile", help="Calibrated profile JSON")
    calibration_plan.set_defaults(func=cmd_calibration_plan)
    calibration_apply = calibration_actions.add_parser(
        "apply-clearance",
        help="Create a revision applying only a measured friction-lid clearance increase",
    )
    calibration_apply.add_argument("project", help="Source NeuroCAD enclosure project JSON")
    calibration_apply.add_argument("profile", help="Calibrated profile JSON")
    calibration_apply.add_argument("-o", "--output", required=True, help="New project revision path")
    calibration_apply.add_argument("--reason", help="Optional audit reason")
    calibration_apply.set_defaults(func=cmd_calibration_apply_clearance)

    integrations_parser = sub.add_parser("integrations", help="Inspect and create honest file handoffs for external applications")
    integration_actions = integrations_parser.add_subparsers(dest="integration_action", required=True)
    integrations_list = integration_actions.add_parser("list", help="Report capabilities and detected prerequisites")
    integrations_list.add_argument("application", nargs="*", help="Optional application IDs or aliases")
    integrations_list.set_defaults(func=cmd_integrations_list)
    integrations_export = integration_actions.add_parser(
        "export", help="Create an OpenSCAD exchange bundle from a validated enclosure project"
    )
    integrations_export.add_argument("project", help="NeuroCAD enclosure project JSON")
    integrations_export.add_argument("--output-dir", required=True, help="New exchange bundle directory")
    integrations_export.add_argument("--stl", action="store_true", help="Compile and verify STL files with OpenSCAD")
    integrations_export.add_argument("--fn", type=_fn, default=64)
    integrations_export.add_argument("--timeout", type=_positive_timeout, default=120)
    integrations_export.add_argument("--manifest", help="Optional neutral application manifest outside the bundle")
    integrations_export.add_argument("--application", action="append", help="Limit the neutral manifest to this application (repeatable)")
    integrations_export.set_defaults(func=cmd_integrations_export)
    integrations_handoff = integration_actions.add_parser(
        "handoff", help="Reverify a bundle and write instructions for one target application"
    )
    integrations_handoff.add_argument("bundle", help="Existing NeuroCAD exchange bundle directory")
    integrations_handoff.add_argument("application", help="Target application ID or alias")
    integrations_handoff.add_argument("-o", "--output", required=True, help="New handoff receipt JSON")
    integrations_handoff.set_defaults(func=cmd_integrations_handoff)
    integrations_verify = integration_actions.add_parser(
        "verify", help="Rebuild and independently verify every source and artifact in a bundle"
    )
    integrations_verify.add_argument("bundle", help="Existing NeuroCAD exchange bundle directory")
    integrations_verify.set_defaults(func=cmd_integrations_verify)
    kicad_request = integration_actions.add_parser(
        "kicad-request", help="Hash a KiCad board and create a bounded external extraction request"
    )
    kicad_request.add_argument("board", help="Existing .kicad_pcb board file")
    kicad_request.add_argument("-o", "--output", required=True, help="New extraction request JSON")
    kicad_request.set_defaults(func=cmd_integrations_kicad_request)
    kicad_extract = integration_actions.add_parser(
        "kicad-extract", help="Extract a bounded rectangular KiCad board plus reviewed mechanical facts"
    )
    kicad_extract.add_argument("board", help="Existing rectangular .kicad_pcb board file")
    kicad_extract.add_argument("--review", required=True, help="Strict mechanical review JSON for connectors and height")
    kicad_extract.add_argument("-o", "--output", required=True, help="New source-hash-bound KiCad receipt JSON")
    kicad_extract.set_defaults(func=cmd_integrations_kicad_extract)
    kicad_bind = integration_actions.add_parser(
        "kicad-bind", help="Bind a reviewed extraction draft to the exact KiCad board bytes"
    )
    kicad_bind.add_argument("draft", help="Reviewed neurocad-kicad-extraction-draft-v1 JSON")
    kicad_bind.add_argument("--source-board", required=True, help="Exact .kicad_pcb file represented by the draft")
    kicad_bind.add_argument("-o", "--output", required=True, help="New hash-bound KiCad receipt JSON")
    kicad_bind.set_defaults(func=cmd_integrations_kicad_bind)
    kicad_inspect = integration_actions.add_parser(
        "kicad-inspect", help="Verify a completed handoff against its source board and print PCB data"
    )
    kicad_inspect.add_argument("receipt", help="Completed bounded KiCad handoff JSON")
    kicad_inspect.add_argument("--source-board", required=True, help="Exact .kicad_pcb file named by the receipt")
    kicad_inspect.set_defaults(func=cmd_integrations_kicad_inspect)
    kicad_apply = integration_actions.add_parser(
        "kicad-apply", help="Apply a hash-bound PCB envelope as a new project revision"
    )
    kicad_apply.add_argument("project", help="Source NeuroCAD enclosure project JSON")
    kicad_apply.add_argument("receipt", help="Completed bounded KiCad handoff JSON")
    kicad_apply.add_argument("--source-board", required=True, help="Exact .kicad_pcb file named by the receipt")
    kicad_apply.add_argument("-o", "--output", required=True, help="New project revision path")
    kicad_apply.add_argument("--reason", help="Optional audit reason stored in project history")
    kicad_apply.set_defaults(func=cmd_integrations_kicad_apply)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        raise SystemExit(0)
    try:
        code = args.func(args)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    raise SystemExit(code)


if __name__ == "__main__":
    main()
