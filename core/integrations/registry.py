"""Application registry with runtime prerequisite detection and no implied success."""

from __future__ import annotations

import importlib.util
import os
import shutil
from collections.abc import Callable, Iterable

from .model import ApplicationAdapter, Capability, CapabilityState, Prerequisite


def _executable_prerequisite(identifier: str, candidates: tuple[str, ...]) -> Prerequisite:
    executable = next((path for candidate in candidates if (path := shutil.which(candidate))), None)
    detail = f"detected executable {executable}" if executable else f"none of {', '.join(candidates)} found on PATH"
    return Prerequisite(identifier, executable is not None, detail)


def _module_prerequisite(identifier: str, module: str) -> Prerequisite:
    try:
        available = importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        available = False
    detail = f"Python module {module!r} detected" if available else f"Python module {module!r} not detected"
    return Prerequisite(identifier, available, detail)


def _environment_prerequisite(identifier: str, names: tuple[str, ...]) -> Prerequisite:
    available = all(bool(os.environ.get(name)) for name in names)
    # Report names and presence only. Credential values must never enter manifests.
    status = "present" if available else "missing"
    return Prerequisite(identifier, available, f"required environment variables are {status}: {', '.join(names)}")


def _unavailable_native(operation: str, detail: str) -> Capability:
    return Capability(operation, CapabilityState.UNAVAILABLE, (), detail)


def _openscad() -> ApplicationAdapter:
    executable = _executable_prerequisite("openscad_executable", ("openscad",))
    compile_capability = Capability(
        "compile_verified_stl",
        CapabilityState.AVAILABLE if executable.available else CapabilityState.UNAVAILABLE,
        ("stl",) if executable.available else (),
        "OpenSCAD executable detected; compilation and mesh verification have not been performed by this discovery call"
        if executable.available
        else "OpenSCAD is not detected; only native SCAD source can be emitted",
    )
    return ApplicationAdapter(
        "openscad",
        "OpenSCAD",
        (
            Capability(
                "parametric_source",
                CapabilityState.NATIVE,
                ("scad",),
                "NeuroCAD emits deterministic OpenSCAD source; this does not assert that OpenSCAD opened it",
            ),
            compile_capability,
        ),
        (executable,),
        ("SCAD output is not a BREP feature tree", "STL verification does not certify manufacturability"),
    )


def _kicad() -> ApplicationAdapter:
    executable = _executable_prerequisite("kicad_cli", ("kicad-cli",))
    return ApplicationAdapter(
        "kicad",
        "KiCad",
        (
            Capability(
                "complete_board_handoff",
                CapabilityState.FILE_EXCHANGE,
                ("json",),
                "A bounded handoff receipt is checked, then must be hash-bound to the actual board before PCB conversion",
            ),
            Capability(
                "bounded_board_parse",
                CapabilityState.VERIFIED,
                ("kicad_pcb", "json"),
                "Rectangular Edge.Cuts, thickness, and explicitly named round mounting-hole footprints are parsed and reverified",
            ),
            _unavailable_native(
                "live_ipc_control",
                "No live KiCad IPC operation is performed by this package",
            ),
        ),
        (executable,),
        (
            "Only one axis-aligned rectangular board outline is accepted",
            "Connector inventory and maximum component height require explicit mechanical review",
            "Connector cutouts and standoffs are not inferred",
        ),
    )


def _file_exchange_adapter(
    identifier: str,
    display_name: str,
    prerequisite: Prerequisite,
    *,
    operations: tuple[Capability, ...],
    native_detail: str,
    limitations: tuple[str, ...],
) -> ApplicationAdapter:
    return ApplicationAdapter(
        identifier,
        display_name,
        (*operations, _unavailable_native("native_parametric_document", native_detail)),
        (prerequisite,),
        limitations,
    )


def _fusion() -> ApplicationAdapter:
    return _file_exchange_adapter(
        "fusion",
        "Autodesk Fusion",
        _module_prerequisite("fusion_adsk_module", "adsk"),
        operations=(
            Capability(
                "mesh_import_handoff",
                CapabilityState.FILE_EXCHANGE,
                ("stl",),
                "Produces an explicit STL import manifest; no Fusion API call is made",
            ),
        ),
        native_detail="No Fusion add-in or native feature-tree writer is implemented",
        limitations=("Imported STL is a mesh, not an editable Fusion feature tree",),
    )


def _onshape() -> ApplicationAdapter:
    return _file_exchange_adapter(
        "onshape",
        "Onshape",
        _environment_prerequisite("onshape_credentials", ("ONSHAPE_ACCESS_KEY", "ONSHAPE_SECRET_KEY")),
        operations=(
            Capability(
                "mesh_import_handoff",
                CapabilityState.FILE_EXCHANGE,
                ("stl",),
                "Produces an explicit STL translation handoff; no Onshape document or API request is created",
            ),
        ),
        native_detail="Authenticated Part Studio generation is not implemented",
        limitations=("The handoff cannot create or edit a Part Studio", "Credentials are detected by presence only"),
    )


def _freecad() -> ApplicationAdapter:
    prerequisite = _executable_prerequisite("freecad_executable", ("FreeCADCmd", "freecadcmd", "freecad"))
    return _file_exchange_adapter(
        "freecad",
        "FreeCAD",
        prerequisite,
        operations=(
            Capability(
                "mesh_import_handoff",
                CapabilityState.FILE_EXCHANGE,
                ("stl",),
                "Produces an explicit mesh import handoff; FreeCAD is not launched",
            ),
            Capability(
                "openscad_source_handoff",
                CapabilityState.FILE_EXCHANGE,
                ("scad",),
                "Provides SCAD source for a user-controlled FreeCAD/OpenSCAD workflow",
            ),
        ),
        native_detail="No FCStd document or native FreeCAD feature tree is generated",
        limitations=("SCAD import behavior depends on the user's FreeCAD/OpenSCAD configuration",),
    )


def _blender() -> ApplicationAdapter:
    return _file_exchange_adapter(
        "blender",
        "Blender",
        _executable_prerequisite("blender_executable", ("blender",)),
        operations=(
            Capability(
                "mesh_import_handoff",
                CapabilityState.FILE_EXCHANGE,
                ("stl",),
                "Produces an explicit STL import handoff; Blender is not launched",
            ),
        ),
        native_detail="Blender visualization is not treated as authoritative parametric CAD",
        limitations=("Mesh import is intended for visualization, not dimensional CAD editing",),
    )


def _slicer(identifier: str, display_name: str, candidates: tuple[str, ...]) -> ApplicationAdapter:
    prerequisite = _executable_prerequisite(f"{identifier}_executable", candidates)
    return ApplicationAdapter(
        identifier,
        display_name,
        (
            Capability(
                "verified_mesh_handoff",
                CapabilityState.FILE_EXCHANGE,
                ("stl",),
                "Accepts a kernel-verified STL through file exchange; slicing is not executed or verified",
            ),
            _unavailable_native("slicer_project", "No native slicer project or print profile is generated"),
        ),
        (prerequisite,),
        ("Printer settings, supports, and toolpaths remain the slicer's responsibility",),
    )


def _build123d() -> ApplicationAdapter:
    prerequisite = _module_prerequisite("build123d_module", "build123d")
    state = CapabilityState.AVAILABLE if prerequisite.available else CapabilityState.UNAVAILABLE
    return ApplicationAdapter(
        "build123d",
        "build123d / OpenCascade",
        (
            Capability(
                "exact_feature_compile",
                state,
                ("step", "brep", "stl") if prerequisite.available else (),
                (
                    "Experimental NeuroCAD Feature IR compiler is available; execution still requires explicit build/verification"
                    if prerequisite.available
                    else "Install the exact-build123d optional dependency to enable the experimental exact-CAD compiler"
                ),
            ),
        ),
        (prerequisite,),
        (
            "Python 3.11+ is required by build123d 0.13",
            "Exact-kernel validity does not certify structural safety or manufacturability",
            "The verified v1 OpenSCAD compiler remains a separate supported path",
        ),
    )


def _cadquery() -> ApplicationAdapter:
    prerequisite = _module_prerequisite("cadquery_module", "cadquery")
    return ApplicationAdapter(
        "cadquery",
        "CadQuery / OpenCascade",
        (
            _unavailable_native(
                "exact_feature_compile",
                "CadQuery is a planned differential exact-CAD backend; the NeuroCAD compiler adapter is not implemented yet",
            ),
        ),
        (prerequisite,),
        (
            "CadQuery 2.8 requires Python 3.11+",
            "Keep CadQuery isolated from build123d 0.13 until their OCP dependency lines are proven compatible",
        ),
    )


def _planned_python_tool(identifier: str, display_name: str, module: str, operation: str) -> ApplicationAdapter:
    prerequisite = _module_prerequisite(f"{identifier}_module", module)
    return ApplicationAdapter(
        identifier,
        display_name,
        (
            _unavailable_native(
                operation,
                "Software discovery is implemented, but NeuroCAD does not execute this workflow yet",
            ),
        ),
        (prerequisite,),
        ("Presence of the Python package is not evidence that an analysis or optimization was performed",),
    )


def _planned_external_tool(
    identifier: str,
    display_name: str,
    candidates: tuple[str, ...],
    operation: str,
    formats: tuple[str, ...] = (),
) -> ApplicationAdapter:
    prerequisite = _executable_prerequisite(f"{identifier}_executable", candidates)
    return ApplicationAdapter(
        identifier,
        display_name,
        (
            Capability(
                operation,
                CapabilityState.UNAVAILABLE,
                formats,
                "Executable discovery is implemented, but the NeuroCAD execution/verification adapter is not implemented yet",
            ),
        ),
        (prerequisite,),
        ("Executable presence alone is not evidence that the external workflow succeeded",),
    )


def _gmsh() -> ApplicationAdapter:
    return _planned_external_tool(
        "gmsh",
        "Gmsh",
        ("gmsh",),
        "tagged_volume_mesh",
        ("msh", "step"),
    )


def _calculix() -> ApplicationAdapter:
    return _planned_external_tool(
        "calculix",
        "CalculiX",
        ("ccx",),
        "structural_fea",
        ("inp", "frd"),
    )


def _openfoam() -> ApplicationAdapter:
    return _planned_external_tool(
        "openfoam",
        "OpenFOAM",
        ("foamRun", "simpleFoam"),
        "cfd_simulation",
        ("foam_case", "vtk"),
    )


def _openems() -> ApplicationAdapter:
    return _planned_external_tool(
        "openems",
        "openEMS",
        ("openEMS",),
        "electromagnetic_fdtd",
        ("xml", "h5"),
    )


def _lammps() -> ApplicationAdapter:
    return _planned_external_tool(
        "lammps",
        "LAMMPS",
        ("lmp", "lmp_mpi", "lammps"),
        "atomistic_simulation",
        ("lammps_data", "dump"),
    )


def _paraview() -> ApplicationAdapter:
    return _planned_external_tool(
        "paraview",
        "ParaView",
        ("paraview", "pvpython"),
        "scientific_visualization",
        ("vtk", "vtu", "xdmf"),
    )


FACTORIES: dict[str, Callable[[], ApplicationAdapter]] = {
    "openscad": _openscad,
    "kicad": _kicad,
    "fusion": _fusion,
    "onshape": _onshape,
    "freecad": _freecad,
    "blender": _blender,
    "prusaslicer": lambda: _slicer("prusaslicer", "PrusaSlicer", ("prusa-slicer", "PrusaSlicer")),
    "orcaslicer": lambda: _slicer("orcaslicer", "OrcaSlicer", ("orca-slicer", "OrcaSlicer")),
    "bambu_studio": lambda: _slicer("bambu_studio", "Bambu Studio", ("bambu-studio", "BambuStudio")),
    "cura": lambda: _slicer("cura", "UltiMaker Cura", ("cura", "UltiMaker-Cura")),
    "build123d": _build123d,
    "cadquery": _cadquery,
    "gmsh": _gmsh,
    "calculix": _calculix,
    "openfoam": _openfoam,
    "openems": _openems,
    "lammps": _lammps,
    "paraview": _paraview,
    "openmdao": lambda: _planned_python_tool("openmdao", "OpenMDAO", "openmdao", "multidisciplinary_optimization"),
    "casadi": lambda: _planned_python_tool("casadi", "CasADi", "casadi", "nonlinear_optimization"),
    "pyvista": lambda: _planned_python_tool("pyvista", "PyVista", "pyvista", "scientific_visualization"),
}

ALIASES = {
    "open_scad": "openscad",
    "fusion360": "fusion",
    "fusion_360": "fusion",
    "autodesk_fusion": "fusion",
    "prusa_slicer": "prusaslicer",
    "orca_slicer": "orcaslicer",
    "bambustudio": "bambu_studio",
    "build_123d": "build123d",
    "open_foam": "openfoam",
    "open_ems": "openems",
}


class AdapterRegistry:
    def __init__(self, factories: dict[str, Callable[[], ApplicationAdapter]] | None = None):
        self._factories = dict(factories or FACTORIES)

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))

    def get(self, identifier: str) -> ApplicationAdapter:
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("application identifier must be a non-empty string")
        normalized = identifier.strip().lower().replace("-", "_").replace(" ", "_")
        normalized = ALIASES.get(normalized, normalized)
        factory = self._factories.get(normalized)
        if factory is None:
            raise KeyError(f"unknown integration {identifier!r}; choose one of {', '.join(self.ids())}")
        return factory()

    def describe(self, identifiers: Iterable[str] | None = None) -> tuple[ApplicationAdapter, ...]:
        selected = self.ids() if identifiers is None else tuple(identifiers)
        return tuple(self.get(identifier) for identifier in selected)


def default_registry() -> AdapterRegistry:
    return AdapterRegistry()
