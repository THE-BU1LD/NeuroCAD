from __future__ import annotations

import argparse
import difflib
import importlib
import json
import os
import platform
import re
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from dataclasses import replace
from importlib import metadata
from pathlib import Path
from typing import Any

from core.artifacts import (
    compile_scad,
    compile_scad_verified,
    design_manifest,
    probe_openscad_capabilities,
    verify_stl,
    write_manifest,
    write_text_atomic,
)
from core.benchmark import generate_benchmark, load_benchmark, run_benchmark, save_benchmark_results, write_benchmark
from core.data import prepare_dataset, validate_dataset
from core.ir import CADProgram, program_bounds, program_bounds_are_exact
from core.ir_export import program_to_scad
from core.ir_parser import parse_ir_json, serialize_ir_json
from core.json_io import read_bounded_utf8
from core.program_evaluation import evaluate_program
from core.structural_verification import _build_verification_bundle
from text_to_cad import TextToCAD

__version__ = "0.5.0a6"
MAX_IR_INPUT_BYTES = 1_048_576


def _color_enabled(stream: object = sys.stdout) -> bool:
    return bool(getattr(stream, "isatty", lambda: False)()) and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"


def _paint(value: str, code: str, *, stream: object = sys.stdout) -> str:
    return f"\033[{code}m{value}\033[0m" if _color_enabled(stream) else value


def _duration(value: object) -> str:
    seconds = max(0.0, float(value)) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, remainder = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {remainder}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def _status_label(status: object) -> str:
    labels = {
        "queued": ("◇", "queued", "33"),
        "running": ("◆", "running", "36"),
        "succeeded": ("✓", "succeeded", "32"),
        "failed": ("✗", "failed", "31"),
        "cancelled": ("−", "cancelled", "90"),
        "ready": ("●", "ready", "32"),
        "stopped": ("○", "stopped", "90"),
        "stopping": ("◌", "stopping", "33"),
        "not_started": ("○", "not started", "90"),
    }
    symbol, label, color = labels.get(str(status), ("?", str(status), "33"))
    return _paint(f"{symbol} {label}", color)


def _short(value: object, width: int) -> str:
    text = str(value or "-").replace("\n", " ")
    return text if len(text) <= width else text[: max(1, width - 1)] + "…"


def _print_daemon_status(result: dict[str, object]) -> None:
    print(_paint("NeuroCAD daemon", "1;36"))
    print(f"  {_status_label(result.get('status'))}  pid {result.get('pid', '-')}  uptime {_duration(result.get('uptime_seconds'))}")
    print(
        f"  workers {result.get('workers_alive', 0)}/{result.get('workers', 0)}"
        f"  queue {result.get('queue_depth', 0)}/{result.get('queue_capacity', 0)}"
    )
    jobs = result.get("jobs")
    if isinstance(jobs, dict):
        print("  jobs    " + "  ".join(f"{name} {jobs.get(name, 0)}" for name in ("running", "queued", "succeeded", "failed")))


def _print_job(record: dict[str, object]) -> None:
    print(f"{_status_label(record.get('status'))}  {_paint(str(record.get('job_id', '-')), '1')}")
    request = record.get("request")
    if isinstance(request, dict):
        print(f"  prompt   {request.get('prompt', '-')}")
        print(f"  formats  {', '.join(str(item) for item in request.get('formats', []))}")
    print(f"  created  {record.get('created_at', '-')}")
    if record.get("elapsed_seconds") is not None:
        print(f"  elapsed  {_duration(record.get('elapsed_seconds'))}")
    print(f"  output   {record.get('output_dir', '-')}")
    error = record.get("error")
    if isinstance(error, dict):
        print(_paint(f"  error    {error.get('type', 'Error')}: {error.get('message', 'unknown error')}", "31"))


def _print_jobs(records: list[dict[str, object]]) -> None:
    if not records:
        print("No jobs found.")
        return
    print(_paint(f"NeuroCAD jobs ({len(records)})", "1;36"))
    print(f"{'STATUS':<13} {'JOB ID':<29} {'CREATED':<20} PROMPT")
    for record in records:
        request = record.get("request")
        prompt = request.get("prompt") if isinstance(request, dict) else "-"
        created = str(record.get("created_at", "-")).replace("T", " ").removesuffix("Z")[:19]
        print(f"{_status_label(record.get('status')):<13} {_short(record.get('job_id'), 28):<29} {created:<20} {_short(prompt, 52)}")


def _job_transition(record: dict[str, object]) -> None:
    if _color_enabled(sys.stderr):
        print(f"  {_status_label(record.get('status'))}  {record.get('job_id', '')}", file=sys.stderr, flush=True)


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


def _format_mm(value: object) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "-"
    return f"{float(value):.6g} mm"


def _source_location(source: str, offset: int | None) -> str:
    if offset is None:
        return ""
    line = source.count("\n", 0, offset) + 1
    previous = source.rfind("\n", 0, offset)
    column = offset + 1 if previous < 0 else offset - previous
    return f"line {line}, column {column}"


def _print_interpretation(interpretation: Any) -> None:
    status = "ready" if interpretation.ready else "needs input"
    color = "32" if interpretation.ready else "33"
    print(_paint("NeuroCAD language analysis", "1;36"))
    print(f"  {_paint(status, color)}  {interpretation.interpreter}")
    if interpretation.mappings:
        print(_paint("\nUnderstood", "1"))
        for mapping in interpretation.mappings:
            print(f"  {_paint('OK', '32'):<2} {mapping.field:<24} {_short(mapping.text, 68)}")
    if interpretation.issues:
        print(_paint("\nNeeds attention", "1"))
        for issue in interpretation.issues:
            marker = "?" if issue.kind == "question" else "!"
            color = "33" if issue.kind == "question" else "31"
            location = _source_location(interpretation.source, issue.start)
            suffix = f" ({location})" if location else ""
            print(f"  {_paint(marker, color)} {issue.kind}: {issue.message}{suffix}")
            if issue.text:
                print(f"    {_short(issue.text, 76)}")
            if issue.suggestion:
                print(f"    next: {issue.suggestion}")
    if interpretation.assumptions:
        print(_paint("\nDisclosed assumptions", "1"))
        for assumption in interpretation.assumptions:
            print(f"  {_paint('!', '33')} {assumption.field} = {assumption.value:g} mm")
            print(f"    {assumption.reason}")
    if interpretation.spec is not None:
        spec = interpretation.spec
        width, depth, height = spec.outer_size_mm
        floor = spec.wall_mm if spec.floor_mm is None else spec.floor_mm
        floor_note = " (wall default)" if spec.floor_mm is None else ""
        print(_paint("\nResolved specification", "1"))
        print(f"  title       {spec.title}")
        print(f"  envelope    {width:g} x {depth:g} x {height:g} mm")
        print(f"  shell       wall {spec.wall_mm:g} mm  floor {floor:g} mm{floor_note}  radius {spec.corner_radius_mm:g} mm")
        print(f"  process     {spec.profile.replace('_', ' ')}")
        closure = "open top" if spec.lid.kind == "none" else f"{spec.lid.kind} lid"
        print(f"  closure     {closure}")
        print(f"  features    {len(spec.cutouts)} cutouts  {len(spec.vents)} vents  {len(spec.standoffs)} standoffs")


def _print_tolerance_report(report: dict[str, object]) -> None:
    result = report["result"]
    if not isinstance(result, dict):
        raise TypeError("tolerance report result must be an object")
    margin = result.get("margin_to_target_mm")
    worst = result.get("worst_case_low_mm")
    target_met = isinstance(margin, (int, float)) and not isinstance(margin, bool) and margin >= 0
    if result.get("worst_case_guard_applied"):
        target_met = target_met and isinstance(worst, (int, float)) and not isinstance(worst, bool) and worst >= 0
    status = "target met" if target_met else "clearance revision recommended"
    color = "32" if target_met else "33"
    print(_paint("NeuroCAD tolerance analysis", "1;36"))
    print(f"  {_paint(status, color)}  {report['model']} / {report['variation_model']}")
    print(_paint("\nClearance", "1"))
    print(f"  nominal       {_format_mm(result.get('nominal_clearance_mm'))}")
    print(f"  predicted     {_format_mm(result.get('mean_clearance_mm'))}")
    print(f"  sigma         {_format_mm(result.get('sigma_mm'))}")
    print(f"  target low    {_format_mm(result.get('statistical_low_mm'))}")
    print(f"  worst low     {_format_mm(result.get('worst_case_low_mm'))}")
    print(f"  recommended   {_format_mm(result.get('recommended_clearance_mm'))}")
    probability = result.get("success_probability", result.get("moment_matched_success_probability"))
    target = result.get("target_success_probability")
    if isinstance(probability, (int, float)) and isinstance(target, (int, float)):
        print(f"  fit estimate  {float(probability):.5%}  target {float(target):.5%}")
    contributions = result.get("contributions")
    if isinstance(contributions, list) and contributions:
        print(_paint("\nContributions", "1"))
        print(f"  {'NAME':<22} {'MEAN':>11} {'SIGMA':>11} {'VARIANCE':>11}")
        for entry in contributions:
            if not isinstance(entry, dict):
                continue
            fraction = entry.get("variance_fraction")
            fraction_text = "-" if fraction is None else f"{float(fraction):.1%}"
            print(
                f"  {_short(entry.get('name'), 22):<22} {_format_mm(entry.get('mean_effect_mm')):>11} "
                f"{_format_mm(entry.get('sigma_mm')):>11} {fraction_text:>11}"
            )
    print("\n  Analytical estimate only; physical acceptance still requires measured evidence.")


def cmd_doctor(args: argparse.Namespace) -> int:
    from core.config import default_config_path, load_config
    from core.daemon import daemon_is_ready

    checks: list[dict[str, object]] = []

    def add(name: str, ok: bool, detail: str, *, required: bool = True) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail, "required": required})

    add("Python", sys.version_info >= (3, 10), platform.python_version())
    for package in ("jsonschema", "numpy", "trimesh"):
        try:
            importlib.import_module(package)
            version = metadata.version(package)
            add(package, True, str(version))
        except ImportError as exc:
            add(package, False, str(exc))

    try:
        generator = TextToCAD()
        doc = generator.build("a 120 x 80 x 4 mm plate with four 4 mm holes")
        scad = doc.scad
        add("Generation", bool(scad.strip()), f"{len(scad)} character OpenSCAD program")
        add("Validation", doc.validation.valid, "; ".join(doc.validation.errors) or "semantic checks passed")
    except Exception as exc:  # noqa: BLE001 - doctor must report a broken installation instead of crashing
        add("Generation", False, str(exc))

    openscad = probe_openscad_capabilities()
    add("OpenSCAD mesh", openscad.mesh, openscad.mesh_detail, required=False)
    add("OpenSCAD preview", openscad.preview, openscad.preview_detail, required=False)
    config_path = _resolved_path(args.config) if args.config else default_config_path().resolve()
    config = None
    if config_path.exists():
        try:
            config = load_config(config_path, require_exists=True)
            add("Configuration", True, str(config_path))
        except (OSError, TypeError, ValueError) as exc:
            add("Configuration", False, str(exc))
    else:
        add("Configuration", True, f"first prompt will create {config_path}")
    if config is not None:
        storage_path = Path(config.output_root)
        while not storage_path.exists() and storage_path != storage_path.parent:
            storage_path = storage_path.parent
        free = shutil.disk_usage(storage_path).free
        add("Output storage", free >= 100 * 1024 * 1024, f"{free / (1024**3):.1f} GiB free at {config.output_root}")
        daemon_ready = daemon_is_ready(config)
        add("Daemon", daemon_ready, "ready" if daemon_ready else "stopped; starts automatically", required=False)

    failed = any(bool(check["required"]) and not bool(check["ok"]) for check in checks)
    if args.json:
        print(json.dumps({"ok": not failed, "checks": checks}, indent=2, sort_keys=True))
    else:
        print(_paint("NeuroCAD doctor", "1;36"))
        for check in checks:
            if check["ok"]:
                mark = _paint("✓", "32")
            elif check["required"]:
                mark = _paint("✗", "31")
            else:
                mark = _paint("!", "33")
            print(f"  {mark} {check['name']!s:<15} {check['detail']}")
        print(_paint("  healthy" if not failed else "  action required", "1;32" if not failed else "1;31"))
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


def build_verification_report(prompt: str, fn: int = 96):
    """Compatibility API for canonical main's structural-only report."""
    return _build_verification_bundle(prompt, fn)[0]


def cmd_verify(args: argparse.Namespace) -> int:
    report_path = _resolved_path(args.json_output) if args.json_output else None
    scad_path = _resolved_path(args.scad_output) if args.scad_output else None
    _require_distinct_paths(report=report_path, scad=scad_path)
    _require_new_paths(force=args.force, report=report_path, scad=scad_path)
    report, scad = _build_verification_bundle(_prompt(args.prompt), args.fn)
    if scad_path is not None and report["status"] == "valid":
        write_text_atomic(scad_path, scad)
    payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if report_path is not None:
        write_text_atomic(report_path, payload)
        print(report_path)
    else:
        print(payload, end="")
    return 0 if report["status"] == "valid" else 1


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
        print(_paint("INVALID", "1;31", stream=sys.stderr), file=sys.stderr)
        _show_errors(doc.validation.errors)
    else:
        program = doc.require_program()
        extents = _program_extents(program)
        primitives = sum(node.primitive is not None for node in program.nodes)
        operations = sum(node.composition is not None for node in program.nodes)
        for warning in doc.validation.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        print(_paint("VALID", "1;32"))
        print(f"  design       {program.title}")
        print(f"  structure    {primitives} primitives  {operations} operations  {len(program.constraints)} constraints")
        if extents is not None:
            print(f"  extents      {extents[0]:g} x {extents[1]:g} x {extents[2]:g} mm")
        else:
            print("  extents      conservative or transform-dependent")
        mesh_verification = doc.design.metadata.get("mesh_verification")
        if isinstance(mesh_verification, dict):
            print(f"  kernel       watertight STL verified  {mesh_verification.get('faces', '-')} faces")
        else:
            print("  kernel       not requested; use --compile for STL verification")
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
    _require_new_paths(force=args.force, results=output)
    if args.generate:
        if dataset.exists() and not args.force:
            raise FileExistsError(f"dataset already exists; choose a new path or pass --force: {dataset}")
        tasks = generate_benchmark(seed=args.seed)
        write_benchmark(dataset, tasks)
    else:
        tasks = load_benchmark(dataset)
    results = run_benchmark(tasks, seed=args.seed)
    save_benchmark_results(output, results)
    print(json.dumps({"dataset": str(dataset), "results": str(output), "task_count": len(tasks)}, sort_keys=True))
    return 0


def cmd_data_prepare(args: argparse.Namespace) -> int:
    print(json.dumps(prepare_dataset(_resolved_path(args.output), seed=args.seed, force=args.force), indent=2, sort_keys=True))
    return 0


def cmd_data_validate(args: argparse.Namespace) -> int:
    print(json.dumps(validate_dataset(_resolved_path(args.dataset)), indent=2, sort_keys=True))
    return 0


def _requested_formats(value: str) -> tuple[str, ...]:
    if value == "all":
        return ("ir", "scad", "stl", "preview")
    if value == "auto":
        capabilities = probe_openscad_capabilities()
        formats = ["ir", "scad"]
        if capabilities.mesh:
            formats.append("stl")
        if capabilities.preview:
            formats.append("preview")
        return tuple(formats)
    return (value,)


def cmd_generate(args: argparse.Namespace) -> int:
    from core.config import default_config_path, ensure_runtime_directories, load_or_create_config
    from core.daemon import daemon_is_ready, daemon_request, new_job_id, start_daemon, wait_for_job
    from core.generation import GenerationRequest, generate_artifacts

    config_path = _resolved_path(args.config) if args.config else default_config_path().resolve()
    config, config_path, created = load_or_create_config(config_path)
    ensure_runtime_directories(config)
    if created and _color_enabled(sys.stderr):
        print(f"  {_paint('✓', '32', stream=sys.stderr)} created config  {config_path}", file=sys.stderr)
    prompt = _prompt(args.prompt)
    formats = _requested_formats(args.format)
    fn = args.fn or config.default_fn
    timeout = args.timeout or config.default_timeout_seconds
    if args.local or args.output:
        output = _resolved_path(args.output) if args.output else Path(config.output_root) / new_job_id()
        result = generate_artifacts(
            GenerationRequest(prompt=prompt, output_dir=str(output), formats=formats, fn=fn, timeout_seconds=timeout)
        )
        if args.json:
            print(json.dumps(result, sort_keys=True))
        elif _color_enabled():
            print(f"{_paint('✓ complete', '1;32')}  {_duration(result.get('runtime', {}).get('elapsed_seconds'))}")
            print(f"  {result['output_dir']}")
        else:
            print(result["output_dir"])
        return 0
    if not daemon_is_ready(config):
        if args.no_start:
            raise RuntimeError("NeuroCAD daemon is not running; use 'neurocad daemon start' or omit --no-start")
        start_daemon(config_path, config)
    record = daemon_request(
        config,
        "submit",
        payload={"prompt": prompt, "formats": list(formats), "fn": fn, "timeout_seconds": timeout},
    )
    if args.no_wait:
        if args.json:
            print(json.dumps(record, sort_keys=True))
        elif _color_enabled():
            print(f"{_status_label('queued')}  {record['job_id']}")
            print("  Use `neurocad jobs wait JOB_ID` to follow it.")
        else:
            print(record["job_id"])
        return 0
    record = wait_for_job(
        config,
        record["job_id"],
        timeout_seconds=args.wait_timeout,
        on_update=None if args.json else _job_transition,
    )
    if record["status"] != "succeeded":
        error = record.get("error") or {}
        raise RuntimeError(f"generation failed ({error.get('type', 'unknown')}): {error.get('message', 'unknown error')}")
    if args.json:
        print(json.dumps(record, sort_keys=True))
    elif _color_enabled():
        print(f"{_paint('✓ complete', '1;32')}  {_duration(record.get('elapsed_seconds'))}")
        print(f"  {record['output_dir']}")
    else:
        print(record["output_dir"])
    return 0


def cmd_setup(args: argparse.Namespace) -> int:
    import time

    from core.config import NeuroCADConfig, default_config_path, ensure_runtime_directories, load_config, write_config
    from core.daemon import daemon_is_ready, daemon_request, start_daemon
    from core.service import install_user_service

    config_path = _resolved_path(args.config) if args.config else default_config_path().resolve()
    if config_path.exists():
        config = load_config(config_path, require_exists=True)
    else:
        config = NeuroCADConfig.defaults()
        if args.output_root:
            config = replace(config, output_root=str(_resolved_path(args.output_root)))
        write_config(config, config_path)
    ensure_runtime_directories(config)
    if args.repair and daemon_is_ready(config):
        daemon_request(config, "shutdown")
        deadline = time.monotonic() + 10
        while daemon_is_ready(config) and time.monotonic() < deadline:
            time.sleep(0.05)
        if daemon_is_ready(config):
            raise RuntimeError("daemon did not stop during repair")
    service = (
        {"manager": "disabled", "path": None, "activated": False, "detail": "service installation skipped"}
        if args.no_service
        else install_user_service(config_path, config, activate=not args.no_start)
    )
    daemon: dict[str, object] = {"status": "not_started"}
    if not args.no_start:
        deadline = time.monotonic() + 3
        while not daemon_is_ready(config) and time.monotonic() < deadline:
            time.sleep(0.05)
        daemon = daemon_request(config, "ping") if daemon_is_ready(config) else start_daemon(config_path, config)
    result = {"config": str(config_path), "output_root": config.output_root, "service": service, "daemon": daemon}
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(_paint("NeuroCAD is ready", "1;32"))
        print(f"  config   {config_path}")
        print(f"  outputs  {config.output_root}")
        print(f"  daemon   {daemon.get('status', 'not started')}")
        print(f"  service  {service.get('manager', 'disabled')}")
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    import time

    from core.config import default_config_path, load_config
    from core.daemon import daemon_is_ready, daemon_request
    from core.service import uninstall_user_service

    config_path = _resolved_path(args.config) if args.config else default_config_path().resolve()
    daemon_stopped = True
    if config_path.exists():
        config = load_config(config_path, require_exists=True)
        if daemon_is_ready(config):
            daemon_request(config, "shutdown")
            deadline = time.monotonic() + 10
            while daemon_is_ready(config) and time.monotonic() < deadline:
                time.sleep(0.05)
            daemon_stopped = not daemon_is_ready(config)
            if not daemon_stopped:
                raise RuntimeError("daemon did not stop during uninstall")
    service = uninstall_user_service(remove_definition=True)
    config_removed = False
    if args.remove_config and config_path.exists():
        config_path.unlink()
        config_removed = True
    result = {
        "status": "uninstalled",
        "daemon_stopped": daemon_stopped,
        "service": service,
        "config": str(config_path),
        "config_removed": config_removed,
        "data_preserved": True,
    }
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else "NeuroCAD service removed; generated data was preserved.")
    return 0


def _job_or_bundle(value: str, config_path_value: str | None) -> Path:
    from core.config import default_config_path, load_config
    from core.daemon import JOB_ID_PATTERN, JobStore

    if JOB_ID_PATTERN.fullmatch(value):
        config_path = _resolved_path(config_path_value) if config_path_value else default_config_path().resolve()
        config = load_config(config_path, require_exists=True)
        record = JobStore(config).read(value)
        if record.get("status") != "succeeded":
            raise RuntimeError(f"job {value} is {record.get('status')}; only successful jobs have complete artifacts")
        output = record.get("output_dir")
        if not isinstance(output, str):
            raise TypeError(f"job {value} has no valid output directory")
        return Path(output).expanduser().resolve()
    return _resolved_path(value)


def cmd_artifacts(args: argparse.Namespace) -> int:
    from core.generation import verify_artifact_bundle

    bundle = _job_or_bundle(args.bundle, args.config)
    result = verify_artifact_bundle(bundle)
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else f"verified {result['artifact_count']} artifacts: {bundle}")
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    bundle = _job_or_bundle(args.job_id, args.config)
    if not bundle.is_dir():
        raise FileNotFoundError(f"job output directory does not exist: {bundle}")
    if args.print_only:
        print(bundle)
        return 0
    system = platform.system()
    if system == "Darwin":
        command = ["open", str(bundle)]
    elif system == "Windows":
        command = ["explorer", str(bundle)]
    else:
        command = ["xdg-open", str(bundle)]
    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)  # nosec B603 B607
    except FileNotFoundError as exc:
        raise RuntimeError(f"no desktop opener is available; artifact directory: {bundle}") from exc
    print(bundle)
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    from core.performance import profile_generation

    result = profile_generation(
        _prompt(args.prompt),
        iterations=args.iterations,
        fn=args.fn,
        warmup_iterations=args.warmups,
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = _resolved_path(args.output)
        _require_new_path(output, label="performance profile")
        write_text_atomic(output, payload)
        print(output)
    else:
        print(payload, end="")
    return 0


def cmd_daemon(args: argparse.Namespace) -> int:
    import time

    from core.config import default_config_path, load_or_create_config
    from core.daemon import daemon_is_ready, daemon_request, start_daemon

    config_path = _resolved_path(args.config) if args.config else default_config_path().resolve()
    config, config_path, _ = load_or_create_config(config_path)
    action = args.daemon_action
    if action == "start":
        result = start_daemon(config_path, config)
    elif action == "status":
        if not daemon_is_ready(config):
            stopped: dict[str, object] = {"status": "stopped", "socket": config.socket_path}
            if args.json:
                print(json.dumps(stopped, sort_keys=True))
            else:
                print(_paint("NeuroCAD daemon", "1;36"))
                print(f"  {_status_label('stopped')}  run `neurocad daemon start`")
            return 1
        result = daemon_request(config, "ping")
    elif action in {"stop", "restart"}:
        if daemon_is_ready(config):
            result = daemon_request(config, "shutdown")
            deadline = time.monotonic() + 10
            while daemon_is_ready(config) and time.monotonic() < deadline:
                time.sleep(0.05)
            if daemon_is_ready(config):
                raise RuntimeError("daemon did not stop within 10 seconds")
        else:
            result = {"status": "stopped"}
        if action == "restart":
            result = start_daemon(config_path, config)
    else:
        log_path = Path(config.log_path)
        if not log_path.exists():
            print(f"No daemon log exists at {log_path}")
            return 0
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-args.lines :]
        print("\n".join(lines))
        return 0
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif result.get("status") == "ready":
        _print_daemon_status(result)
    else:
        print(_status_label(result.get("status")))
    return 0


def cmd_jobs(args: argparse.Namespace) -> int:
    from core.config import default_config_path, load_config
    from core.daemon import daemon_request, wait_for_job

    config_path = _resolved_path(args.config) if args.config else default_config_path().resolve()
    config = load_config(config_path, require_exists=True)
    if args.jobs_action == "list":
        result = daemon_request(config, "list", limit=args.limit)
        jobs = result.get("jobs", [])
        if not isinstance(jobs, list):
            raise TypeError("daemon returned an invalid job list")
        if args.status:
            jobs = [job for job in jobs if isinstance(job, dict) and job.get("status") == args.status]
        result = {"jobs": jobs}
    elif args.jobs_action == "show":
        result = daemon_request(config, "show", job_id=args.job_id)
    elif args.jobs_action == "cancel":
        result = daemon_request(config, "cancel", job_id=args.job_id)
    elif args.jobs_action == "retry":
        result = daemon_request(config, "retry", job_id=args.job_id)
        if not args.no_wait:
            result = wait_for_job(
                config,
                result["job_id"],
                timeout_seconds=args.timeout,
                on_update=None if args.json else _job_transition,
            )
    else:
        result = wait_for_job(
            config,
            args.job_id,
            timeout_seconds=args.timeout,
            on_update=None if args.json else _job_transition,
        )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.jobs_action == "list":
        _print_jobs(result["jobs"])
    else:
        _print_job(result)
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    from core.config import default_config_path, load_config, write_config

    config_path = _resolved_path(args.config) if args.config else default_config_path().resolve()
    config = load_config(config_path, require_exists=True)
    if args.config_action == "show":
        print(json.dumps(config.to_dict(), indent=2, sort_keys=True))
        return 0
    if args.key == "default_formats":
        config = replace(config, default_formats=tuple(part.strip() for part in args.value.split(",") if part.strip()))
    elif args.key in {"worker_count", "default_fn", "default_timeout_seconds"}:
        integer_value = int(args.value)
        if args.key == "worker_count":
            config = replace(config, worker_count=integer_value)
        elif args.key == "default_fn":
            config = replace(config, default_fn=integer_value)
        else:
            config = replace(config, default_timeout_seconds=integer_value)
    else:
        path_value = str(_resolved_path(args.value))
        if args.key == "data_root":
            config = replace(config, data_root=path_value)
        elif args.key == "state_root":
            config = replace(config, state_root=path_value)
        elif args.key == "output_root":
            config = replace(config, output_root=path_value)
        elif args.key == "socket_path":
            config = replace(config, socket_path=path_value)
        else:
            config = replace(config, log_path=path_value)
    write_config(config, config_path, overwrite=True)
    print(json.dumps({"config": str(config_path), "updated": args.key, "restart_required": True}, sort_keys=True))
    return 0


def cmd_shell(args: argparse.Namespace) -> int:
    if not sys.stdin.isatty():
        raise RuntimeError("interactive shell requires a terminal")
    import webbrowser

    from core.agent_workbench import start_agent_workbench
    from core.agentic import AgentWorkspace, planning_provider
    from core.config import default_config_path, load_or_create_config
    from core.daemon import daemon_is_ready, daemon_request
    from core.prompt_engine import generate_design
    from core.validation import validate_design

    config_path = _resolved_path(args.config) if args.config else default_config_path().resolve()
    config, _, _ = load_or_create_config(config_path)
    project_path = _resolved_path(args.project) if args.project else (Path(config.data_root) / "projects" / "default").resolve()
    workspace = AgentWorkspace(project_path)
    provider = planning_provider(args.provider)
    workbench_server = None
    workbench_thread = None
    workbench_url = None

    def open_view() -> None:
        nonlocal workbench_server, workbench_thread, workbench_url
        if workbench_server is None:
            workbench_server, workbench_thread, workbench_url = start_agent_workbench(
                workspace,
                port=args.port,
                open_browser=True,
            )
        elif workbench_url is not None:
            webbrowser.open(workbench_url)
        print(f"  {_paint('live view', '1;36')}  {workbench_url}")

    def open_in_openscad() -> None:
        design_path = workspace.root / "design.scad"
        if not design_path.is_file():
            raise FileNotFoundError("the active agent project has no design.scad yet")
        if platform.system() == "Darwin":
            command = ["open", "-a", "OpenSCAD", str(design_path)]
        else:
            executable = shutil.which("openscad")
            if executable is None:
                raise RuntimeError(f"OpenSCAD is not available; design file: {design_path}")
            command = [executable, str(design_path)]
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)  # nosec B603 B607
        print(f"  {_paint('opened in OpenSCAD', '1;32')}  {design_path}")

    if args.view:
        open_view()
    print(_paint("┌─ NEUROCAD / AGENT STUDIO", "1;36"))
    print(f"│  project   {_short(project_path, 68)}")
    print(f"│  planner   {provider.name}")
    print("│  :view  :project  :assumptions  :history  :status  :jobs  :help  :quit")
    print(_paint("└────────────────────────────────────────────────────────────────────", "36"))
    print("  Describe a design naturally. Explicit dimensions remain authoritative.\n")
    try:
        while True:
            try:
                value = input(_paint("you › ", "1;36")).strip()
            except EOFError:
                print()
                return 0
            except KeyboardInterrupt:
                print("\n  interrupted")
                continue
            if not value:
                continue
            if value in {":quit", ":exit", "quit", "exit"}:
                return 0
            if value == ":help":
                print("  Describe an object or revise the active agent project in ordinary language.")
                print("  Dimensioned plates, enclosures, and primitives use the verified fast path.")
                print("  :view opens live geometry; :project shows files; :assumptions shows inferred choices.")
                continue
            if value == ":view":
                open_view()
                continue
            if value in {":project", ":assumptions", ":history"}:
                state = workspace.read_state()
                if state is None:
                    print("  no agent project revision yet")
                elif value == ":project":
                    print(f"  {project_path}")
                    print(f"  revision {state['revision']}  {state['status']}  {state['title']}")
                elif value == ":assumptions":
                    for assumption in state["plan"]["assumptions"]:
                        print(f"  {_paint('◆', '33')} {assumption['name']}: {assumption['value']}")
                        print(f"    {assumption['reason']} [{assumption['source']}]")
                else:
                    for item in state.get("history", []):
                        print(f"  r{item['revision']:04d}  {item['prompt']}  ({item['provider']})")
                continue
            if value in {":status", ":jobs"}:
                if not daemon_is_ready(config):
                    print(f"  {_status_label('stopped')}  a verified fast-path request will start the daemon")
                elif value == ":status":
                    _print_daemon_status(daemon_request(config, "ping"))
                else:
                    response = daemon_request(config, "list", limit=10)
                    records = response.get("jobs", [])
                    if not isinstance(records, list):
                        raise TypeError("daemon returned an invalid job list")
                    _print_jobs(records)
                continue
            if value.startswith(":"):
                print(f"  unknown command {value!r}; use :help")
                continue
            try:
                if re.search(r"^\s*(?:open|show|view)\b.*\bopenscad\b", value, re.IGNORECASE):
                    open_in_openscad()
                    continue
                design = generate_design(value)
                if validate_design(design).valid:
                    command = argparse.Namespace(
                        prompt=[value],
                        config=args.config,
                        local=False,
                        output=None,
                        format="auto",
                        fn=None,
                        timeout=None,
                        no_start=False,
                        no_wait=False,
                        wait_timeout=None,
                        json=False,
                    )
                    cmd_generate(command)
                    continue

                def progress(event: dict[str, object]) -> None:
                    symbol = "✓" if event["status"] == "complete" else "◆"
                    color = "32" if event["status"] == "complete" else "36"
                    print(f"  {_paint(symbol, color)} {event['message']}")

                result = workspace.run(value, provider, fn=config.default_fn, callback=progress)
                print(f"  {_paint('✓ draft revision complete', '1;32')}  r{result.revision:04d}")
                print(f"    {result.project_dir}")
                if workbench_url is None:
                    print("    use :view for the live project workbench")
            except KeyboardInterrupt:
                print("\n  interrupted; the last completed component checkpoint is still available")
            except (OSError, RuntimeError, TypeError, ValueError) as exc:
                print(f"  {_paint('ERROR', '1;31', stream=sys.stderr)}: {exc}", file=sys.stderr)
    finally:
        if workbench_server is not None:
            workbench_server.shutdown()
            workbench_server.server_close()
        if workbench_thread is not None:
            workbench_thread.join(timeout=2)


def _agent_progress(event: dict[str, object]) -> None:
    symbol = "✓" if event["status"] == "complete" else "◆"
    color = "32" if event["status"] == "complete" else "36"
    print(f"{_paint(symbol, color)} {event['message']}")


def cmd_agent_run(args: argparse.Namespace) -> int:
    from core.agentic import AgentWorkspace, planning_provider

    workspace = AgentWorkspace(_resolved_path(args.project))
    provider = planning_provider(args.provider)
    result = workspace.run(
        _prompt(args.prompt),
        provider,
        fn=args.fn,
        callback=None if args.json else _agent_progress,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"{_paint('✓ draft complete', '1;32')}  revision {result.revision}")
        print(f"  {result.project_dir}")
    return 0


def cmd_agent_inspect(args: argparse.Namespace) -> int:
    from core.agentic import AgentWorkspace

    state = AgentWorkspace(_resolved_path(args.project)).read_state()
    if state is None:
        raise FileNotFoundError("agent project has no project.json")
    print(json.dumps(state, indent=2, sort_keys=True))
    return 0


def cmd_agent_view(args: argparse.Namespace) -> int:
    from core.agent_workbench import start_agent_workbench
    from core.agentic import AgentWorkspace

    server, thread, url = start_agent_workbench(
        AgentWorkspace(_resolved_path(args.project)),
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
    )
    print(f"NeuroCAD live agent workbench: {url}")
    try:
        thread.join()
    except KeyboardInterrupt:
        print()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    return 0


def cmd_research(args: argparse.Namespace) -> int:
    from dataclasses import replace

    from core.research_suite import ResearchConfig, load_research_config, run_research_suite

    config, configured_run_id = load_research_config(_resolved_path(args.config)) if args.config else (ResearchConfig(), None)
    overrides = {
        "seed": args.seed,
        "compiler_tasks": args.compiler_tasks,
        "ir_programs": args.ir_programs,
        "invalid_cases": args.invalid_cases,
        "edit_cases": args.edit_cases,
        "constraint_ablation_cases": args.constraint_ablation_cases,
        "kernel_samples": args.kernel_samples,
        "fn": args.fn,
        "openscad_timeout_seconds": args.timeout,
    }
    config = replace(config, **{key: value for key, value in overrides.items() if value is not None})
    config.validate()
    run_id = args.run_id or configured_run_id or "NC-RUN-2026-09-03-FULL"
    output = _resolved_path(args.output)
    results = run_research_suite(output, config, require_kernel=args.require_kernel, run_id=run_id)
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


def cmd_topology(args: argparse.Namespace) -> int:
    import hashlib
    import io

    import trimesh

    from core.mesh_geometry import analyze_self_intersections
    from core.topology import analyze_triangle_complex

    source = _resolved_path(args.input)
    output = _resolved_path(args.output) if args.output else None
    _require_distinct_paths(input=source, output=output)
    _require_new_paths(force=args.force, output=output)
    if source.suffix.lower() != ".stl":
        raise ValueError("topology input must be an STL file")
    with source.open("rb") as handle:
        payload = handle.read(32 * 1024 * 1024 + 1)
    if not payload or len(payload) > 32 * 1024 * 1024:
        raise ValueError("topology input must be non-empty and at most 32 MiB")
    mesh = trimesh.load_mesh(io.BytesIO(payload), file_type="stl", process=True)
    report = analyze_triangle_complex(mesh.vertices, mesh.faces)
    report["embedding"] = analyze_self_intersections(mesh.vertices, mesh.faces)
    report["source_sha256"] = hashlib.sha256(payload).hexdigest()
    report["preprocessing"] = "trimesh process=True vertex welding; topology is of the processed mesh"
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if output:
        write_text_atomic(output, text)
    print(text, end="")
    if args.require_closed_manifold and (not report["manifold"] or not report["closed"] or report["embedding"]["self_intersecting"]):
        return 1
    return 0


def cmd_tolerance(args: argparse.Namespace) -> int:
    from core.engineering_math import ToleranceContribution, quadratic_tolerance_stack, tolerance_stack
    from core.json_io import strict_json_loads

    source = _resolved_path(args.input)
    output = _resolved_path(args.output) if args.output else None
    _require_distinct_paths(input=source, output=output)
    _require_new_paths(force=args.force, output=output)
    with source.open("rb") as handle:
        payload = handle.read(MAX_IR_INPUT_BYTES + 1)
    if len(payload) > MAX_IR_INPUT_BYTES:
        raise ValueError("tolerance input exceeds 1 MiB")
    request = strict_json_loads(payload.decode("utf-8"))
    required = {"nominal_clearance_mm", "contributions"}
    optional = {
        "correlations",
        "confidence_multiplier",
        "model",
        "sensitivities",
        "hessian_per_mm",
        "target_success_probability",
        "require_nonnegative_worst_case",
    }
    if not isinstance(request, dict) or not required <= request.keys() or request.keys() - (required | optional):
        raise ValueError(
            "tolerance input requires nominal_clearance_mm and contributions; optional model, correlations, "
            "confidence_multiplier, target_success_probability, require_nonnegative_worst_case, sensitivities, "
            "and hessian_per_mm"
        )
    if not isinstance(request["contributions"], list) or len(request["contributions"]) > 128:
        raise ValueError("contributions must be an array of at most 128 entries")
    contributions = []
    for entry in request["contributions"]:
        if not isinstance(entry, dict) or set(entry) != {"name", "mean_mm", "sigma_mm", "worst_case_mm"}:
            raise ValueError("each contribution requires exactly name, mean_mm, sigma_mm, worst_case_mm")
        contributions.append(ToleranceContribution(**entry))
    model = request.get("model", "linear")
    if model == "linear":
        if "sensitivities" in request or "hessian_per_mm" in request:
            raise ValueError("sensitivities and hessian_per_mm require model 'quadratic'")
        result_payload = tolerance_stack(
            request["nominal_clearance_mm"],
            tuple(contributions),
            confidence_multiplier=request.get("confidence_multiplier", 3.0),
            correlations=request.get("correlations"),
            target_success_probability=request.get("target_success_probability"),
            require_nonnegative_worst_case=request.get("require_nonnegative_worst_case", False),
        ).to_dict()
        probability_model = "normal"
    elif model == "quadratic":
        if "sensitivities" not in request or "hessian_per_mm" not in request:
            raise ValueError("quadratic model requires sensitivities and hessian_per_mm")
        result_payload = quadratic_tolerance_stack(
            request["nominal_clearance_mm"],
            tuple(contributions),
            sensitivities=tuple(request["sensitivities"]),
            hessian_per_mm=tuple(tuple(row) for row in request["hessian_per_mm"]),
            confidence_multiplier=request.get("confidence_multiplier", 3.0),
            correlations=request.get("correlations"),
            target_success_probability=request.get("target_success_probability"),
            require_nonnegative_worst_case=request.get("require_nonnegative_worst_case", False),
        ).to_dict()
        probability_model = "moment_matched_normal_for_quadratic_form"
    else:
        raise ValueError("model must be 'linear' or 'quadratic'")
    report = {
        "schema_version": "neurocad-tolerance-v2",
        "math_revision": "neurocad-tolerance-math-v3",
        "result": result_payload,
        "model": model,
        "variation_model": "joint_normal_correlated" if request.get("correlations") is not None else "independent_normal",
        "probability_model": probability_model,
        "limitations": [
            "Normal-model fit probability is not empirical acceptance or a safety guarantee.",
            "Worst-case intervals are separate declared bounds, not bounds on a normal distribution.",
            "Quadratic success probability is moment-matched; only its reported first two moments are analytical.",
        ],
    }
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if output:
        write_text_atomic(output, text)
    if getattr(args, "human", False) and not getattr(args, "json", False):
        _print_tolerance_report(report)
        if output:
            print(f"\n  report        {output}")
    else:
        print(text, end="")
    return 0


def cmd_math_beam(args: argparse.Namespace) -> int:
    from core.engineering_math import rectangular_cantilever

    result = rectangular_cantilever(
        force_n=args.force,
        length_mm=args.length,
        width_mm=args.width,
        thickness_mm=args.thickness,
        elastic_modulus_mpa=args.modulus,
        yield_strength_mpa=args.yield_strength,
    )
    payload = {
        "schema_version": "neurocad-cantilever-v1",
        "model": "euler_bernoulli_end_loaded_rectangular_cantilever",
        "inputs": {
            "force_n": args.force,
            "length_mm": args.length,
            "width_mm": args.width,
            "thickness_mm": args.thickness,
            "elastic_modulus_mpa": args.modulus,
            "yield_strength_mpa": args.yield_strength,
        },
        "result": result.to_dict(),
        "limitations": [
            "Small-deflection linear-elastic beam theory only.",
            "The estimate is not finite-element analysis or safety certification.",
        ],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    else:
        print(_paint("NeuroCAD beam analysis", "1;36"))
        print("  Euler-Bernoulli / end-loaded rectangular cantilever")
        print(_paint("\nResponse", "1"))
        print(f"  stress        {result.maximum_stress_mpa:.6g} MPa")
        print(f"  deflection    {_format_mm(result.tip_deflection_mm)}")
        print(f"  strain        {result.strain:.6g}")
        print(f"  second moment {result.second_moment_mm4:.6g} mm^4")
        safety = "not evaluated" if result.safety_factor is None else f"{result.safety_factor:.6g}"
        print(f"  safety factor {safety}")
        print("\n  Analytical estimate only; validate material, loading, and geometry independently.")
    return 0


def cmd_physics(args: argparse.Namespace) -> int:
    from collections.abc import Callable
    from dataclasses import MISSING, fields

    from core.json_io import strict_json_loads
    from core.physics import (
        EulerBucklingInput,
        InternalPipeFlowInput,
        SteadyConductionInput,
        ThermalExpansionInput,
        ThinWallCylinderInput,
        euler_buckling,
        internal_pipe_flow,
        steady_conduction,
        thermal_expansion,
        thin_wall_cylinder,
    )

    source = _resolved_path(args.input)
    output = _resolved_path(args.output) if args.output else None
    _require_distinct_paths(input=source, output=output)
    _require_new_paths(force=args.force, output=output)
    with source.open("rb") as handle:
        payload = handle.read(MAX_IR_INPUT_BYTES + 1)
    if len(payload) > MAX_IR_INPUT_BYTES:
        raise ValueError("physics input exceeds 1 MiB")
    request = strict_json_loads(payload.decode("utf-8"))
    if not isinstance(request, dict) or set(request) != {"model", "inputs"}:
        raise ValueError("physics input requires exactly model and inputs")
    if not isinstance(request["model"], str) or not isinstance(request["inputs"], dict):
        raise TypeError("physics model must be a string and inputs must be an object")
    models: dict[str, tuple[type[Any], Callable[[Any], dict[str, Any]]]] = {
        "euler_buckling": (EulerBucklingInput, euler_buckling),
        "thermal_expansion": (ThermalExpansionInput, thermal_expansion),
        "steady_conduction": (SteadyConductionInput, steady_conduction),
        "internal_pipe_flow": (InternalPipeFlowInput, internal_pipe_flow),
        "thin_wall_cylinder": (ThinWallCylinderInput, thin_wall_cylinder),
    }
    if request["model"] not in models:
        raise ValueError("unsupported physics model; use " + ", ".join(sorted(models)))
    input_type, evaluate = models[request["model"]]
    allowed = {field.name for field in fields(input_type)}
    required = {field.name for field in fields(input_type) if field.default is MISSING and field.default_factory is MISSING}
    supplied = set(request["inputs"])
    if not required <= supplied or supplied - allowed:
        raise ValueError(f"{request['model']} inputs require {sorted(required)} and allow {sorted(allowed - required)}")
    result = evaluate(input_type(**request["inputs"]))
    report = {
        "schema_version": "neurocad-physics-v1",
        "requested_model": request["model"],
        **result,
    }
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if output:
        write_text_atomic(output, text)
    print(text, end="")
    return 0


def _run_enclosure_interpretation(args: argparse.Namespace, *, human_default: bool) -> int:
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
    human = (human_default or getattr(args, "human", False)) and not getattr(args, "json", False)
    if output is not None:
        write_text_atomic(output, encoded)
    if human:
        _print_interpretation(interpretation)
        if output is not None:
            print(f"\n  analysis     {output}")
    elif output is None:
        print(encoded, end="")
    else:
        print(output)
    if project is not None and project_output is not None:
        write_project(project_output, project)
        print(f"  project      {project_output}" if human else project_output)
    elif project_output is not None:
        _show_errors([issue.message for issue in interpretation.issues])
    return 0 if interpretation.ready else 2


def cmd_enclosure_interpret(args: argparse.Namespace) -> int:
    return _run_enclosure_interpretation(args, human_default=False)


def cmd_nlp(args: argparse.Namespace) -> int:
    return _run_enclosure_interpretation(args, human_default=True)


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
    payload = report.to_dict()
    if args.bundle:
        from core.workflow import verified_material_report

        payload["compiled_geometry"] = verified_material_report(
            project,
            _resolved_path(args.bundle),
            density_g_cm3=args.density,
            material_cost_per_kg=args.material_cost,
        )
    print(json.dumps(payload, indent=2, sort_keys=True))
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
    dataset = parse_calibration_dataset(read_bounded_utf8(source, max_bytes=MAX_CALIBRATION_JSON_BYTES, label="calibration dataset"))
    profile = fit_calibration_profile(dataset)
    write_text_atomic(output, serialize_calibration_profile(profile) + "\n")
    print(output)
    return 0


def cmd_calibration_inspect(args: argparse.Namespace) -> int:
    from core.calibration import MAX_CALIBRATION_JSON_BYTES, parse_calibration_profile

    source = _resolved_path(args.profile)
    profile = parse_calibration_profile(read_bounded_utf8(source, max_bytes=MAX_CALIBRATION_JSON_BYTES, label="calibration profile"))
    print(json.dumps(profile.to_dict(), indent=2, sort_keys=True, allow_nan=False))
    return 0


def _read_calibration_profile(path_value: str):
    from core.calibration import MAX_CALIBRATION_JSON_BYTES, parse_calibration_profile

    source = _resolved_path(path_value)
    return parse_calibration_profile(read_bounded_utf8(source, max_bytes=MAX_CALIBRATION_JSON_BYTES, label="calibration profile"))


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
    manifest = strict_json_loads(read_bounded_utf8(manifest_path, max_bytes=MAX_IR_INPUT_BYTES, label="exchange manifest"))
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


def cmd_fit_sample(args: argparse.Namespace) -> int:
    from core.fit_sample import cutout_fit_sample
    from core.project import read_project

    source, output = _resolved_path(args.project), _resolved_path(args.output)
    _require_distinct_paths(source=source, output=output)
    _require_new_path(output, label="fit sample")
    sample = cutout_fit_sample(read_project(source), args.cutout, margin_mm=args.margin)
    write_text_atomic(output, serialize_ir_json(sample))
    print(str(output))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neurocad",
        description="Conversational CAD projects with validated, reproducible geometry artifacts.",
        epilog=(
            "examples:\n"
            "  neurocad 'a 120 x 80 x 4 mm plate with four 4 mm holes'\n"
            "  neurocad nlp 'design an enclosure 10 x 7 x 3 cm with walls 2 mm'\n"
            "  neurocad math beam --force 10 --length 50 --width 10 --thickness 4 --modulus 2200\n"
            "  neurocad jobs list --status failed\n"
            "  neurocad daemon status\n"
            "  neurocad --version"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"NeuroCAD {__version__}")
    sub = parser.add_subparsers(dest="command")

    doctor = sub.add_parser("doctor", help="Check the local NeuroCAD installation")
    doctor.add_argument("--config", help="Alternative configuration path")
    doctor.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    doctor.set_defaults(func=cmd_doctor)

    setup = sub.add_parser("setup", help="Create user configuration, runtime directories, and daemon service")
    setup.add_argument("--config", help="Alternative configuration path")
    setup.add_argument("--output-root", help="Artifact root used only when creating a new configuration")
    setup.add_argument("--no-service", action="store_true", help="Do not install a user launch service")
    setup.add_argument("--no-start", action="store_true", help="Do not activate or start the daemon")
    setup.add_argument("--repair", action="store_true", help="Stop the daemon and reinstall its service definition")
    setup.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    setup.set_defaults(func=cmd_setup)

    uninstall = sub.add_parser("uninstall", help="Stop and remove the user daemon service while preserving generated data")
    uninstall.add_argument("--config", help="Alternative configuration path")
    uninstall.add_argument("--remove-config", action="store_true", help="Also remove the configuration file")
    uninstall.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    uninstall.set_defaults(func=cmd_uninstall)

    open_parser = sub.add_parser("open", help="Open a successful job's artifact directory")
    open_parser.add_argument("job_id")
    open_parser.add_argument("--config", help="Alternative configuration path")
    open_parser.add_argument("--print-only", action="store_true", help="Print without launching a desktop application")
    open_parser.set_defaults(func=cmd_open)

    artifacts_parser = sub.add_parser("artifacts", help="Independently verify generated artifact bundles")
    artifacts_actions = artifacts_parser.add_subparsers(dest="artifacts_action", required=True)
    artifacts_verify = artifacts_actions.add_parser("verify", help="Verify every declared byte and reject undeclared files")
    artifacts_verify.add_argument("bundle", help="Artifact directory or durable job ID")
    artifacts_verify.add_argument("--config", help="Alternative configuration path")
    artifacts_verify.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    artifacts_verify.set_defaults(func=cmd_artifacts)

    profile_parser = sub.add_parser("profile", help="Measure deterministic source-generation latency and peak Python memory")
    profile_parser.add_argument("prompt", nargs="+", help="Supported engineering prompt")
    profile_parser.add_argument("--iterations", type=_positive_int, default=20)
    profile_parser.add_argument("--warmups", type=_positive_int, default=3)
    profile_parser.add_argument("--fn", type=_fn, default=64)
    profile_parser.add_argument("-o", "--output", help="New machine-readable profile path")
    profile_parser.set_defaults(func=cmd_profile)

    nlp_parser = sub.add_parser("nlp", help="Explain how enclosure language maps to a validated specification")
    nlp_parser.add_argument("prompt", nargs="+", help="Conversational but measurable enclosure requirements")
    nlp_parser.add_argument("-o", "--output", help="Optional new interpretation JSON path")
    nlp_parser.add_argument("--project-output", help="Write a project only when every requirement is resolved")
    nlp_parser.add_argument("--project-id", default="enclosure-project")
    nlp_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of the terminal analysis")
    nlp_parser.set_defaults(func=cmd_nlp)

    generate = sub.add_parser("generate", help="Generate a complete validated artifact bundle from a terminal prompt")
    generate.add_argument("prompt", nargs="+", help="Engineering prompt")
    generate.add_argument("-o", "--output", help="Explicit output directory; implies direct local execution")
    generate.add_argument(
        "--format",
        choices=["auto", "all", "ir", "scad", "stl", "preview"],
        default="auto",
        help="Artifact selection; auto includes only OpenSCAD outputs that pass local capability probes",
    )
    generate.add_argument("--fn", type=_fn)
    generate.add_argument("--timeout", type=_positive_timeout)
    generate.add_argument("--config", help="Alternative configuration path")
    generate.add_argument("--local", action="store_true", help="Bypass the daemon")
    generate.add_argument("--no-start", action="store_true", help="Fail instead of starting a stopped daemon")
    generate.add_argument("--no-wait", action="store_true", help="Print the job ID immediately")
    generate.add_argument("--wait-timeout", type=_positive_timeout, help="CLI wait limit; the daemon job continues after timeout")
    generate.add_argument("--json", action="store_true", help="Print the complete job/result record")
    generate.set_defaults(func=cmd_generate)

    agent_parser = sub.add_parser("agent", help="Plan and revise persistent conversational CAD projects")
    agent_actions = agent_parser.add_subparsers(dest="agent_action", required=True)
    agent_run = agent_actions.add_parser("run", help="Create the next progressive project revision")
    agent_run.add_argument("prompt", nargs="+", help="Natural-language design or revision request")
    agent_run.add_argument("--project", required=True, help="Persistent agent project directory")
    agent_run.add_argument("--provider", choices=["auto", "builtin", "openai", "ollama", "compatible"], default="auto")
    agent_run.add_argument("--fn", type=_fn, default=64)
    agent_run.add_argument("--json", action="store_true", help="Print the complete revision record")
    agent_run.set_defaults(func=cmd_agent_run)
    agent_inspect = agent_actions.add_parser("inspect", help="Print current plan, assumptions, and revision history")
    agent_inspect.add_argument("project")
    agent_inspect.set_defaults(func=cmd_agent_inspect)
    agent_view = agent_actions.add_parser("view", help="Open the live local project workbench")
    agent_view.add_argument("project")
    agent_view.add_argument("--host", default="127.0.0.1")
    agent_view.add_argument("--port", type=int, default=8766)
    agent_view.add_argument("--no-browser", action="store_true")
    agent_view.set_defaults(func=cmd_agent_view)

    for name, help_text in (
        ("studio", "Open the conversational CAD agent studio"),
        ("shell", "Alias for the conversational CAD agent studio"),
    ):
        shell_parser = sub.add_parser(name, help=help_text)
        shell_parser.add_argument("project", nargs="?", help="Persistent agent project directory")
        shell_parser.add_argument("--provider", choices=["auto", "builtin", "openai", "ollama", "compatible"], default="auto")
        shell_parser.add_argument("--view", action="store_true", help="Open the live project workbench")
        shell_parser.add_argument("--port", type=int, default=8766, help="Live workbench loopback port")
        shell_parser.add_argument("--config", help="Alternative configuration path")
        shell_parser.set_defaults(func=cmd_shell)

    daemon_parser = sub.add_parser("daemon", help="Manage the local generation daemon")
    daemon_actions = daemon_parser.add_subparsers(dest="daemon_action", required=True)
    for action in ("start", "stop", "restart", "status"):
        daemon_action = daemon_actions.add_parser(action)
        daemon_action.add_argument("--config", help="Alternative configuration path")
        daemon_action.add_argument("--json", action="store_true", help="Print machine-readable JSON")
        daemon_action.set_defaults(func=cmd_daemon)
    daemon_logs = daemon_actions.add_parser("logs")
    daemon_logs.add_argument("--config", help="Alternative configuration path")
    daemon_logs.add_argument("--lines", type=_positive_int, default=100)
    daemon_logs.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    daemon_logs.set_defaults(func=cmd_daemon)

    jobs_parser = sub.add_parser("jobs", help="List, inspect, wait for, retry, or cancel durable jobs")
    jobs_actions = jobs_parser.add_subparsers(dest="jobs_action", required=True)
    jobs_list = jobs_actions.add_parser("list")
    jobs_list.add_argument("--limit", type=_positive_int, default=50)
    jobs_list.add_argument("--status", choices=["queued", "running", "succeeded", "failed", "cancelled"])
    jobs_list.add_argument("--config", help="Alternative configuration path")
    jobs_list.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    jobs_list.set_defaults(func=cmd_jobs)
    for action in ("show", "cancel"):
        jobs_action = jobs_actions.add_parser(action)
        jobs_action.add_argument("job_id")
        jobs_action.add_argument("--config", help="Alternative configuration path")
        jobs_action.add_argument("--json", action="store_true", help="Print machine-readable JSON")
        jobs_action.set_defaults(func=cmd_jobs)
    jobs_wait = jobs_actions.add_parser("wait", help="Wait for a queued or running job to finish")
    jobs_wait.add_argument("job_id")
    jobs_wait.add_argument("--timeout", type=_positive_timeout)
    jobs_wait.add_argument("--config", help="Alternative configuration path")
    jobs_wait.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    jobs_wait.set_defaults(func=cmd_jobs)
    jobs_retry = jobs_actions.add_parser("retry", help="Create a new job from a finished job's request")
    jobs_retry.add_argument("job_id")
    jobs_retry.add_argument("--no-wait", action="store_true", help="Return as soon as the replacement job is queued")
    jobs_retry.add_argument("--timeout", type=_positive_timeout)
    jobs_retry.add_argument("--config", help="Alternative configuration path")
    jobs_retry.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    jobs_retry.set_defaults(func=cmd_jobs)

    config_parser = sub.add_parser("config", help="Inspect or update terminal/daemon configuration")
    config_actions = config_parser.add_subparsers(dest="config_action", required=True)
    config_show = config_actions.add_parser("show")
    config_show.add_argument("--config", help="Alternative configuration path")
    config_show.set_defaults(func=cmd_config)
    config_set = config_actions.add_parser("set")
    config_set.add_argument(
        "key",
        choices=[
            "data_root",
            "state_root",
            "output_root",
            "socket_path",
            "log_path",
            "worker_count",
            "default_fn",
            "default_timeout_seconds",
            "default_formats",
        ],
    )
    config_set.add_argument("value")
    config_set.add_argument("--config", help="Alternative configuration path")
    config_set.set_defaults(func=cmd_config)

    topology = sub.add_parser("topology", help="Analyze STL F2 homology and manifold structure, not physical validity")
    topology.add_argument("input", help="STL file, at most 32 MiB and 100,000 faces")
    topology.add_argument("-o", "--output", help="Optional new JSON report path")
    topology.add_argument("--require-closed-manifold", action="store_true", help="Exit 1 for open or singular complexes")
    topology.add_argument("--force", action="store_true", help="Explicitly replace the report file")
    topology.set_defaults(func=cmd_topology)

    tolerance = sub.add_parser("tolerance", help="Compute a validated linear or quadratic correlated tolerance stack")
    tolerance.add_argument("input", help="Tolerance JSON request; see docs/MATHEMATICS.md")
    tolerance.add_argument("-o", "--output", help="Optional new JSON report path")
    tolerance.add_argument("--force", action="store_true", help="Explicitly replace the report file")
    tolerance_output = tolerance.add_mutually_exclusive_group()
    tolerance_output.add_argument("--human", action="store_true", help="Print a terminal-oriented analysis")
    tolerance_output.add_argument("--json", action="store_true", help="Print machine-readable JSON (the default)")
    tolerance.set_defaults(func=cmd_tolerance)

    math_parser = sub.add_parser("math", help="Run auditable engineering calculations with terminal-oriented results")
    math_actions = math_parser.add_subparsers(dest="math_action", required=True)
    math_tolerance = math_actions.add_parser("tolerance", help="Analyze a linear or quadratic tolerance request")
    math_tolerance.add_argument("input", help="Tolerance JSON request; see docs/MATHEMATICS.md")
    math_tolerance.add_argument("-o", "--output", help="Optional new JSON report path")
    math_tolerance.add_argument("--force", action="store_true", help="Explicitly replace the report file")
    math_tolerance.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of the terminal analysis")
    math_tolerance.set_defaults(func=cmd_tolerance, human=True)
    math_beam = math_actions.add_parser("beam", help="Evaluate an end-loaded rectangular cantilever")
    math_beam.add_argument("--force", type=float, required=True, help="End load in newtons")
    math_beam.add_argument("--length", type=float, required=True, help="Cantilever length in millimetres")
    math_beam.add_argument("--width", type=float, required=True, help="Section width in millimetres")
    math_beam.add_argument("--thickness", type=float, required=True, help="Bending-axis thickness in millimetres")
    math_beam.add_argument("--modulus", type=float, required=True, help="Elastic modulus in MPa")
    math_beam.add_argument("--yield-strength", type=float, help="Optional yield strength in MPa")
    math_beam.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    math_beam.set_defaults(func=cmd_math_beam)

    physics = sub.add_parser("physics", help="Evaluate a bounded analytical physics constraint model")
    physics.add_argument("input", help="Physics JSON request; see docs/PHYSICS.md")
    physics.add_argument("-o", "--output", help="Optional new JSON report path")
    physics.add_argument("--force", action="store_true", help="Explicitly replace the report file")
    physics.set_defaults(func=cmd_physics)

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

    verify = sub.add_parser("verify", help="Report structural generation integrity, not kernel or physical validity")
    verify.add_argument("prompt", nargs="+", help="Fully dimensioned supported prompt")
    verify.add_argument("--json-output", help="New verification report path")
    verify.add_argument("--scad-output", help="New exact reported OpenSCAD path (valid designs only)")
    verify.add_argument("--fn", type=_fn, default=96)
    verify.add_argument("--force", action="store_true", help="Explicitly replace existing output files")
    verify.set_defaults(func=cmd_verify)

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
    benchmark_parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate the dataset before evaluation; otherwise load and validate the frozen dataset",
    )
    benchmark_parser.add_argument("--force", action="store_true", help="Explicitly replace existing dataset and result files")
    benchmark_parser.set_defaults(func=cmd_benchmark)

    data_parser = sub.add_parser("data", help="Prepare and validate project-authored benchmark datasets")
    data_actions = data_parser.add_subparsers(dest="data_action", required=True)
    data_prepare = data_actions.add_parser("prepare", help="Generate a deterministic dataset and checksum manifest")
    data_prepare.add_argument("output")
    data_prepare.add_argument("--seed", type=int, default=20260902)
    data_prepare.add_argument("--force", action="store_true")
    data_prepare.set_defaults(func=cmd_data_prepare)
    for action in ("validate", "inspect"):
        data_read = data_actions.add_parser(action, help=f"{action.title()} a frozen dataset without modifying it")
        data_read.add_argument("dataset")
        data_read.set_defaults(func=cmd_data_validate)

    research_parser = sub.add_parser("research", help="Run and freeze the controlled NeuroCAD research suite")
    research_parser.add_argument("--output", default="research/runs/NC-RUN-2026-09-03-FULL")
    research_parser.add_argument("--config", help="Reviewed JSON config; explicit CLI values override it")
    research_parser.add_argument("--run-id")
    research_parser.add_argument("--seed", type=int)
    research_parser.add_argument("--compiler-tasks", type=_positive_int)
    research_parser.add_argument("--ir-programs", type=_positive_int)
    research_parser.add_argument("--invalid-cases", type=_positive_int)
    research_parser.add_argument("--edit-cases", type=_positive_int)
    research_parser.add_argument("--constraint-ablation-cases", type=_positive_int)
    research_parser.add_argument("--kernel-samples", type=_positive_int)
    research_parser.add_argument("--fn", type=_fn)
    research_parser.add_argument("--timeout", type=_positive_timeout)
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

    fit_sample = enclosure_actions.add_parser("fit-sample", help="Extract a flat cutout coupon as canonical IR")
    fit_sample.add_argument("project")
    fit_sample.add_argument("--cutout", required=True, help="Existing body cutout ID")
    fit_sample.add_argument("--margin", type=float, default=5.0, help="Surrounding material in mm (2–50)")
    fit_sample.add_argument("-o", "--output", required=True, help="New canonical IR file; compile with neurocad compile")
    fit_sample.set_defaults(func=cmd_fit_sample)

    enclosure_interpret = enclosure_actions.add_parser("interpret", help="Interpret measurable enclosure requirements")
    enclosure_interpret.add_argument("prompt", nargs="+", help="Conversational clauses with explicit engineering dimensions")
    enclosure_interpret.add_argument("-o", "--output", help="Write the auditable interpretation JSON")
    enclosure_interpret.add_argument("--project-output", help="Write a project file only when interpretation is complete")
    enclosure_interpret.add_argument("--project-id", default="enclosure-project")
    enclosure_interpret_output = enclosure_interpret.add_mutually_exclusive_group()
    enclosure_interpret_output.add_argument("--human", action="store_true", help="Print a terminal-oriented explanation")
    enclosure_interpret_output.add_argument("--json", action="store_true", help="Print machine-readable JSON (the default)")
    enclosure_interpret.set_defaults(func=cmd_enclosure_interpret)

    enclosure_build = enclosure_actions.add_parser("build", help="Build a new collision-refusing enclosure artifact bundle")
    enclosure_build.add_argument("project", help="NeuroCAD enclosure project JSON")
    enclosure_build.add_argument("--output-dir", required=True, help="A new output directory; existing paths are refused")
    enclosure_build.add_argument("--stl", action="store_true", help="Compile and request-level verify body/lid STL files")
    enclosure_build.add_argument("--fn", type=_fn, default=64)
    enclosure_build.add_argument("--timeout", type=_positive_timeout, default=120)
    enclosure_build.set_defaults(func=cmd_enclosure_build)

    enclosure_verify = enclosure_actions.add_parser("verify", help="Rebuild and verify every source and artifact in an enclosure bundle")
    enclosure_verify.add_argument("bundle", help="Existing enclosure bundle directory")
    enclosure_verify.set_defaults(func=cmd_enclosure_verify)

    enclosure_preflight = enclosure_actions.add_parser("preflight", help="Run exact and disclosed heuristic fabrication checks")
    enclosure_preflight.add_argument("project", help="NeuroCAD enclosure project JSON")
    enclosure_preflight.add_argument("--density", type=float, help="Optional material density in g/cm^3")
    enclosure_preflight.add_argument("--material-cost", type=float, help="Optional material cost per kg; requires density")
    enclosure_preflight.add_argument("--calibration", help="Optional evidence-backed calibration profile JSON")
    enclosure_preflight.add_argument("--bundle", help="Measure solid material from a verified STL bundle matching this exact project")
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
    kicad_bind = integration_actions.add_parser("kicad-bind", help="Bind a reviewed extraction draft to the exact KiCad board bytes")
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
    kicad_apply = integration_actions.add_parser("kicad-apply", help="Apply a hash-bound PCB envelope as a new project revision")
    kicad_apply.add_argument("project", help="Source NeuroCAD enclosure project JSON")
    kicad_apply.add_argument("receipt", help="Completed bounded KiCad handoff JSON")
    kicad_apply.add_argument("--source-board", required=True, help="Exact .kicad_pcb file named by the receipt")
    kicad_apply.add_argument("-o", "--output", required=True, help="New project revision path")
    kicad_apply.add_argument("--reason", help="Optional audit reason stored in project history")
    kicad_apply.set_defaults(func=cmd_integrations_kicad_apply)

    return parser


KNOWN_COMMANDS = frozenset(
    {
        "agent",
        "artifacts",
        "benchmark",
        "calibration",
        "compile",
        "config",
        "create",
        "daemon",
        "data",
        "demo",
        "doctor",
        "enclosure",
        "evaluate",
        "export",
        "generate",
        "integrations",
        "ir",
        "jobs",
        "math",
        "nlp",
        "open",
        "physics",
        "profile",
        "research",
        "setup",
        "shell",
        "studio",
        "tolerance",
        "topology",
        "uninstall",
        "validate",
        "verify",
    }
)


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    raw_args = list(sys.argv[1:] if argv is None else argv)
    if not raw_args and sys.stdin.isatty():
        raw_args = ["studio"]
    elif raw_args and not raw_args[0].startswith("-") and raw_args[0] not in KNOWN_COMMANDS:
        suggestion = difflib.get_close_matches(raw_args[0], KNOWN_COMMANDS, n=1, cutoff=0.74)
        if suggestion and " " not in raw_args[0]:
            parser.error(f"unknown command {raw_args[0]!r}; did you mean {suggestion[0]!r}?")
        raw_args.insert(0, "generate")
    args = parser.parse_args(raw_args)
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
