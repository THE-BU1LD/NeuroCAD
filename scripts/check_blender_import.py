"""Run inside Blender after `neurocad integrations verify BUNDLE` succeeds.

blender --background --factory-startup --python scripts/check_blender_import.py -- --bundle BUNDLE --output NEW_DIR
This checks actual STL import and scale. It does not validate physical fit or a native CAD feature tree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    root = args.bundle.resolve()
    manifest_bytes = (root / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("schema_version") != "neurocad-exchange-v2" or manifest.get("units") != "mm":
        parser.error("requires a verified millimetre NeuroCAD exchange bundle")
    if args.output.exists():
        parser.error("output must be a new directory; acceptance evidence is never overwritten")
    # A separate factory-startup process owns this scene, never the user's GUI.
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"
    bpy.context.scene.unit_settings.scale_length = 1.0
    records = []
    for part in manifest["parts"]:
        artifacts = [item for item in part["artifacts"] if item["format"] == "stl"]
        if len(artifacts) != 1:
            raise ValueError("each part must contain one verified STL")
        artifact = artifacts[0]
        path = root / artifact["filename"]
        if path.is_symlink() or path.resolve().parent != root or path.suffix != ".stl":
            raise ValueError("STL must be a direct, regular bundle member")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != artifact["sha256"]:
            raise ValueError("STL bytes changed since bundle verification")
        before = set(bpy.data.objects)
        # STL has no units. NeuroCAD coordinates are millimetres; Blender's
        # internal metric length is metres, so import with an explicit 0.001 scale.
        bpy.ops.wm.stl_import(filepath=str(path), global_scale=0.001, use_scene_unit=False, use_mesh_validate=True)
        imported = set(bpy.data.objects) - before
        if len(imported) != 1:
            raise ValueError("STL import must create exactly one object per part")
        obj = imported.pop()
        if obj.type != "MESH" or not obj.data.polygons:
            raise ValueError("STL import did not create a non-empty mesh")
        bpy.context.view_layer.update()
        measured = [float(value) * 1000 for value in obj.dimensions]
        expected = part["mesh_verification"]["extents_mm"]
        if len(expected) != 3 or not all(math.isclose(a, b, rel_tol=1e-5, abs_tol=0.001) for a, b in zip(measured, expected)):
            raise ValueError(f"imported {part['id']} dimensions differ: {measured} versus {expected} mm")
        obj.name = part["id"]
        records.append({
            "part": part["id"], "filename": path.name, "sha256": digest,
            "dimensions_mm": measured, "expected_dimensions_mm": expected,
            "vertices": len(obj.data.vertices), "faces": len(obj.data.polygons),
        })
        # Separate pieces for review without changing mesh dimensions.
        obj.location.x = (len(records) - 1) * 0.12
    if len(records) not in (1, 2) or len(bpy.context.scene.objects) != len(records):
        raise ValueError("unexpected imported part count")
    args.output.mkdir(parents=True)
    bpy.ops.wm.save_as_mainfile(filepath=str((args.output / "imported.blend").resolve()))
    receipt = {
        "schema_version": "neurocad-blender-import-acceptance-v1",
        "blender_version": bpy.app.version_string,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "import_scale": 0.001, "scene_scale_length": 1.0, "display_units": "MILLIMETERS",
        "parts": records, "import_executed": True, "physical_fit_verified": False,
    }
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
