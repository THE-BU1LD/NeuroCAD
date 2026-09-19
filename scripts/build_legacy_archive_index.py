#!/usr/bin/env python3
"""Build a deterministic, hash-preserving inventory of the legacy archive."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "neurocad-legacy-archive-v1"
SOURCE_SUFFIXES = {".py", ".c", ".cc", ".cpp", ".h", ".hpp", ".js", ".ts"}
GENERATED_SUFFIXES = {".3mf", ".cad", ".obj", ".scad", ".step", ".stl", ".zip"}
CAPABILITY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("test_or_benchmark", ("test", "benchmark", "metric", "evaluation")),
    ("export_or_exchange", ("export", "step", "scad", "stl", "obj", "connector")),
    ("mesh_or_topology", ("mesh", "octree", "topology", "dual_contour", "sampling")),
    ("geometry_or_kernel", ("geometry", "kernel", "primitive", "surface", "sdf", "cad_")),
    ("physics_or_engineering", ("aero", "fatigue", "engineering", "differential")),
    ("optimization", ("optim", "critic", "determin")),
    ("learned_or_neural", ("neural", "embedding", "nlp", "intelligence")),
    ("orchestration", ("pipeline", "config", "device", "engine", "examples")),
)


def _capability(relative: str, suffix: str) -> str:
    lowered = relative.lower()
    if relative == "README.md":
        return "archive_documentation"
    if relative.startswith("generated/") or suffix in GENERATED_SUFFIXES:
        return "unverified_generated_artifact"
    for capability, terms in CAPABILITY_RULES:
        if any(term in lowered for term in terms):
            return capability
    if suffix in SOURCE_SUFFIXES:
        return "miscellaneous_source"
    return "archive_metadata"


def _failure_class(relative: str, suffix: str, data: bytes) -> tuple[str, list[str]]:
    if relative == "README.md":
        return "archive_boundary", []
    if relative.startswith("generated/") or suffix in GENERATED_SUFFIXES:
        return "unverified_output", ["not_source_bound"]
    if suffix not in SOURCE_SUFFIXES:
        return "historical_unverified", []
    text = data.decode("utf-8", errors="replace")
    risks: list[str] = []
    if "NotImplementedError" in text:
        risks.append("incomplete_implementation_marker")
    if "placeholder" in text.lower() or "pseudocode" in text.lower():
        risks.append("placeholder_or_pseudocode_marker")
    if "if __name__" not in text and any(token in text for token in (".write_", "open(", "subprocess.run(")):
        risks.append("review_import_time_side_effects")
    if relative.endswith("_legacy_broken.py"):
        risks.append("known_broken_source")
    return ("known_incomplete" if risks else "historical_unverified"), risks


def build_index(archive_root: Path) -> dict[str, Any]:
    root = archive_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"legacy archive does not exist: {root}")
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"legacy archive must not contain symlinks: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        suffix = path.suffix.lower()
        failure_class, risks = _failure_class(relative, suffix, data)
        entries.append(
            {
                "path": relative,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "capability_class": _capability(relative, suffix),
                "failure_class": failure_class,
                "risks": risks,
            }
        )
    capability_counts = Counter(entry["capability_class"] for entry in entries)
    failure_counts = Counter(entry["failure_class"] for entry in entries)
    return {
        "schema_version": SCHEMA_VERSION,
        "archive_root": archive_root.name,
        "entry_count": len(entries),
        "total_bytes": sum(int(entry["bytes"]) for entry in entries),
        "tree_sha256": hashlib.sha256("".join(f"{entry['sha256']}  {entry['path']}\n" for entry in entries).encode("utf-8")).hexdigest(),
        "capability_counts": dict(sorted(capability_counts.items())),
        "failure_counts": dict(sorted(failure_counts.items())),
        "entries": entries,
        "claim_boundary": (
            "Inventory and integrity evidence only. Archived source and generated artifacts are unsupported, "
            "unverified, and excluded from the release package."
        ),
    }


def verify_index(archive_root: Path, manifest_path: Path) -> dict[str, Any]:
    recorded = json.loads(manifest_path.read_text(encoding="utf-8"))
    current = build_index(archive_root)
    if recorded != current:
        raise ValueError("legacy archive differs from its recorded manifest")
    return {
        "status": "verified",
        "entry_count": current["entry_count"],
        "total_bytes": current["total_bytes"],
        "tree_sha256": current["tree_sha256"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("legacy"))
    parser.add_argument("--output", type=Path, default=Path("audit/legacy_archive_manifest.json"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    if args.verify:
        result = verify_index(args.archive, args.output)
        print(json.dumps(result, sort_keys=True))
        return 0
    index = build_index(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: index[key] for key in ("entry_count", "total_bytes", "tree_sha256")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
