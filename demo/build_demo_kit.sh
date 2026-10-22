#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR=${1:-neurocad-demo-artifacts}
NEUROCAD_CLI=${NEUROCAD_CLI:-neurocad}
PYTHON_BIN=${PYTHON_BIN:-python3}

if [ -e "$OUTPUT_DIR" ] || [ -L "$OUTPUT_DIR" ]; then
  echo "Demo output already exists; choose a new path: $OUTPUT_DIR" >&2
  exit 2
fi
command -v "$NEUROCAD_CLI" >/dev/null 2>&1 || {
  echo "neurocad is not installed or NEUROCAD_CLI is incorrect" >&2
  exit 2
}
command -v "$PYTHON_BIN" >/dev/null 2>&1 || {
  echo "python3 is required to write the evidence receipt" >&2
  exit 2
}

mkdir -p "$OUTPUT_DIR"
"$NEUROCAD_CLI" doctor >"$OUTPUT_DIR/doctor.txt"

plate_prompt="a 120 x 80 x 4 mm plate with four 4 mm holes"
"$NEUROCAD_CLI" validate "$plate_prompt" --compile --json >"$OUTPUT_DIR/plate.validation.json"
"$NEUROCAD_CLI" ir "$plate_prompt" -o "$OUTPUT_DIR/plate.ncad.json"
"$NEUROCAD_CLI" create "$plate_prompt" -o "$OUTPUT_DIR/plate.scad" --manifest "$OUTPUT_DIR/plate.manifest.json"
"$NEUROCAD_CLI" export "$plate_prompt" --format stl -o "$OUTPUT_DIR/plate.stl" \
  >"$OUTPUT_DIR/plate-export.stdout.txt" 2>"$OUTPUT_DIR/plate-export.stderr.txt"

cylinder_prompt="a cylinder with radius 20 mm and height 50 mm"
"$NEUROCAD_CLI" validate "$cylinder_prompt" --compile --json >"$OUTPUT_DIR/cylinder.validation.json"
"$NEUROCAD_CLI" ir "$cylinder_prompt" -o "$OUTPUT_DIR/cylinder.ncad.json"
"$NEUROCAD_CLI" create "$cylinder_prompt" -o "$OUTPUT_DIR/cylinder.scad" --manifest "$OUTPUT_DIR/cylinder.manifest.json"
"$NEUROCAD_CLI" export "$cylinder_prompt" --format stl -o "$OUTPUT_DIR/cylinder.stl" \
  >"$OUTPUT_DIR/cylinder-export.stdout.txt" 2>"$OUTPUT_DIR/cylinder-export.stderr.txt"

enclosure_prompt="80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm; rectangular cutout 12 x 7 mm on front at 0 x 8 mm for USB-C"
"$NEUROCAD_CLI" enclosure interpret "$enclosure_prompt" \
  -o "$OUTPUT_DIR/enclosure.interpretation.json" \
  --project-id demo-enclosure --project-output "$OUTPUT_DIR/enclosure.ncad.json"
"$NEUROCAD_CLI" enclosure build "$OUTPUT_DIR/enclosure.ncad.json" \
  --output-dir "$OUTPUT_DIR/enclosure-bundle" --stl \
  >"$OUTPUT_DIR/enclosure-build.json"
"$NEUROCAD_CLI" enclosure verify "$OUTPUT_DIR/enclosure-bundle" \
  >"$OUTPUT_DIR/enclosure-verification.json"

unsupported_prompt="design a load-rated aircraft engine mount"
if "$NEUROCAD_CLI" create "$unsupported_prompt" -o "$OUTPUT_DIR/unsupported.scad" \
  >/dev/null 2>"$OUTPUT_DIR/unsupported.stderr.txt"; then
  echo "Unsupported safety-critical prompt unexpectedly succeeded" >&2
  exit 1
fi
test ! -e "$OUTPUT_DIR/unsupported.scad"

cli_version=$("$NEUROCAD_CLI" --version)
"$PYTHON_BIN" - "$OUTPUT_DIR" "$cli_version" <<'PY'
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
receipt_path = root / "DEMO_RECEIPT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_provenance() -> dict[str, object]:
    """Bind the receipt to the active implementation without leaking local paths."""
    requested_revision = os.environ.get("NEUROCAD_SOURCE_REVISION", "").strip()
    if requested_revision and not re.fullmatch(r"[0-9a-fA-F]{40,64}", requested_revision):
        raise SystemExit("NEUROCAD_SOURCE_REVISION must be a full hexadecimal Git revision")

    module_spec = importlib.util.find_spec("neurocad_cli")
    core_spec = importlib.util.find_spec("core")
    if module_spec is None or module_spec.origin is None or core_spec is None or not core_spec.submodule_search_locations:
        raise SystemExit("could not locate the active NeuroCAD implementation")
    cli_module = Path(module_spec.origin).resolve()
    core_root = Path(next(iter(core_spec.submodule_search_locations))).resolve()
    source_files = {"neurocad_cli.py": cli_module}
    source_files.update({f"core/{path.relative_to(core_root)}": path for path in sorted(core_root.rglob("*.py"))})
    file_hashes = {name: sha256(path) for name, path in source_files.items()}
    implementation_sha256 = hashlib.sha256(
        "".join(f"{name}:{digest}\n" for name, digest in sorted(file_hashes.items())).encode("ascii")
    ).hexdigest()

    revision = requested_revision.lower() or None
    revision_status = "user_supplied_unverified" if revision else "not_available_from_installed_package"
    if revision is None:
        for candidate in (cli_module.parent, *cli_module.parents):
            if not (candidate / ".git").exists():
                continue
            completed = subprocess.run(
                ["git", "-C", str(candidate), "rev-parse", "HEAD"], capture_output=True, text=True, check=False
            )
            possible_revision = completed.stdout.strip()
            if completed.returncode == 0 and re.fullmatch(r"[0-9a-fA-F]{40,64}", possible_revision):
                revision = possible_revision.lower()
                revision_status = "observed_checkout"
            break

    return {
        "source_revision": revision,
        "source_revision_status": revision_status,
        "implementation_sha256": implementation_sha256,
        "implementation_files": file_hashes,
    }


openscad = shutil.which("openscad")
if openscad is None:
    raise SystemExit("OpenSCAD disappeared after artifact compilation")
version = subprocess.run([openscad, "--version"], check=True, capture_output=True, text=True)
files = sorted(path for path in root.rglob("*") if path.is_file() and path != receipt_path)
if not files:
    raise SystemExit("demo generated no files")
for path in files:
    if path.stat().st_size == 0:
        raise SystemExit(f"demo generated an empty file: {path}")

receipt = {
    "receipt_version": "neurocad-demo-v1",
    "neurocad_version": sys.argv[2],
    "openscad": (version.stdout or version.stderr).strip(),
    "prompts": {
        "plate": "a 120 x 80 x 4 mm plate with four 4 mm holes",
        "cylinder": "a cylinder with radius 20 mm and height 50 mm",
        "enclosure": "80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm; rectangular cutout 12 x 7 mm on front at 0 x 8 mm for USB-C",
        "expected_rejection": "design a load-rated aircraft engine mount",
    },
    "artifacts": {
        str(path.relative_to(root)): {"bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in files
    },
    "implementation": source_provenance(),
    "physical_validation": "not performed",
}
receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(receipt_path)
PY

echo "Demo kit verified: $OUTPUT_DIR"
