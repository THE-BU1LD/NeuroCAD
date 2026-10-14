#!/usr/bin/env python3
"""Five exact-CAD goldens and three repeated tagged meshing workflows.

Analytic expectations are declared before execution. These are authored
engineering controls, not an independent CAD benchmark or physical study.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.exact_build123d import Build123dBackend
from core.feature_ir import EntitySelector, Feature, FeatureProgram, serialize_feature_ir_json
from core.gmsh_process import GmshProcessBackend
from scripts.reproduce_mesh_quality import measure_mesh


def sketch(name: str, entities: list[dict], plane: str = "XY") -> Feature:
    return Feature(id=name, kind="sketch", parameters={"plane": plane, "entities": entities, "constraints": []})


def rectangle(width: float, height: float, center: list[float] | None = None, operation: str = "add") -> dict:
    return {"kind": "rectangle", "width": width, "height": height,
            "center": [0.0, 0.0] if center is None else center, "operation": operation}


def extrude(name: str, profile: str, distance: float) -> Feature:
    return Feature(id=name, kind="extrude", inputs=(profile,), parameters={"distance": distance, "operation": "new"})


def edge_operation(name: str, source: str, kind: str, axis: list[float], amount: float) -> Feature:
    return Feature(id=name, kind=kind, inputs=(source,),
                   parameters={"radius" if kind == "fillet" else "distance": amount},
                   selectors=(EntitySelector(entity="edge", generated_by=source,
                                             predicates=({"kind": "parallel_to", "axis": axis},),
                                             role="depth_edges", unique=False),))


def golden_programs() -> dict[str, tuple[FeatureProgram, tuple[float, float, float], float]]:
    beam = (sketch("section", [rectangle(40.0, 6.0)]), extrude("beam", "section", 4.0))
    plate = (
        sketch("outline", [rectangle(40.0, 24.0)]), extrude("blank", "outline", 4.0),
        sketch("hole_profile", [{"kind": "circle", "radius": 1.5, "center": [-10.0, -6.0], "operation": "add"}]),
        extrude("hole", "hole_profile", 4.0),
        Feature(id="row", kind="linear_pattern", inputs=("hole",),
                parameters={"count": 2, "spacing": 20.0, "direction": [1.0, 0.0, 0.0]}),
        Feature(id="grid", kind="linear_pattern", inputs=("row",),
                parameters={"count": 2, "spacing": 12.0, "direction": [0.0, 1.0, 0.0]}),
        Feature(id="plate", kind="boolean_cut", inputs=("blank", "grid")),
    )
    bottle = (
        sketch("profile", [rectangle(15.0, 20.0, [7.5, 0.0]), rectangle(6.0, 8.0, [3.0, 14.0])]),
        Feature(id="bottle", kind="revolve", inputs=("profile",),
                parameters={"angle_deg": 360.0, "axis": [0.0, 1.0, 0.0], "operation": "new"}),
    )
    fillet = (Feature(id="box", kind="primitive_box", parameters={"size": [20.0, 12.0, 6.0]}),
              edge_operation("rounded", "box", "fillet", [0.0, 0.0, 1.0], 1.0))
    enclosure = (
        sketch("wall_section", [rectangle(40.0, 30.0), rectangle(36.0, 26.0, operation="subtract")]),
        extrude("walls", "wall_section", 10.0),
        Feature(id="floor", kind="primitive_box", parameters={"size": [40.0, 30.0, 4.0]}),
        Feature(id="housing", kind="boolean_union", inputs=("floor", "walls")),
        sketch("port_profile", [rectangle(8.0, 4.0, [0.0, 6.0])], plane="XZ"),
        extrude("port_tool", "port_profile", 30.0),
        edge_operation("chamfered_port", "port_tool", "chamfer", [0.0, 1.0, 0.0], 1.0),
        Feature(id="enclosure", kind="boolean_cut", inputs=("housing", "chamfered_port")),
    )
    specifications = {
        "beam": (beam, (40.0, 6.0, 4.0), 960.0),
        "patterned_plate": (plate, (40.0, 24.0, 4.0), 3840.0 - 36.0 * math.pi),
        "revolved_bottle": (bottle, (30.0, 28.0, 30.0), 4788.0 * math.pi),
        "filleted_box": (fillet, (20.0, 12.0, 6.0), 1416.0 + 6.0 * math.pi),
        "enclosure": (enclosure, (40.0, 30.0, 12.0), 6852.0),
    }
    return {name: (FeatureProgram(title=name, parameters=(), features=features,
                                  outputs=(features[-1].id,), metadata={"engineering_control": name}), extents, volume)
            for name, (features, extents, volume) in specifications.items()}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check_geometry(inspection: Any, extents: tuple[float, float, float], volume: float) -> None:
    check(inspection.valid_brep and inspection.manifold and inspection.solid_count == 1, "invalid golden topology")
    check(all(math.isclose(a, b, rel_tol=0, abs_tol=1e-6) for a, b in zip(inspection.extents_mm, extents)),
          "golden extents differ from analytic expectation")
    check(math.isclose(inspection.volume_mm3, volume, rel_tol=1e-8, abs_tol=1e-7),
          f"golden volume {inspection.volume_mm3} differs from analytic expectation {volume}")


def verify(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    sources = ["core/exact_build123d.py", "core/feature_ir.py", "core/gmsh_backend.py", "core/gmsh_process.py",
               "core/gmsh_integrity.py", "core/mesh_roles.py", "scripts/verify_native_acceptance.py",
               "scripts/reproduce_mesh_quality.py", "research/development/native_acceptance_20261014/contract.json"]
    summary: dict[str, Any] = {
        "protocol": "NEUROCAD_NATIVE_ACCEPTANCE_V1", "status": "RUNNING", "cases": [],
        "source_sha256": {name: file_hash(ROOT / name) for name in sources},
        "commit": os.environ.get("NEUROCAD_SOURCE_COMMIT", "UNKNOWN"),
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "architecture": platform.machine()},
        "claim_boundary": "Authored software controls only; no physical, independent-human or solver validation.",
    }
    try:
        protected = json.loads((ROOT / "research/physics_v3/validation_v5/freeze.json").read_text(encoding="utf-8"))["protected"]
        check(all(file_hash(ROOT / name) == digest for name, digest in protected.items()),
              "protected historical evidence changed")
        summary["protected_sha256"] = protected
        summary["environment"].update({name: version(name) for name in
                                       ("build123d", "cadquery-ocp-novtk", "gmsh", "numpy")})
        backend = Build123dBackend()
        for name, (program, extents, volume) in golden_programs().items():
            case = output / name
            case.mkdir()
            (case / "program.ncad2.json").write_text(serialize_feature_ir_json(program), encoding="utf-8")
            exact = backend.export_verified_step(program, case / "exact")
            check_geometry(exact.inspection, extents, volume)
            check(exact.roundtrip_inspection is not None, "missing STEP re-import inspection")
            check_geometry(exact.roundtrip_inspection, extents, volume)
            row: dict[str, Any] = {"name": name, "analytic_volume_mm3": volume, "extents_mm": extents,
                                   "exact": exact.to_dict(), "mesh_runs": []}
            summary["cases"].append(row)
            if name not in {"beam", "patterned_plate", "enclosure"}:
                continue
            axis = "x" if name == "beam" else "z"
            roles: dict[str, Any] = {"source_step_sha256": exact.step_sha256,
                     "roles": {"fixed_end" if name == "beam" else "base": {
                         "axis": axis, "side": "min", "expected_surfaces": 1},
                         "loaded_end" if name == "beam" else "top": {
                         "axis": axis, "side": "max", "expected_surfaces": 1}}}
            (case / "roles.json").write_text(json.dumps(roles, indent=2) + "\n", encoding="utf-8")
            for repeat in range(2):
                destination = case / f"mesh-{repeat}"
                receipt = GmshProcessBackend(timeout_seconds=120).mesh_step(
                    case / "exact/design.step", destination, min_size_mm=0.4, max_size_mm=2.0,
                    boundary_roles=roles, minimum_sicn=1e-6)
                measurement = measure_mesh(destination / "design.msh")
                tolerance = 0.025 if name == "patterned_plate" else 1e-8
                check(abs(measurement["volume_mm3"] - volume) / volume <= tolerance, "mesh volume failed independent audit")
                check(receipt.volume_entity_count == 1 and measurement["tetrahedra"] == receipt.volume_element_count,
                      "mesh topology/count mismatch")
                check(set(receipt.physical_groups) == {"domain", "boundary", *roles["roles"]}, "missing semantic role")
                check(all(math.isclose(a, b, abs_tol=1e-6, rel_tol=0) for a, b in zip(measurement["extents_mm"], extents)),
                      "mesh extent mismatch")
                row["mesh_runs"].append({"receipt": receipt.to_dict(), "measurement": measurement,
                                         "relative_volume_tolerance": tolerance})
            first, second = row["mesh_runs"]
            for key in ("node_count", "volume_element_count", "boundary_surface_count", "physical_groups"):
                check(first["receipt"][key] == second["receipt"][key], f"repeat mesh invariant changed: {key}")
            check(math.isclose(first["measurement"]["volume_mm3"], second["measurement"]["volume_mm3"], rel_tol=1e-12),
                  "repeat independent mesh volume changed")
        check(summary["source_sha256"] == {name: file_hash(ROOT / name) for name in sources}, "source changed during run")
        check(all(file_hash(ROOT / name) == digest for name, digest in protected.items()),
              "protected historical evidence changed during run")
        summary["status"] = "PASS"
    except BaseException as exc:
        summary["status"] = "FAIL"
        summary["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        manifest = {p.relative_to(output).as_posix(): file_hash(p) for p in sorted(output.rglob("*")) if p.is_file()}
        (output / "SHA256SUMS.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    result = verify(parser.parse_args().output)
    print(json.dumps({"status": result["status"], "goldens": len(result["cases"]), "mesh_runs": 6}))
