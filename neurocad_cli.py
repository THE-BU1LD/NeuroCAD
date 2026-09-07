from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any

from text_to_cad import TextToCAD

__version__ = "0.4.0a1"

_VERIFICATION_SCOPE = "structural_generation_only"
_CLAIM_BOUNDARY = (
    "Checks generation integrity and design-graph structure only; it does not establish "
    "manufacturability, simulation accuracy, safety, or physical feasibility."
)
_SUPPORTED_OPERATIONS = {"union", "difference", "intersection"}


def _prompt(parts: list[str]) -> str:
    value = " ".join(parts).strip()
    if not value:
        raise SystemExit("A non-empty engineering prompt is required.")
    return value


def cmd_doctor(_: argparse.Namespace) -> int:
    checks: list[tuple[str, bool, str]] = []
    checks.append(("python>=3.10", sys.version_info >= (3, 10), platform.python_version()))
    for package in ("numpy", "trimesh"):
        try:
            module = importlib.import_module(package)
            version = getattr(module, "__version__", "installed")
            checks.append((package, True, str(version)))
        except Exception as exc:
            checks.append((package, False, str(exc)))

    try:
        generator = TextToCAD()
        scad = generator.to_scad("a compact box with two holes")
        checks.append(("generation-smoke", bool(scad.strip()), f"{len(scad)} chars"))
    except Exception as exc:
        checks.append(("generation-smoke", False, str(exc)))

    failed = False
    for name, ok, detail in checks:
        state = "OK" if ok else "FAIL"
        print(f"[{state}] {name}: {detail}")
        failed = failed or not ok
    return 1 if failed else 0


def _generate(prompt_parts: list[str], output: str, fn: int) -> Path:
    prompt = _prompt(prompt_parts)
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    TextToCAD(output_path=str(path), fn=fn).export(prompt)
    if not path.exists() or path.stat().st_size == 0:
        raise SystemExit("NeuroCAD generated an empty output file.")
    return path


def cmd_create(args: argparse.Namespace) -> int:
    path = _generate(args.prompt, args.output, args.fn)
    print(path)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    if args.format != "scad":
        raise SystemExit("This public alpha currently supports --format scad only.")
    path = _generate(args.prompt, args.output, args.fn)
    print(path)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    prompt = _prompt(args.prompt)
    doc = TextToCAD(fn=args.fn).build(prompt)
    if not doc.scad.strip():
        print("INVALID: generated OpenSCAD is empty", file=sys.stderr)
        return 1
    if not getattr(doc, "design", None):
        print("INVALID: no design graph was produced", file=sys.stderr)
        return 1
    print("VALID")
    return 0


def _finite_sequence(values: Any) -> bool:
    try:
        return all(math.isfinite(float(value)) for value in values)
    except (TypeError, ValueError):
        return False


def _component_record(component: Any) -> dict[str, Any]:
    geometry = component.geometry() if callable(getattr(component, "geometry", None)) else {}
    transform = dict(getattr(component, "transform", {}) or {})
    return {
        "name": str(getattr(component, "name", "")),
        "role": str(getattr(component, "role", "")),
        "operation": str(getattr(component, "operation", "")),
        "geometry": dict(geometry or {}),
        "transform": transform,
    }


def _build_verification_bundle(prompt: str, fn: int = 96) -> tuple[dict[str, Any], str]:
    doc = TextToCAD(fn=fn).build(prompt)
    design = getattr(doc, "design", None)
    components = list(getattr(design, "components", []) or []) if design is not None else []
    connections = list(getattr(design, "connections", []) or []) if design is not None else []
    scad = str(getattr(doc, "scad", "") or "")

    names = [str(getattr(component, "name", "")) for component in components]
    component_ids = {id(component) for component in components}

    checks = [
        {
            "name": "scad_nonempty",
            "passed": bool(scad.strip()),
            "detail": f"{len(scad)} characters generated",
        },
        {
            "name": "design_graph_nonempty",
            "passed": bool(components),
            "detail": f"{len(components)} components",
        },
        {
            "name": "unique_component_names",
            "passed": bool(names) and all(names) and len(names) == len(set(names)),
            "detail": f"{len(set(names))}/{len(names)} unique names",
        },
        {
            "name": "supported_boolean_operations",
            "passed": all(
                str(getattr(component, "operation", "")) in _SUPPORTED_OPERATIONS
                for component in components
            ),
            "detail": "operations are limited to union/difference/intersection",
        },
        {
            "name": "geometry_kind_present",
            "passed": all(
                bool(
                    (component.geometry() if callable(getattr(component, "geometry", None)) else {}).get(
                        "kind"
                    )
                )
                for component in components
            ),
            "detail": "every component declares a geometry kind",
        },
        {
            "name": "finite_transforms",
            "passed": all(
                all(
                    _finite_sequence((getattr(component, "transform", {}) or {}).get(key, ()))
                    for key in ("translate", "rotate", "scale")
                )
                for component in components
            ),
            "detail": "all translate/rotate/scale entries are finite numbers",
        },
        {
            "name": "connections_resolve",
            "passed": all(
                id(getattr(connection, "a", None)) in component_ids
                and id(getattr(connection, "b", None)) in component_ids
                for connection in connections
            ),
            "detail": f"{len(connections)} graph connections resolve to emitted components",
        },
    ]

    passed = all(check["passed"] for check in checks)
    report = {
        "schema_version": 1,
        "status": "valid" if passed else "invalid",
        "verification_scope": _VERIFICATION_SCOPE,
        "claim_boundary": _CLAIM_BOUNDARY,
        "prompt": prompt,
        "fn": int(fn),
        "checks": checks,
        "design": {
            "title": str(getattr(design, "title", "")) if design is not None else "",
            "component_count": len(components),
            "connection_count": len(connections),
            "metadata": dict(getattr(design, "metadata", {}) or {}) if design is not None else {},
            "components": [_component_record(component) for component in components],
            "connections": [
                {
                    "a": str(getattr(getattr(connection, "a", None), "name", "")),
                    "b": str(getattr(getattr(connection, "b", None), "name", "")),
                    "relation": str(getattr(connection, "relation", "")),
                }
                for connection in connections
            ],
        },
        "artifact": {
            "format": "scad",
            "sha256": hashlib.sha256(scad.encode("utf-8")).hexdigest(),
            "character_count": len(scad),
            "line_count": len(scad.splitlines()),
        },
    }
    return report, scad


def build_verification_report(prompt: str, fn: int = 96) -> dict[str, Any]:
    """Build a deterministic, structural-only public-alpha verification report."""

    report, _ = _build_verification_bundle(prompt, fn=fn)
    return report


def cmd_verify(args: argparse.Namespace) -> int:
    prompt = _prompt(args.prompt)
    report, scad = _build_verification_bundle(prompt, fn=args.fn)

    if args.scad_output:
        scad_path = Path(args.scad_output).expanduser().resolve()
        scad_path.parent.mkdir(parents=True, exist_ok=True)
        scad_path.write_text(scad, encoding="utf-8")
        if not scad_path.exists() or scad_path.stat().st_size == 0:
            raise SystemExit("NeuroCAD generated an empty OpenSCAD artifact.")

    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_output:
        report_path = Path(args.json_output).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(payload, encoding="utf-8")
        print(report_path)
    else:
        print(payload, end="")

    return 0 if report["status"] == "valid" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neurocad",
        description="NeuroCAD public alpha: natural-language engineering intent to OpenSCAD geometry.",
    )
    parser.add_argument("--version", action="version", version=f"NeuroCAD {__version__}")
    sub = parser.add_subparsers(dest="command")

    doctor = sub.add_parser("doctor", help="Check the local NeuroCAD installation")
    doctor.set_defaults(func=cmd_doctor)

    create = sub.add_parser("create", help="Generate OpenSCAD from an engineering prompt")
    create.add_argument("prompt", nargs="+", help="Engineering prompt")
    create.add_argument("-o", "--output", default="generated.scad")
    create.add_argument("--fn", type=int, default=96)
    create.set_defaults(func=cmd_create)

    validate = sub.add_parser("validate", help="Parse and validate that a prompt produces a design")
    validate.add_argument("prompt", nargs="+", help="Engineering prompt")
    validate.add_argument("--fn", type=int, default=96)
    validate.set_defaults(func=cmd_validate)

    verify = sub.add_parser(
        "verify",
        help="Emit a deterministic structural verification report for a generated design",
    )
    verify.add_argument("prompt", nargs="+", help="Engineering prompt")
    verify.add_argument("--json-output", help="Write the verification manifest to this JSON path")
    verify.add_argument("--scad-output", help="Write the exact verified OpenSCAD artifact to this path")
    verify.add_argument("--fn", type=int, default=96)
    verify.set_defaults(func=cmd_verify)

    export = sub.add_parser("export", help="Export generated geometry")
    export.add_argument("prompt", nargs="+", help="Engineering prompt")
    export.add_argument("-o", "--output", default="generated.scad")
    export.add_argument("--format", choices=["scad"], default="scad")
    export.add_argument("--fn", type=int, default=96)
    export.set_defaults(func=cmd_export)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        raise SystemExit(0)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
