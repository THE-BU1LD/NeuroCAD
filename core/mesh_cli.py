"""Optional STEP-to-mesh companion; leave the maintained CAD CLI unchanged."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .gmsh_process import DEFAULT_TIMEOUT_SECONDS, GmshProcessBackend


def cmd_step(args: argparse.Namespace) -> int:
    source = Path(args.step).expanduser()
    destination = Path(args.output_dir).expanduser()
    if source.resolve() == destination.resolve():
        raise ValueError("STEP input and mesh output directory must be distinct")
    # Preserve the original paths so the backend can reject symlink inputs.
    receipt = GmshProcessBackend(timeout_seconds=args.timeout_seconds).mesh_step(
        source, destination, min_size_mm=args.min_size, max_size_mm=args.max_size,
    )
    print(json.dumps(receipt.to_dict(), indent=2, sort_keys=True, allow_nan=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neurocad-mesh",
        description="Create a verified mesh bundle from STEP; not solver or safety certification.",
    )
    actions = parser.add_subparsers(dest="command", required=True)
    step = actions.add_parser("step", help="Import STEP and verify tagged 3-D mesh serialization")
    step.add_argument("step", help="Existing regular STEP file")
    step.add_argument("--output-dir", required=True, help="New output directory; existing paths are refused")
    step.add_argument("--max-size", type=float, required=True, help="Maximum target element size in mm")
    step.add_argument("--min-size", type=float, help="Minimum target size in mm; defaults to max(0.01, max-size/5)")
    step.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS,
                      help="Native worker wait limit, 0.1 to 3600 seconds (default: 120); not a RAM/CPU quota")
    step.set_defaults(func=cmd_step)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        code = args.func(args)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    raise SystemExit(code)


if __name__ == "__main__":
    main()
