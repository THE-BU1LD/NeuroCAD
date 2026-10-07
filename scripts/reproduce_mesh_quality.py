#!/usr/bin/env python3
"""Generate and audit native STEP/MSH reference parts without a learned model.

The fixed box and through-hole plate have closed-form volumes. Gmsh's OCC
kernel constructs the STEP geometry; the maintained backend creates the mesh;
an independent determinant sum checks tetrahedral volume after reading MSH.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.gmsh_backend import GmshBackend

SOURCE_FILES = ("core/gmsh_backend.py", "core/gmsh_integrity.py", "scripts/reproduce_mesh_quality.py")
SIZES_MM = (4.0, 2.0, 1.0)
PARTS: dict[str, dict[str, Any]] = {
    "box": {"extents_mm": [20.0, 10.0, 5.0], "volume_mm3": 1000.0, "relative_volume_tolerance": 1e-9},
    "holed_plate": {"extents_mm": [20.0, 12.0, 4.0], "hole_radius_mm": 2.0,
                    "volume_mm3": 960.0 - 16.0 * math.pi, "relative_volume_tolerance": 0.025},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: sha256(ROOT / name) for name in SOURCE_FILES}


def make_step(name: str, path: Path) -> float:
    import gmsh

    if gmsh.isInitialized():
        raise RuntimeError("refusing to borrow an active Gmsh session")
    gmsh.initialize(readConfigFiles=False)
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add(name)
        spec = PARTS[name]
        dx, dy, dz = spec["extents_mm"]
        box = gmsh.model.occ.addBox(0, 0, 0, dx, dy, dz)
        if name == "holed_plate":
            hole = gmsh.model.occ.addCylinder(dx / 2, dy / 2, 0, 0, 0, dz, spec["hole_radius_mm"])
            gmsh.model.occ.cut([(3, box)], [(3, hole)])
        gmsh.model.occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        if len(volumes) != 1:
            raise ValueError("reference part must have exactly one solid")
        mass = gmsh.model.occ.getMass(3, volumes[0][1])
        if not math.isclose(mass, spec["volume_mm3"], rel_tol=1e-12, abs_tol=1e-9):
            raise ValueError("constructed CAD volume disagrees with analytic reference")
        gmsh.write(str(path))
        return float(mass)
    finally:
        gmsh.finalize()


def signed_tetra_volume(points: list[list[float]]) -> float:
    """Oriented volume from coordinates; no Gmsh quality or mass query."""
    a, b, c, d = points
    u, v, w = ([point[k] - a[k] for k in range(3)] for point in (b, c, d))
    return (u[0] * (v[1] * w[2] - v[2] * w[1])
            - u[1] * (v[0] * w[2] - v[2] * w[0])
            + u[2] * (v[0] * w[1] - v[1] * w[0])) / 6.0


def measure_mesh(path: Path) -> dict:
    import gmsh

    if gmsh.isInitialized():
        raise RuntimeError("refusing to borrow an active Gmsh session")
    gmsh.initialize(readConfigFiles=False)
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(str(path))
        tags, flat, _ = gmsh.model.mesh.getNodes()
        if not len(tags) or len(flat) != 3 * len(tags):
            raise ValueError("invalid node coordinate array")
        if any(not math.isfinite(float(x)) for x in flat):
            raise ValueError("nonfinite mesh coordinates")
        coordinates = {int(tag): [float(x) for x in flat[3 * i:3 * i + 3]] for i, tag in enumerate(tags)}
        kinds, elements, connections = gmsh.model.mesh.getElements(3)
        signed: list[float] = []
        for kind, element_tags, nodes in zip(kinds, elements, connections):
            if int(kind) != 4 or len(nodes) != 4 * len(element_tags):
                raise ValueError("this independent reference-volume audit requires linear four-node tetrahedra")
            signed.extend(signed_tetra_volume([coordinates[int(tag)] for tag in nodes[i:i + 4]])
                          for i in range(0, len(nodes), 4))
        if not signed or any(not math.isfinite(value) or value <= 0 for value in signed):
            raise ValueError("empty, inverted, degenerate, or nonfinite reference tetrahedron")
        return {"tetrahedra": len(signed), "volume_mm3": math.fsum(signed),
                "smallest_signed_tetrahedron_mm3": min(signed),
                "extents_mm": [max(x[k] for x in coordinates.values()) - min(x[k] for x in coordinates.values()) for k in range(3)]}
    finally:
        gmsh.finalize()


def reproduce(output: Path) -> dict:
    before = source_hashes()
    output.mkdir(parents=True, exist_ok=False)
    try:
        cases = []
        for name, spec in PARTS.items():
            part_dir = output / name
            part_dir.mkdir()
            source = part_dir / "source.step"
            cad_volume = make_step(name, source)
            for size in SIZES_MM:
                bundle = part_dir / f"size-{size:g}mm"
                receipt = GmshBackend().mesh_step(source, bundle, max_size_mm=size, min_size_mm=size / 5)
                measurement = measure_mesh(bundle / "design.msh")
                relative_error = abs(measurement["volume_mm3"] - spec["volume_mm3"]) / spec["volume_mm3"]
                passed = (relative_error <= spec["relative_volume_tolerance"]
                          and measurement["tetrahedra"] == receipt.volume_element_count
                          and receipt.min_sicn is not None and receipt.min_sicn > 0
                          and all(math.isclose(a, b, abs_tol=1e-7, rel_tol=0)
                                  for a, b in zip(measurement["extents_mm"], spec["extents_mm"])))
                cases.append({"part": name, "max_size_mm": size, "status": "PASS" if passed else "FAIL",
                              "analytic_volume_mm3": spec["volume_mm3"], "cad_volume_mm3": cad_volume,
                              "relative_volume_error": relative_error, "relative_volume_tolerance": spec["relative_volume_tolerance"],
                              "minimum_sicn": receipt.min_sicn, "mean_sicn": receipt.mean_sicn,
                              "bundle": bundle.relative_to(output).as_posix(), **measurement})
        after = source_hashes()
        if before != after:
            raise RuntimeError("source changed during reproduction; results cannot be published as a completed run")
        summary = {
            "protocol": "NEUROCAD_NATIVE_MESH_REFERENCE_V1", "evidence_kind": "executed native geometry engineering controls",
            "status": "PASS" if all(row["status"] == "PASS" for row in cases) else "FAIL",
            "source_sha256": before,
            "source_base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "environment": {"python": platform.python_version(), "platform": platform.platform(),
                            "gmsh": version("gmsh"), "numpy": version("numpy")},
            "cases": cases,
            "claim_boundary": [
                "Two synthetic reference CAD parts across three fixed mesh sizes; no empirical manufacturing or physics study.",
                "Positive native minSICN, serialization integrity and an independent tetrahedron-volume sum are checked.",
                "Volume agreement is not a solver-convergence, structural-safety, topology-completeness or general CAD benchmark claim.",
                "No learned parser, protected VCG stage, dataset split or closed research result was changed or rerun.",
                "STEP headers and native mesher details may differ on replay; retained hashes bind this run only.",
            ],
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n")
        lines = ["# Native STEP-to-tetrahedron reference audit", "", f"Status: **{summary['status']}**. Six native runs; two analytic reference parts.", "",
                 "| Part | Max size (mm) | Tetrahedra | Mesh volume (mm³) | Relative volume error | Minimum SICN |", "|---|---:|---:|---:|---:|---:|"]
        for row in cases:
            lines.append(f"| {row['part']} | {row['max_size_mm']:g} | {row['tetrahedra']} | {row['volume_mm3']:.6f} | {row['relative_volume_error']:.6%} | {row['minimum_sicn']:.6f} |")
        lines += ["", "The box volume is 20 × 10 × 5 = 1000 mm³. The plate is 20 × 12 × 4 mm with a radius-2 mm through hole: 960 − 16π mm³.",
                  "The fixed relative-volume tolerances are 1e-9 for the box and 2.5% for the plate; they are declared in the runner before meshing.",
                  "All STEP files, ASCII MSH files, receipts and the aggregate report are retained here. Reproduce using `python scripts/reproduce_mesh_quality.py NEW_DIRECTORY`.", "", "## Limits", ""]
        lines += [f"- {item}" for item in summary["claim_boundary"]]
        (output / "README.md").write_text("\n".join(lines) + "\n")
        artifacts = {p.relative_to(output).as_posix(): sha256(p) for p in sorted(output.rglob("*")) if p.is_file()}
        (output / "SHA256SUMS.json").write_text(json.dumps(artifacts, indent=2, sort_keys=True) + "\n")
        return summary
    except BaseException as exc:
        (output / "FAILED.json").write_text(json.dumps({"status": "FAILED", "error": str(exc), "source_sha256": before}, indent=2) + "\n")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory; existing artifacts are refused")
    result = reproduce(parser.parse_args().output)
    print(json.dumps({"status": result["status"], "cases": len(result["cases"])}))
    raise SystemExit(0 if result["status"] == "PASS" else 2)
