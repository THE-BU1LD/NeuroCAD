from __future__ import annotations

import argparse
import importlib
import platform
import sys
from pathlib import Path

from text_to_cad import TextToCAD

__version__ = "0.4.0a1"


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
