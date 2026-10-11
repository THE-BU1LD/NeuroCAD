"""Controlled conformance study for NeuroCAD Physics v2 provenance bindings."""

from __future__ import annotations

import argparse
import copy
import json
import math
import platform
import random
import resource
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import fields
from pathlib import Path
from typing import Any

from core.agentic import AGENT_PLAN_VERSION, AGENT_PROJECT_VERSION, AgentComponent, parse_agent_plan
from core.artifacts import write_text_atomic
from core.json_io import read_bounded_utf8, strict_json_loads
from core.physics import (
    CircularShaftTorsionInput,
    HydrostaticBuoyancyInput,
    LumpedThermalTransientInput,
    circular_shaft_torsion,
    hydrostatic_buoyancy,
    lumped_thermal_transient,
)
from core.physics_context import (
    LOAD_CASE_VERSION,
    MATERIAL_CARD_VERSION,
    PHYSICS_CONTEXT_VERSION,
    StalePhysicsBindingError,
    canonical_sha256,
    component_geometry_metrics,
    component_geometry_sha256,
    resolve_physics_context,
    verify_physics_report,
)

STUDY_VERSION = "nc-physics-v2-study-v1"
CONFIRMATORY_SEED = 20261011
EXPECTED_CONFIRMATORY_CASES = 216
EXPECTED_FAMILY_COUNTS = {
    "geometry_input_contradiction": 24,
    "load_input_contradiction": 24,
    "material_input_contradiction": 24,
    "non_geometric_mutation": 24,
    "post_result_geometry_mutation": 48,
    "stale_expected_hash": 24,
    "valid": 48,
}
MEMORY_FLOOR_MIB = 512.0
DISK_FLOOR_MIB = 2_048.0
ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = Path(__file__).resolve().parent
EXECUTION_LEDGER = STUDY_ROOT / "CONFIRMATORY_EXECUTION.json"

ModelSpec = tuple[type[Any], Callable[[Any], dict[str, Any]]]
MODELS: dict[str, ModelSpec] = {
    "circular_shaft_torsion": (CircularShaftTorsionInput, circular_shaft_torsion),
    "hydrostatic_buoyancy": (HydrostaticBuoyancyInput, hydrostatic_buoyancy),
    "lumped_thermal_transient": (LumpedThermalTransientInput, lumped_thermal_transient),
}
SOURCE_FILES = (
    "core/agentic.py",
    "core/physics.py",
    "core/physics_context.py",
    "neurocad_cli.py",
    "research/physics_v2/MODEL_SPEC.md",
    "research/physics_v2/PROTOCOL.md",
    "research/physics_v2/study.py",
    "requirements-research.lock",
)


def _canonical_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()


def _source_hashes() -> dict[str, str]:
    return {name: _sha256_file(ROOT / name) for name in SOURCE_FILES}


def _free_plus_speculative_mib() -> float | None:
    if sys.platform == "darwin":
        completed = subprocess.run(["vm_stat"], check=True, text=True, capture_output=True)
        page_size = 16_384
        pages: dict[str, int] = {}
        for line in completed.stdout.splitlines():
            if "page size of" in line:
                token = line.split("page size of", 1)[1].split("bytes", 1)[0].strip()
                page_size = int(token)
            elif ":" in line:
                key, raw = line.split(":", 1)
                raw = raw.strip().rstrip(".")
                if raw.isdigit():
                    pages[key] = int(raw)
        return (pages.get("Pages free", 0) + pages.get("Pages speculative", 0)) * page_size / 1024**2
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return float(line.split()[1]) / 1024.0
    return None


def resource_receipt(path: Path) -> dict[str, Any]:
    memory = _free_plus_speculative_mib()
    disk = shutil.disk_usage(path).free / 1024**2
    return {
        "free_plus_speculative_mib": memory,
        "disk_free_mib": disk,
        "memory_floor_mib": MEMORY_FLOOR_MIB,
        "disk_floor_mib": DISK_FLOOR_MIB,
        "admitted": memory is not None and memory >= MEMORY_FLOOR_MIB and disk >= DISK_FLOOR_MIB,
    }


def _model_result(model: str, inputs: dict[str, Any]) -> dict[str, Any]:
    input_type, evaluator = MODELS[model]
    allowed = {field.name for field in fields(input_type)}
    if set(inputs) - allowed:
        raise ValueError(f"unsupported {model} inputs")
    return evaluator(input_type(**inputs))


def _component_dict(component: AgentComponent) -> dict[str, Any]:
    return component.to_dict()


def _component_from_dict(value: dict[str, Any]) -> AgentComponent:
    return AgentComponent(
        id=value["id"],
        label=value["label"],
        part=value["part"],
        operation=value["operation"],
        shape=value["shape"],
        parameters=copy.deepcopy(value["parameters"]),
        translate=tuple(value["translate"]),
        rotate=tuple(value["rotate"]),
    )


def _agent_state(component: AgentComponent, *, revision: int = 1) -> dict[str, Any]:
    return {
        "schema_version": AGENT_PROJECT_VERSION,
        "project_id": "physics-v2-study-case",
        "revision": revision,
        "plan": {
            "version": AGENT_PLAN_VERSION,
            "title": "Physics v2 controlled study component",
            "summary": "Synthetic primitive for the frozen provenance conformance matrix.",
            "assumptions": [],
            "components": [_component_dict(component)],
        },
    }


def _shape_component(index: int, rng: random.Random) -> AgentComponent:
    shape = ("box", "rounded_box", "sphere", "cylinder", "cone", "torus")[index % 6]
    if shape == "box":
        parameters: dict[str, Any] = {"size": [rng.uniform(20, 80), rng.uniform(20, 80), rng.uniform(20, 80)]}
    elif shape == "rounded_box":
        size = [rng.uniform(30, 80), rng.uniform(30, 80), rng.uniform(20, 80)]
        parameters = {"size": size, "radius": min(size[0], size[1]) * 0.15}
    elif shape == "sphere":
        parameters = {"radius": rng.uniform(10, 35)}
    elif shape == "cylinder":
        parameters = {"radius": rng.uniform(8, 30), "height": rng.uniform(30, 120)}
    elif shape == "cone":
        parameters = {"r1": rng.uniform(10, 30), "r2": rng.uniform(2, 9), "height": rng.uniform(30, 120)}
    else:
        major = rng.uniform(20, 40)
        parameters = {"major_radius": major, "minor_radius": rng.uniform(3, major * 0.35)}
    height = float(parameters.get("height", parameters.get("radius", parameters.get("minor_radius", 20.0)) * 2.0))
    return AgentComponent(
        "component",
        "Study component",
        "study_part",
        "add",
        shape,
        parameters,
        (rng.uniform(-5, 5), rng.uniform(-5, 5), height / 2.0),
        (0.0, 0.0, 0.0),
    )


def _valid_blueprint(index: int, rng: random.Random) -> dict[str, Any]:
    family = index % 3
    if family == 0:
        radius = rng.uniform(5, 20)
        height = rng.uniform(40, 180)
        torque = rng.uniform(5, 100)
        component = AgentComponent(
            "component",
            "Study shaft",
            "shaft",
            "add",
            "cylinder",
            {"radius": radius, "height": height},
            (0.0, 0.0, height / 2.0),
        )
        inputs = {
            "torque_n_m": torque,
            "length_mm": height,
            "outer_diameter_mm": 2.0 * radius,
            "shear_modulus_mpa": 79_000.0,
            "yield_strength_mpa": 250.0,
            "safety_factor": 1.5,
        }
        context = {
            "schema_version": PHYSICS_CONTEXT_VERSION,
            "material": {
                "schema_version": MATERIAL_CARD_VERSION,
                "material_id": "controlled-steel",
                "revision": 1,
                "source": "Frozen synthetic study card; values are illustrative, not design authority.",
                "properties": {
                    "density_kg_m3": 7_850.0,
                    "shear_modulus_mpa": 79_000.0,
                    "yield_strength_mpa": 250.0,
                },
            },
            "load_case": {
                "schema_version": LOAD_CASE_VERSION,
                "case_id": "controlled-torque",
                "coordinate_system": "component-local",
                "source": "Frozen synthetic study load.",
                "values": {"torque_n_m": torque, "safety_factor": 1.5},
            },
        }
        model = "circular_shaft_torsion"
    elif family == 1:
        component = _shape_component(index, rng)
        volume = float(component_geometry_metrics(component)["volume_mm3"])
        inputs = {
            "fluid_density_kg_m3": 1_000.0,
            "depth_mm": rng.uniform(0, 2_000),
            "displaced_volume_mm3": volume,
            "object_mass_kg": max(0.001, 700.0 * volume * 1e-9),
        }
        context = {"schema_version": PHYSICS_CONTEXT_VERSION}
        model = "hydrostatic_buoyancy"
    else:
        component = _shape_component(index, rng)
        metrics = component_geometry_metrics(component)
        inputs = {
            "density_kg_m3": 2_700.0,
            "specific_heat_j_kgk": 900.0,
            "volume_mm3": float(metrics["volume_mm3"]),
            "surface_area_mm2": float(metrics["surface_area_mm2"]),
            "heat_transfer_coefficient_w_m2k": 5.0,
            "conductivity_w_mk": 205.0,
            "initial_temperature_k": 380.0,
            "ambient_temperature_k": 295.0,
            "time_s": rng.uniform(0, 600),
        }
        context = {
            "schema_version": PHYSICS_CONTEXT_VERSION,
            "material": {
                "schema_version": MATERIAL_CARD_VERSION,
                "material_id": "controlled-aluminum",
                "revision": 1,
                "source": "Frozen synthetic study card; values are illustrative, not design authority.",
                "properties": {
                    "density_kg_m3": 2_700.0,
                    "specific_heat_j_kgk": 900.0,
                    "conductivity_w_mk": 205.0,
                },
            },
        }
        model = "lumped_thermal_transient"
    return {
        "model": model,
        "inputs": inputs,
        "context": context,
        "component": _component_dict(component),
    }


def _wrong_geometry_input(case: dict[str, Any]) -> None:
    names = {
        "circular_shaft_torsion": ("outer_diameter_mm", "length_mm"),
        "hydrostatic_buoyancy": ("displaced_volume_mm3",),
        "lumped_thermal_transient": ("volume_mm3", "surface_area_mm2"),
    }[case["model"]]
    name = names[int(case["task_id"].rsplit("-", 1)[1]) % len(names)]
    case["inputs"][name] *= 1.05


def _wrong_material_input(case: dict[str, Any]) -> None:
    properties = case["context"]["material"]["properties"]
    name = min(set(properties) & set(case["inputs"]))
    properties[name] *= 1.05


def _wrong_load_input(case: dict[str, Any]) -> None:
    values = case["context"]["load_case"]["values"]
    name = min(set(values) & set(case["inputs"]))
    values[name] *= 1.05


def _mutated_component(component: AgentComponent, kind: str) -> AgentComponent:
    value = _component_dict(component)
    if kind == "parameter":
        parameters = copy.deepcopy(value["parameters"])
        if "size" in parameters:
            parameters["size"][0] *= 1.03
        else:
            name = next(key for key in ("radius", "height", "r1", "major_radius", "minor_radius") if key in parameters)
            parameters[name] *= 1.03
        value["parameters"] = parameters
    elif kind == "transform":
        value["translate"][0] += 1.0
    elif kind == "part":
        value["part"] = value["part"] + "_changed"
    elif kind == "label":
        value["label"] = value["label"] + " renamed"
    else:
        raise ValueError(f"unsupported mutation {kind}")
    return _component_from_dict(value)


def generate_confirmatory_cases(seed: int = CONFIRMATORY_SEED) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    cases: list[dict[str, Any]] = []

    def add(family: str, blueprint: dict[str, Any], expected: dict[str, Any], **extra: Any) -> dict[str, Any]:
        task_id = f"{family}-{sum(item['family'] == family for item in cases):03d}"
        case = {
            "schema_version": STUDY_VERSION,
            "task_id": task_id,
            "family": family,
            **copy.deepcopy(blueprint),
            "expected": expected,
            **extra,
        }
        cases.append(case)
        return case

    for index in range(48):
        add("valid", _valid_blueprint(index, rng), {"full_accepted": True, "deterministic": True})
    for index in range(24):
        case = add(
            "geometry_input_contradiction",
            _valid_blueprint(index, rng),
            {"full_detected": True, "hash_only_detected": False, "unbound_detected": False},
        )
        _wrong_geometry_input(case)
    for index in range(24):
        blueprint = _valid_blueprint(index * 3 if index % 2 == 0 else index * 3 + 2, rng)
        case = add(
            "material_input_contradiction",
            blueprint,
            {"full_detected": True, "hash_only_detected": False, "unbound_detected": False},
        )
        _wrong_material_input(case)
    for index in range(24):
        case = add(
            "load_input_contradiction",
            _valid_blueprint(index * 3, rng),
            {"full_detected": True, "hash_only_detected": False, "unbound_detected": False},
        )
        _wrong_load_input(case)
    for index in range(24):
        blueprint = _valid_blueprint(index, rng)
        component = _component_from_dict(blueprint["component"])
        wrong = _mutated_component(component, "transform")
        blueprint["context"]["expected_geometry_sha256"] = component_geometry_sha256(wrong)
        add(
            "stale_expected_hash",
            blueprint,
            {"full_detected": True, "hash_only_detected": True, "unbound_detected": False},
        )
    for index in range(48):
        mutation = "parameter" if index < 32 else ("transform" if index < 40 else "part")
        add(
            "post_result_geometry_mutation",
            _valid_blueprint(index, rng),
            {"full_detected": True, "hash_only_detected": True, "unbound_detected": False},
            mutation=mutation,
        )
    for index in range(24):
        mutation = "label" if index < 12 else "revision"
        add(
            "non_geometric_mutation",
            _valid_blueprint(index, rng),
            {"full_current": True, "hash_only_current": True},
            mutation=mutation,
        )
    if len(cases) != EXPECTED_CONFIRMATORY_CASES or len({case["task_id"] for case in cases}) != len(cases):
        raise AssertionError("confirmatory generator violated the frozen count or ID uniqueness")
    return cases


def generate_development_cases() -> list[dict[str, Any]]:
    all_cases = generate_confirmatory_cases(seed=20261010)
    selected = []
    counts = {
        "valid": 3,
        "geometry_input_contradiction": 2,
        "material_input_contradiction": 1,
        "load_input_contradiction": 1,
        "stale_expected_hash": 1,
        "post_result_geometry_mutation": 3,
        "non_geometric_mutation": 1,
    }
    for family, count in counts.items():
        family_cases = [case for case in all_cases if case["family"] == family]
        selected.extend(copy.deepcopy(family_cases[:count]))
    for index, case in enumerate(selected):
        case["task_id"] = f"development-{index:03d}"
    return selected


def _read_component(project: Path, component_id: str = "component") -> AgentComponent:
    state = strict_json_loads(read_bounded_utf8(project, max_bytes=4 * 1024**2, label="study project"))
    plan = parse_agent_plan(state["plan"])
    return next(item for item in plan.components if item.id == component_id)


def _context_for_case(case: dict[str, Any], project: Path) -> dict[str, Any]:
    context = copy.deepcopy(case["context"])
    expected = context.pop("expected_geometry_sha256", None)
    geometry: dict[str, Any] = {"agent_project": str(project), "component_id": "component"}
    if expected is not None:
        geometry["expected_geometry_sha256"] = expected
    context["geometry"] = geometry
    return context


def _full_report(case: dict[str, Any], project: Path) -> dict[str, Any]:
    model_result = _model_result(case["model"], case["inputs"])
    request = {"model": case["model"], "inputs": case["inputs"], "context": _context_for_case(case, project)}
    return {
        "schema_version": "neurocad-physics-v2",
        "requested_model": case["model"],
        "inputs": case["inputs"],
        "input_sha256": canonical_sha256(case["inputs"]),
        "request_sha256": canonical_sha256(request),
        **model_result,
        "bindings": resolve_physics_context(request["context"], model=case["model"], inputs=case["inputs"], base_dir=project.parent),
    }


def _hash_only_receipt(case: dict[str, Any], project: Path) -> dict[str, Any]:
    _model_result(case["model"], case["inputs"])
    component = _read_component(project)
    observed = component_geometry_sha256(component)
    expected = case["context"].get("expected_geometry_sha256")
    if expected is not None and expected != observed:
        raise StalePhysicsBindingError("hash-only geometry receipt is stale")
    return {
        "agent_project": str(project),
        "component_id": component.id,
        "geometry_sha256": observed,
    }


def _hash_only_verify(receipt: dict[str, Any]) -> bool:
    component = _read_component(Path(receipt["agent_project"]), receipt["component_id"])
    return component_geometry_sha256(component) == receipt["geometry_sha256"]


def _write_project(path: Path, component: AgentComponent, *, revision: int = 1) -> None:
    write_text_atomic(path, _canonical_text(_agent_state(component, revision=revision)))


def _mutate_project(path: Path, case: dict[str, Any]) -> None:
    component = _read_component(path)
    mutation = case["mutation"]
    if mutation == "revision":
        _write_project(path, component, revision=2)
    else:
        _write_project(path, _mutated_component(component, mutation), revision=2)


def _timed(call: Callable[[], Any]) -> tuple[Any, float]:
    start = time.perf_counter_ns()
    value = call()
    return value, (time.perf_counter_ns() - start) / 1_000_000.0


def execute_case(case: dict[str, Any], work: Path) -> dict[str, Any]:
    project = (work / f"{case['task_id']}.project.json").resolve()
    _write_project(project, _component_from_dict(case["component"]))
    family = case["family"]
    record: dict[str, Any] = {
        "task_id": case["task_id"],
        "family": family,
        "model": case["model"],
        "expected": case["expected"],
        "arms": {},
    }

    full_report: dict[str, Any] | None = None
    hash_receipt: dict[str, Any] | None = None
    for arm in ("full", "hash_only", "unbound"):
        try:
            if arm == "full":
                full_report, elapsed = _timed(lambda: _full_report(case, project))
                accepted = True
            elif arm == "hash_only":
                hash_receipt, elapsed = _timed(lambda: _hash_only_receipt(case, project))
                accepted = True
            else:
                _, elapsed = _timed(lambda: _model_result(case["model"], case["inputs"]))
                accepted = True
            record["arms"][arm] = {"accepted": accepted, "detected": False, "elapsed_ms": elapsed, "error": None}
            if arm == "full" and full_report is not None:
                record["arms"][arm]["report_bytes"] = len(_canonical_text(full_report).encode("utf-8"))
        except (TypeError, ValueError) as exc:
            record["arms"][arm] = {
                "accepted": False,
                "detected": True,
                "elapsed_ms": None,
                "error": f"{type(exc).__name__}: {exc}",
            }

    if family == "valid" and full_report is not None:
        repeated = _full_report(case, project)
        record["arms"]["full"]["deterministic"] = repeated == full_report
        record["arms"]["full"]["binding_sha256"] = full_report["bindings"]["binding_sha256"]
    elif family in {"post_result_geometry_mutation", "non_geometric_mutation"}:
        if full_report is None or hash_receipt is None:
            record["execution_error"] = "a bound arm failed before the mutation"
        else:
            _mutate_project(project, case)
            verification, elapsed = _timed(lambda: verify_physics_report(full_report))
            hash_current, hash_elapsed = _timed(lambda: _hash_only_verify(hash_receipt))
            record["arms"]["full"].update(
                {"detected": not verification["current"], "current": verification["current"], "verify_elapsed_ms": elapsed}
            )
            record["arms"]["hash_only"].update({"detected": not hash_current, "current": hash_current, "verify_elapsed_ms": hash_elapsed})
            record["arms"]["unbound"].update(
                {"detected": False, "current": None, "verify_elapsed_ms": None, "error": "no geometry dependency to verify"}
            )
    return record


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total == 0:
        return None
    proportion = successes / total
    denominator = 1.0 + z**2 / total
    center = (proportion + z**2 / (2.0 * total)) / denominator
    radius = z * math.sqrt(proportion * (1.0 - proportion) / total + z**2 / (4.0 * total**2)) / denominator
    return [max(0.0, center - radius), min(1.0, center + radius)]


def exact_mcnemar_p(discordant_a: int, discordant_b: int) -> float:
    total = discordant_a + discordant_b
    if total == 0:
        return 1.0
    lower = min(discordant_a, discordant_b)
    tail = sum(math.comb(total, index) for index in range(lower + 1)) / 2**total
    return min(1.0, 2.0 * tail)


def _endpoint(records: list[dict[str, Any]], family: str, arm: str, field: str, expected: Any) -> dict[str, Any]:
    selected = [record for record in records if record["family"] == family]
    successes = sum(record["arms"][arm].get(field) == expected for record in selected)
    return {
        "successes": successes,
        "total": len(selected),
        "rate": successes / len(selected) if selected else None,
        "wilson_95": wilson_interval(successes, len(selected)),
    }


def _combined_endpoint(records: list[dict[str, Any]], families: tuple[str, ...], arm: str, field: str, expected: Any) -> dict[str, Any]:
    selected = [record for record in records if record["family"] in families]
    successes = sum(record["arms"][arm].get(field) == expected for record in selected)
    return {
        "successes": successes,
        "total": len(selected),
        "rate": successes / len(selected) if selected else None,
        "wilson_95": wilson_interval(successes, len(selected)),
    }


def analyze(records: list[dict[str, Any]]) -> dict[str, Any]:
    semantic_families = (
        "geometry_input_contradiction",
        "material_input_contradiction",
        "load_input_contradiction",
    )
    endpoints = {
        "valid_full_acceptance": _endpoint(records, "valid", "full", "accepted", True),
        "valid_full_determinism": _endpoint(records, "valid", "full", "deterministic", True),
        "full_geometry_input_detection": _endpoint(records, "geometry_input_contradiction", "full", "detected", True),
        "full_material_input_detection": _endpoint(records, "material_input_contradiction", "full", "detected", True),
        "full_load_input_detection": _endpoint(records, "load_input_contradiction", "full", "detected", True),
        "full_stale_expected_hash_detection": _endpoint(records, "stale_expected_hash", "full", "detected", True),
        "hash_only_semantic_non_detection": _combined_endpoint(records, semantic_families, "hash_only", "detected", False),
        "unbound_semantic_non_detection": _combined_endpoint(records, semantic_families, "unbound", "detected", False),
        "full_post_mutation_detection": _endpoint(records, "post_result_geometry_mutation", "full", "detected", True),
        "hash_only_post_mutation_detection": _endpoint(records, "post_result_geometry_mutation", "hash_only", "detected", True),
        "unbound_post_mutation_non_detection": _endpoint(records, "post_result_geometry_mutation", "unbound", "detected", False),
        "full_non_geometric_specificity": _endpoint(records, "non_geometric_mutation", "full", "current", True),
        "hash_only_non_geometric_specificity": _endpoint(records, "non_geometric_mutation", "hash_only", "current", True),
    }
    primary = (
        "valid_full_acceptance",
        "valid_full_determinism",
        "full_geometry_input_detection",
        "full_material_input_detection",
        "full_load_input_detection",
        "full_stale_expected_hash_detection",
        "hash_only_semantic_non_detection",
        "unbound_semantic_non_detection",
        "full_post_mutation_detection",
        "hash_only_post_mutation_detection",
        "unbound_post_mutation_non_detection",
        "full_non_geometric_specificity",
        "hash_only_non_geometric_specificity",
    )
    primary_pass = all(endpoints[name]["total"] > 0 and endpoints[name]["successes"] == endpoints[name]["total"] for name in primary)
    execution_errors = [record["task_id"] for record in records if "execution_error" in record]
    timings: dict[str, list[float]] = defaultdict(list)
    for record in records:
        for arm, outcome in record["arms"].items():
            if outcome.get("elapsed_ms") is not None:
                timings[arm].append(float(outcome["elapsed_ms"]))

    timing_summary = {}
    for arm, values in timings.items():
        ordered = sorted(values)
        timing_summary[arm] = {
            "count": len(ordered),
            "median_ms": ordered[len(ordered) // 2],
            "p95_ms": ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)],
            "maximum_ms": max(ordered),
        }
    report_sizes = [
        int(record["arms"]["full"]["report_bytes"]) for record in records if record["arms"]["full"].get("report_bytes") is not None
    ]
    post = [record for record in records if record["family"] == "post_result_geometry_mutation"]
    full_only = sum(record["arms"]["full"]["detected"] and not record["arms"]["unbound"]["detected"] for record in post)
    unbound_only = sum(record["arms"]["unbound"]["detected"] and not record["arms"]["full"]["detected"] for record in post)
    return {
        "schema_version": STUDY_VERSION,
        "case_count": len(records),
        "family_counts": dict(sorted(Counter(record["family"] for record in records).items())),
        "endpoints": endpoints,
        "paired_full_vs_unbound_post_mutation": {
            "full_only": full_only,
            "unbound_only": unbound_only,
            "exact_two_sided_mcnemar_p": exact_mcnemar_p(full_only, unbound_only),
        },
        "timing_diagnostics": timing_summary,
        "report_size_bytes": {
            "count": len(report_sizes),
            "median": sorted(report_sizes)[len(report_sizes) // 2] if report_sizes else None,
            "maximum": max(report_sizes) if report_sizes else None,
        },
        "execution_errors": execution_errors,
        "disposition": "SUPPORTED_WITHIN_CONTROLLED_CONTRACT"
        if primary_pass and not execution_errors
        else ("INVALID" if execution_errors else "MIXED"),
        "claim_boundary": (
            "fixed synthetic conformance matrix; not physical validation, safety certification, enterprise CAD/CAE "
            "generalization, or algorithmic novelty"
        ),
    }


def run_study(cases: list[dict[str, Any]], output: Path, *, phase: str) -> dict[str, Any]:
    if output.exists():
        raise ValueError("output directory already exists; study outputs are append-only")
    output.mkdir(parents=True)
    work = output / "work"
    work.mkdir()
    records = [execute_case(case, work) for case in cases]
    raw_text = "".join(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n" for record in records)
    write_text_atomic(output / "raw_results.jsonl", raw_text)
    metrics = analyze(records)
    write_text_atomic(output / "metrics.json", _canonical_text(metrics))
    manifest = {
        "schema_version": STUDY_VERSION,
        "phase": phase,
        "case_count": len(cases),
        "cases_sha256": canonical_sha256(cases),
        "raw_results_sha256": _sha256_file(output / "raw_results.jsonl"),
        "metrics_sha256": _sha256_file(output / "metrics.json"),
        "source_hashes": _source_hashes(),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_status": _git("status", "--porcelain=v1"),
        "python": sys.version,
        "platform": platform.platform(),
        "maximum_rss_native_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "resource_receipt": resource_receipt(output),
        "claim_boundary": metrics["claim_boundary"],
    }
    write_text_atomic(output / "manifest.json", _canonical_text(manifest))
    shutil.rmtree(work)
    return {"metrics": metrics, "manifest": manifest}


def _load_cases(path: Path) -> list[dict[str, Any]]:
    cases = [strict_json_loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not all(isinstance(case, dict) for case in cases):
        raise ValueError("case manifest must contain one JSON object per line")
    return cases


def _validate_confirmatory_cases(cases: list[dict[str, Any]]) -> None:
    counts = dict(sorted(Counter(case.get("family") for case in cases).items()))
    if len(cases) != EXPECTED_CONFIRMATORY_CASES or len({case.get("task_id") for case in cases}) != len(cases):
        raise ValueError("confirmatory manifest violates the frozen count or task-ID uniqueness")
    if counts != EXPECTED_FAMILY_COUNTS:
        raise ValueError("confirmatory manifest violates the frozen family counts")
    if canonical_sha256(cases) != canonical_sha256(generate_confirmatory_cases()):
        raise ValueError("confirmatory manifest differs from the frozen generator output")


def materialize(cases: list[dict[str, Any]], output: Path, *, protected: bool = False) -> None:
    if output.exists():
        raise ValueError("case manifest already exists")
    if protected:
        if _git("status", "--porcelain=v1"):
            raise ValueError("confirmatory materialization requires a clean Git checkout")
        resources = resource_receipt(ROOT)
        if not resources["admitted"]:
            raise ValueError("resource admission failed; confirmatory materialization is not authorized")
        _validate_confirmatory_cases(cases)
    text = "".join(json.dumps(case, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n" for case in cases)
    write_text_atomic(output, text)


def freeze(cases_path: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError("freeze receipt already exists")
    if _git("status", "--porcelain=v1"):
        raise ValueError("freeze requires a clean Git checkout")
    resources = resource_receipt(ROOT)
    if not resources["admitted"]:
        raise ValueError("resource admission failed; confirmatory freeze is not authorized")
    cases = _load_cases(cases_path)
    _validate_confirmatory_cases(cases)
    receipt = {
        "schema_version": STUDY_VERSION,
        "protocol_status": "FROZEN_PREOUTCOME",
        "source_commit": _git("rev-parse", "HEAD"),
        "source_hashes": _source_hashes(),
        "cases_path": str(cases_path.resolve()),
        "cases_file_sha256": _sha256_file(cases_path),
        "cases_semantic_sha256": canonical_sha256(cases),
        "case_count": len(cases),
        "seed": CONFIRMATORY_SEED,
        "outcomes_observed": False,
        "resource_receipt": resources,
        "python": sys.version,
        "platform": platform.platform(),
    }
    write_text_atomic(output, _canonical_text(receipt))
    return receipt


def run_confirmatory(cases_path: Path, freeze_path: Path, output: Path) -> dict[str, Any]:
    if EXECUTION_LEDGER.exists():
        raise ValueError("confirmatory execution ledger already exists; adaptive reruns are prohibited")
    if _git("status", "--porcelain=v1"):
        raise ValueError("confirmatory execution requires a clean Git checkout")
    resources = resource_receipt(ROOT)
    if not resources["admitted"]:
        raise ValueError("resource admission failed; confirmatory execution is not authorized")
    receipt = strict_json_loads(freeze_path.read_text(encoding="utf-8"))
    if receipt.get("protocol_status") != "FROZEN_PREOUTCOME" or receipt.get("outcomes_observed") is not False:
        raise ValueError("freeze receipt is not pre-outcome and frozen")
    if receipt.get("cases_file_sha256") != _sha256_file(cases_path):
        raise ValueError("case manifest hash differs from the frozen receipt")
    if receipt.get("source_hashes") != _source_hashes():
        raise ValueError("study source differs from the frozen receipt")
    cases = _load_cases(cases_path)
    _validate_confirmatory_cases(cases)
    if output.exists():
        raise ValueError("confirmatory output directory already exists")
    started_ledger = {
        "schema_version": STUDY_VERSION,
        "status": "STARTED_SINGLE_ATTEMPT",
        "freeze_sha256": _sha256_file(freeze_path),
        "output": str(output.resolve()),
        "started_unix_seconds": time.time(),
    }
    write_text_atomic(EXECUTION_LEDGER, _canonical_text(started_ledger))
    result = run_study(cases, output, phase="confirmatory")
    ledger = {
        "schema_version": STUDY_VERSION,
        "status": "EXECUTED_ONCE",
        "freeze_sha256": _sha256_file(freeze_path),
        "output": str(output.resolve()),
        "manifest_sha256": _sha256_file(output / "manifest.json"),
        "metrics_sha256": _sha256_file(output / "metrics.json"),
        "disposition": result["metrics"]["disposition"],
    }
    write_text_atomic(EXECUTION_LEDGER, _canonical_text(ledger))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    materialize_parser = actions.add_parser("materialize")
    materialize_parser.add_argument("--phase", choices=("development", "confirmatory"), required=True)
    materialize_parser.add_argument("--output", type=Path, required=True)
    freeze_parser = actions.add_parser("freeze")
    freeze_parser.add_argument("--cases", type=Path, required=True)
    freeze_parser.add_argument("--output", type=Path, required=True)
    run_parser = actions.add_parser("run")
    run_parser.add_argument("--phase", choices=("development", "confirmatory"), required=True)
    run_parser.add_argument("--cases", type=Path)
    run_parser.add_argument("--freeze", type=Path)
    run_parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.action == "materialize":
        cases = generate_development_cases() if args.phase == "development" else generate_confirmatory_cases()
        materialize(cases, args.output, protected=args.phase == "confirmatory")
        print(_canonical_text({"case_count": len(cases), "cases_sha256": canonical_sha256(cases), "output": str(args.output)}), end="")
        return 0
    if args.action == "freeze":
        print(_canonical_text(freeze(args.cases, args.output)), end="")
        return 0
    if args.phase == "development":
        cases = generate_development_cases() if args.cases is None else _load_cases(args.cases)
        print(_canonical_text(run_study(cases, args.output, phase="development")), end="")
        return 0
    if args.cases is None or args.freeze is None:
        raise ValueError("confirmatory run requires --cases and --freeze")
    print(_canonical_text(run_confirmatory(args.cases, args.freeze, args.output)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
