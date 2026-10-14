"""Optional STEP-to-mesh companion; leave the maintained CAD CLI unchanged."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .gmsh_process import DEFAULT_TIMEOUT_SECONDS, GmshProcessBackend
from .json_io import read_bounded_utf8, strict_json_loads
from .mesh_roles import validate_roles


def cmd_step(args: argparse.Namespace) -> int:
    source = Path(args.step).expanduser()
    destination = Path(args.output_dir).expanduser()
    if source.resolve() == destination.resolve():
        raise ValueError("STEP input and mesh output directory must be distinct")
    # Preserve the original paths so the backend can reject symlink inputs.
    policy: dict = {} if args.minimum_sicn is None else {"minimum_sicn": args.minimum_sicn}
    if args.boundary_roles is not None:
        policy["boundary_roles"] = validate_roles(strict_json_loads(read_bounded_utf8(
            Path(args.boundary_roles), max_bytes=64 * 1024, label="boundary roles")))
    receipt = GmshProcessBackend(timeout_seconds=args.timeout_seconds).mesh_step(
        source, destination, min_size_mm=args.min_size, max_size_mm=args.max_size,
        **policy,
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
    step.add_argument("--minimum-sicn", type=float, help="Require minimum element SICN in (0, 1] before publication; not solver certification")
    step.add_argument("--boundary-roles", help="Source-bound JSON roles for planar envelope faces")
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
