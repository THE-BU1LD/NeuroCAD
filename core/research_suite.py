from __future__ import annotations

import hashlib
import html
import importlib.metadata
import json
import math
import platform
import random
import statistics
import subprocess  # nosec B404
import sys
import tracemalloc
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from text_to_cad import TextToCAD

from .artifacts import compile_scad, find_openscad, render_scad_png, verify_stl, write_text_atomic
from .benchmark import BenchmarkTask, benchmark_hash, benchmark_jsonl, run_benchmark
from .ir import CADProgram, Constraint, Node, Primitive, Transform, program_bounds, validate_program
from .ir_export import program_to_scad
from .ir_parser import IRParseError, parse_ir_json, serialize_ir_json
from .program_evaluation import evaluate_program

RESEARCH_SUITE_VERSION = "neurocad-controlled-research-v1"
PROVENANCE_VERSION = "neurocad-research-provenance-v1"
DETERMINISTIC_RESULTS_VERSION = "neurocad-deterministic-results-v1"
RUN_ID = "NC-RUN-2026-09-03-FULL"
EXPERIMENT_IDS = {
    "compiler": "NC-EXP-001",
    "ir_stress": "NC-EXP-002",
    "invalid_taxonomy": "NC-EXP-003",
    "constraint_ablation": "NC-EXP-004",
    "editability": "NC-EXP-005",
    "kernel": "NC-EXP-006",
    "complexity": "NC-EXP-007",
}

_SOURCE_PATTERNS = (
    ".github/workflows/*.yml",
    "CHANGELOG.md",
    "LICENSE",
    "MANIFEST.in",
    "README.md",
    "RELEASE_STATUS.md",
    "REPRODUCIBILITY.md",
    "core/**/*.py",
    "core/schemas/*.json",
    "docs/PRODUCT_WORKFLOW.md",
    "docs/PUBLIC_ALPHA_EVIDENCE_LEDGER.md",
    "research/VERICODEGEN_2026_PROTOCOL.md",
    "research/vericodegen/**/*.json",
    "research/vericodegen/**/*.py",
    "scripts/reproduce_research.sh",
    "tests/**/*.py",
    "neurocad_cli.py",
    "pyproject.toml",
    "requirements-research.lock",
    "text_to_cad.py",
    "text_to_openscad.py",
)
_INSTALLED_SOURCE_PATTERNS = (
    "core/**/*.py",
    "core/schemas/*.json",
    "neurocad_cli.py",
    "text_to_cad.py",
    "text_to_openscad.py",
)


class _ResearchConfigTypeError(TypeError, ValueError):
    """Type error retaining ValueError compatibility for the original public API."""


@dataclass(frozen=True)
class ResearchConfig:
    seed: int = 20260902
    compiler_tasks: int = 240
    ir_programs: int = 1000
    invalid_cases: int = 240
    edit_cases: int = 200
    constraint_ablation_cases: int = 200
    kernel_samples: int = 240
    fn: int = 48
    openscad_timeout_seconds: int = 120
    force_recompile: bool = True

    def validate(self) -> None:
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise _ResearchConfigTypeError("seed must be an integer")
        for name in (
            "compiler_tasks",
            "ir_programs",
            "invalid_cases",
            "edit_cases",
            "constraint_ablation_cases",
            "kernel_samples",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool):
                raise _ResearchConfigTypeError(f"{name} must be positive")
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.compiler_tasks < 30:
            raise ValueError("compiler_tasks must be at least 30 to populate all splits")
        if self.kernel_samples > self.compiler_tasks:
            raise ValueError("kernel_samples cannot exceed compiler_tasks")
        if not isinstance(self.fn, int) or isinstance(self.fn, bool):
            raise _ResearchConfigTypeError("fn must be between 3 and 1000")
        if not 3 <= self.fn <= 1000:
            raise ValueError("fn must be between 3 and 1000")
        if not isinstance(self.openscad_timeout_seconds, int) or isinstance(self.openscad_timeout_seconds, bool):
            raise _ResearchConfigTypeError("openscad_timeout_seconds must be positive")
        if self.openscad_timeout_seconds <= 0:
            raise ValueError("openscad_timeout_seconds must be positive")
        if not isinstance(self.force_recompile, bool):
            raise _ResearchConfigTypeError("force_recompile must be a boolean")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_snapshot(project_root: Path) -> dict[str, Any]:
    """Hash maintained code, tests, workflows, packaging, and research inputs."""

    project_root = project_root.resolve()
    patterns = _SOURCE_PATTERNS if (project_root / "pyproject.toml").is_file() else _INSTALLED_SOURCE_PATTERNS
    paths = sorted(
        {
            path.resolve()
            for pattern in patterns
            for path in project_root.glob(pattern)
            if path.is_file()
        }
    )
    if not paths:
        raise RuntimeError(f"no maintained source files found below {project_root}")
    files = {path.relative_to(project_root).as_posix(): _sha256_file(path) for path in paths}
    aggregate = hashlib.sha256()
    for relative_path, file_sha256 in files.items():
        aggregate.update(relative_path.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(file_sha256.encode("ascii"))
        aggregate.update(b"\n")
    return {
        "snapshot_version": "neurocad-maintained-source-v1",
        "algorithm": "sha256(relative-path + NUL + file-sha256 + LF)",
        "sha256": aggregate.hexdigest(),
        "file_count": len(files),
        "files": files,
    }


def _project_version(project_root: Path) -> str | None:
    pyproject = project_root / "pyproject.toml"
    if not pyproject.is_file():
        return None
    in_project = False
    for raw_line in pyproject.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("["):
            in_project = line == "[project]"
        elif in_project and line.startswith("version = "):
            return line.removeprefix("version = ").strip().strip('"')
    return None


def _project_root() -> Path:
    installed_root = Path(__file__).resolve().parents[1]
    working_root = Path.cwd().resolve()
    if (working_root / "pyproject.toml").is_file() and (working_root / "core" / "research_suite.py").is_file():
        return working_root
    return installed_root


def _installed_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _command_output(arguments: list[str]) -> str | None:
    try:
        # Arguments are fixed by the caller and never evaluated through a shell.
        completed = subprocess.run(  # nosec B603
            arguments,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    output = (completed.stdout or completed.stderr).strip()
    return output or None


def _git_provenance(project_root: Path) -> dict[str, Any]:
    if not (project_root / ".git").exists():
        return {
            "commit": None,
            "dirty": None,
            "reason": "No .git metadata was available in the source snapshot.",
        }
    commit = _command_output(["git", "-C", str(project_root), "rev-parse", "HEAD"])
    try:
        # Git is used only for read-only provenance against the already selected root.
        completed = subprocess.run(  # nosec B603 B607
            ["git", "-C", str(project_root), "status", "--porcelain", "--untracked-files=all"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        status = completed.stdout.strip() if completed.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        status = None
    return {
        "commit": commit,
        "dirty": bool(status) if status is not None else None,
        "status_sha256": _sha256_text(status) if status is not None else None,
    }


def _research_provenance(project_root: Path, source_snapshot: dict[str, Any]) -> dict[str, Any]:
    openscad = find_openscad()
    openscad_path = Path(openscad) if openscad else None
    lock_path = project_root / "requirements-research.lock"
    declared_version = _project_version(project_root)
    installed_version = _installed_version("neurocad-research")
    package_names = (
        "bandit",
        "build",
        "jsonschema",
        "mypy",
        "numpy",
        "pip",
        "pip-audit",
        "pytest",
        "ruff",
        "setuptools",
        "trimesh",
        "wheel",
    )
    return {
        "provenance_version": PROVENANCE_VERSION,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "package": {
            "name": "neurocad-research",
            "declared_version": declared_version,
            "installed_distribution_version": installed_version,
            "versions_match": (
                installed_version == declared_version if installed_version is not None and declared_version is not None else None
            ),
        },
        "source": source_snapshot,
        "requirements_lock": {
            "path": "requirements-research.lock" if lock_path.is_file() else None,
            "sha256": _sha256_file(lock_path) if lock_path.is_file() else None,
        },
        "git": _git_provenance(project_root),
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "executable": sys.executable,
            "platform": platform.platform(),
        },
        "openscad": {
            "executable": openscad,
            "executable_sha256": (
                _sha256_file(openscad_path) if openscad_path is not None and openscad_path.is_file() else None
            ),
            "version_output": _command_output([openscad, "--version"]) if openscad else None,
        },
        "python_packages": {name: _installed_version(name) for name in package_names},
    }


def _is_timing_key(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in ("latency", "runtime", "tracemalloc", "elapsed"))


def _is_snapshot_only_result_key(key: str) -> bool:
    return key in {"artifact_sha256", "openscad", "previous_validation_sha256", "run_id"}


def _deterministic_copy(value: Any) -> Any:
    """Remove host-load-dependent measurements while preserving scientific outcomes."""

    if isinstance(value, dict):
        return {
            key: _deterministic_copy(child)
            for key, child in value.items()
            if not _is_timing_key(key) and not _is_snapshot_only_result_key(key)
        }
    if isinstance(value, list):
        return [_deterministic_copy(child) for child in value]
    return value


def _timing_measurements(value: Any, path: str = "$") -> dict[str, Any]:
    measurements: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if _is_timing_key(key):
                measurements[child_path] = child
            else:
                measurements.update(_timing_measurements(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            measurements.update(_timing_measurements(child, f"{path}[{index}]"))
    return measurements


def _prepare_fresh_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise FileExistsError(f"research output path is not a directory: {output_dir}")
        if next(output_dir.iterdir(), None) is not None:
            raise FileExistsError(
                f"research output directory must be new or empty; refusing to overwrite or resume {output_dir}"
            )
        return
    output_dir.mkdir(parents=True, exist_ok=False)


def _require_archival_provenance(provenance: dict[str, Any]) -> None:
    lock_sha256 = provenance["requirements_lock"]["sha256"]
    if not lock_sha256:
        raise RuntimeError("kernel-required research needs an available requirements-research.lock digest")
    package = provenance["package"]
    declared = package["declared_version"]
    installed = package["installed_distribution_version"]
    if not declared or not installed or declared != installed:
        raise RuntimeError(
            "kernel-required research needs matching declared and installed neurocad-research versions"
        )


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def _split(index: int) -> str:
    bucket = index % 10
    return "train" if bucket < 6 else "validation" if bucket < 8 else "test"


def _count_word(value: int) -> str:
    return {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}.get(value, str(value))


def generate_compiler_stress_tasks(count: int, seed: int) -> list[BenchmarkTask]:
    # This PRNG generates a deterministic benchmark; it is not security-sensitive.
    rng = random.Random(seed)  # nosec B311
    tasks: list[BenchmarkTask] = []
    prompts: set[str] = set()
    families = ("plate", "holes", "slots", "enclosure", "box", "cylinder", "sphere")
    attempts = 0
    while len(tasks) < count:
        attempts += 1
        if attempts > count * 20:
            raise RuntimeError("could not generate enough unique compiler stress tasks")
        index = len(tasks)
        split = _split(index)
        family = families[index % len(families)]
        expected: dict[str, Any]
        if family == "plate":
            width: float
            depth: float
            thickness: float
            width, depth, thickness = rng.randrange(40, 241, 5), rng.randrange(30, 181, 5), rng.choice([1.5, 2, 3, 4, 5, 6])
            if split == "validation":
                prompt = f"a plate {width} mm wide {depth} mm deep and {thickness} mm thick"
            elif split == "test":
                width_in, depth_in, thick_in = rng.choice([2, 3, 4, 5, 6]), rng.choice([1, 2, 3, 4]), rng.choice([0.1, 0.125, 0.2])
                prompt = f"a {width_in} by {depth_in} by {thick_in} inch plate"
                width, depth, thickness = width_in * 25.4, depth_in * 25.4, thick_in * 25.4
            else:
                prompt = f"a {width} x {depth} x {thickness} mm plate"
            expected = {"kind": "box", "size": [width, depth, thickness], "hole_count": 0, "slot_count": 0}
        elif family == "holes":
            width, depth, thickness = rng.randrange(60, 241, 10), rng.randrange(40, 181, 10), rng.choice([2, 3, 4, 5])
            hole_count, diameter = rng.choice([1, 2, 3, 4, 5, 6]), rng.choice([2, 3, 4, 5, 6, 8])
            if split == "test":
                width_cm, depth_cm, thick_cm, diameter_cm = width / 10, depth / 10, thickness / 10, diameter / 10
                prompt = (
                    f"a {width_cm:g} x {depth_cm:g} x {thick_cm:g} cm plate with "
                    f"{_count_word(hole_count)} {diameter_cm:g} cm holes"
                )
            else:
                prompt = f"a {width} x {depth} x {thickness} mm plate with {_count_word(hole_count)} {diameter} mm holes"
            expected = {
                "kind": "box",
                "size": [width, depth, thickness],
                "hole_count": hole_count,
                "hole_diameter": diameter,
            }
        elif family == "slots":
            width, depth, thickness = rng.randrange(80, 241, 10), rng.randrange(50, 181, 10), rng.choice([2, 3, 4, 5])
            slot_count, slot_length, slot_width = rng.choice([1, 2, 3, 4]), rng.choice([8, 10, 12, 16, 20]), rng.choice([2, 3, 4, 5])
            if split == "test":
                prompt = (
                    f"a {width / 10:g} x {depth / 10:g} x {thickness / 10:g} cm plate with "
                    f"{_count_word(slot_count)} {slot_length / 10:g} x {slot_width / 10:g} cm slots"
                )
            else:
                prompt = (
                    f"a {width} x {depth} x {thickness} mm plate with "
                    f"{_count_word(slot_count)} {slot_length} x {slot_width} mm slots"
                )
            expected = {
                "kind": "box",
                "size": [width, depth, thickness],
                "slot_count": slot_count,
                "slot_size": [slot_length, slot_width],
            }
        elif family == "enclosure":
            width, depth, height = rng.randrange(60, 201, 10), rng.randrange(50, 161, 10), rng.randrange(20, 101, 5)
            wall = rng.choice([1, 1.5, 2, 2.5, 3, 4])
            if split == "test":
                prompt = (
                    f"a {width / 10:g} x {depth / 10:g} x {height / 10:g} cm enclosure "
                    f"with {wall / 10:g} cm wall thickness"
                )
            else:
                prompt = f"a {width} x {depth} x {height} mm enclosure with {wall} mm wall thickness"
            expected = {"kind": "box", "size": [width, depth, height], "wall_thickness": wall, "open_top": True}
        elif family == "box":
            if split == "test":
                inches = [rng.choice([0.5, 1, 1.5, 2, 3, 4, 5]), rng.choice([0.5, 1, 2, 3, 4]), rng.choice([0.25, 0.5, 1, 2, 3])]
                size = [value * 25.4 for value in inches]
                prompt = f"a {inches[0]:g} by {inches[1]:g} by {inches[2]:g} inch box"
            else:
                size = [rng.randrange(10, 151, 5), rng.randrange(10, 121, 5), rng.randrange(5, 101, 5)]
                prompt = f"a {size[0]} x {size[1]} x {size[2]} mm box"
            expected = {"kind": "box", "size": size, "hole_count": 0, "slot_count": 0}
        elif family == "cylinder":
            radius, height = rng.randrange(2, 51), rng.randrange(5, 151, 5)
            if split == "test":
                prompt = f"a cylinder with radius {radius / 10:g} cm and height {height / 10:g} cm"
            else:
                prompt = f"a cylinder with radius {radius} mm and height {height} mm"
            expected = {"kind": "cylinder", "radius": radius, "height": height}
        else:
            if split == "test":
                radius_in = rng.choice([0.125, 0.25, 0.5, 1, 1.5, 2, 2.5])
                sphere_radius = radius_in * 25.4
                prompt = f"a sphere with radius {radius_in:g} inch"
            else:
                sphere_radius = float(rng.randrange(2, 76))
                prompt = f"a sphere with radius {sphere_radius:g} mm"
            expected = {"kind": "sphere", "radius": sphere_radius}
        if prompt in prompts:
            continue
        prompts.add(prompt)
        tasks.append(BenchmarkTask(f"NCR-{len(tasks) + 1:04d}", split, family, prompt, expected))
    return tasks


def _dimension_constraints(node_id: str, primitive: Primitive) -> tuple[Constraint, ...]:
    return tuple(
        Constraint("dimension", target=node_id, parameters={"parameter": name, "value": value})
        for name, value in primitive.parameters.items()
    )


def generate_ir_stress_program(index: int, rng: random.Random) -> CADProgram:
    transform = Transform(
        (rng.uniform(-100, 100), rng.uniform(-100, 100), rng.uniform(-30, 30)),
        (rng.choice([0, 15, 30, 45, 90]), rng.choice([0, 15, 30, 45]), rng.choice([0, 30, 60, 90])),
        (rng.choice([0.5, 1, 1.5, 2]), rng.choice([0.5, 1, 1.5]), rng.choice([0.5, 1, 2])),
    )
    family = index % 9
    if family == 0:
        primitive = Primitive("box", {"size": [rng.uniform(0.01, 200), rng.uniform(0.01, 150), rng.uniform(0.01, 100)]})
    elif family == 1:
        size = [rng.uniform(2, 200), rng.uniform(2, 150), rng.uniform(0.1, 100)]
        primitive = Primitive("rounded_box", {"size": size, "radius": rng.uniform(0, min(size[0], size[1]) / 2)})
    elif family == 2:
        primitive = Primitive("sphere", {"radius": rng.uniform(0.001, 100)})
    elif family == 3:
        primitive = Primitive("cylinder", {"radius": rng.uniform(0.001, 80), "height": rng.uniform(0.001, 200)})
    elif family == 4:
        primitive = Primitive(
            "cone",
            {"r1": rng.uniform(0, 80), "r2": rng.uniform(0.001, 80), "height": rng.uniform(0.001, 200)},
        )
    elif family == 5:
        major = rng.uniform(1, 100)
        primitive = Primitive("torus", {"major_radius": major, "minor_radius": rng.uniform(0.001, major * 0.9)})
    else:
        body = Primitive("box", {"size": [rng.uniform(20, 200), rng.uniform(20, 150), rng.uniform(5, 80)]})
        body_node = Node("body", primitive=body)
        if family == 6:
            radius = min(body.parameters["size"][:2]) * 0.1
            cut = Primitive("cylinder", {"radius": radius, "height": body.parameters["size"][2] * 1.5})
            nodes = (
                body_node,
                Node("cut", primitive=cut),
                Node("result", composition="difference", children=("body", "cut"), role="composition"),
            )
            constraints = (*_dimension_constraints("body", body), *_dimension_constraints("cut", cut))
        elif family == 7:
            sphere = Primitive("sphere", {"radius": min(body.parameters["size"]) * 0.6})
            nodes = (
                body_node,
                Node("accent", primitive=sphere, transform=Transform((body.parameters["size"][0] * 0.25, 0, 0))),
                Node("result", composition="union", children=("body", "accent"), role="composition"),
            )
            constraints = (*_dimension_constraints("body", body), *_dimension_constraints("accent", sphere))
        else:
            other = Primitive("box", {"size": [value * 0.8 for value in body.parameters["size"]]})
            nodes = (
                body_node,
                Node("other", primitive=other, transform=Transform((body.parameters["size"][0] * 0.05, 0, 0))),
                Node("result", composition="intersection", children=("body", "other"), role="composition"),
            )
            constraints = (*_dimension_constraints("body", body), *_dimension_constraints("other", other))
        return CADProgram(
            f"IR stress {index:04d}",
            nodes,
            ("result",),
            tuple(constraints),
            {"experiment_id": EXPERIMENT_IDS["ir_stress"], "index": index},
        )
    node = Node("body", primitive=primitive, transform=transform)
    return CADProgram(
        f"IR stress {index:04d}",
        (node,),
        ("body",),
        _dimension_constraints("body", primitive),
        {"experiment_id": EXPERIMENT_IDS["ir_stress"], "index": index},
    )


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[position]


def _wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def _mcnemar_exact(system_records: list[dict[str, Any]], baseline_records: list[dict[str, Any]]) -> dict[str, Any]:
    system = {record["task_id"]: bool(record["passed"]) for record in system_records}
    baseline = {record["task_id"]: bool(record["passed"]) for record in baseline_records}
    system_only = sum(system[key] and not baseline[key] for key in system)
    baseline_only = sum(baseline[key] and not system[key] for key in system)
    discordant = system_only + baseline_only
    if discordant == 0:
        p_value = 1.0
    else:
        lower = min(system_only, baseline_only)
        tail = sum(math.comb(discordant, value) for value in range(lower + 1)) / (2**discordant)
        p_value = min(1.0, 2 * tail)
    return {
        "system_only_correct": system_only,
        "baseline_only_correct": baseline_only,
        "discordant_pairs": discordant,
        "two_sided_exact_p": p_value,
    }


def _run_ir_stress(config: ResearchConfig) -> tuple[dict[str, Any], str, list[CADProgram]]:
    # This PRNG generates a deterministic benchmark; it is not security-sensitive.
    rng = random.Random(config.seed + 1)  # nosec B311
    programs: list[CADProgram] = []
    encoded_lines: list[str] = []
    failures: list[dict[str, Any]] = []
    latencies: list[float] = []
    tracemalloc.start()
    started = perf_counter()
    for index in range(config.ir_programs):
        program = generate_ir_stress_program(index, rng)
        programs.append(program)
        evaluation = evaluate_program(program)
        latencies.append(evaluation.evaluation_latency_ms)
        if not all(
            (
                evaluation.syntactic_validity,
                evaluation.structural_validity,
                evaluation.exact_round_trip,
                evaluation.deterministic_export,
                evaluation.constraint_satisfaction_rate == 1.0,
            )
        ):
            failures.append({"index": index, "evaluation": evaluation.to_dict()})
        encoded_lines.append(serialize_ir_json(program, pretty=False))
    elapsed = perf_counter() - started
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    passed = config.ir_programs - len(failures)
    return (
        {
            "experiment_id": EXPERIMENT_IDS["ir_stress"],
            "programs": config.ir_programs,
            "passed": passed,
            "success_rate": passed / config.ir_programs,
            "validity_scope": "static structural validity; kernel geometry is evaluated separately by NC-EXP-006",
            "kernel_evaluated_programs": 0,
            "wilson_95": _wilson(passed, config.ir_programs),
            "mean_evaluation_latency_ms": statistics.fmean(latencies),
            "p95_evaluation_latency_ms": _percentile(latencies, 0.95),
            "total_runtime_seconds": elapsed,
            "peak_tracemalloc_bytes": peak_memory,
            "failures": failures,
        },
        "\n".join(encoded_lines) + "\n",
        programs,
    )


def _base_ir_dict() -> dict[str, Any]:
    program = CADProgram(
        "taxonomy base",
        (Node("body", primitive=Primitive("box", {"size": [20, 10, 4]})),),
        ("body",),
        (Constraint("dimension", target="body", parameters={"parameter": "size", "value": [20, 10, 4]}),),
    )
    return program.to_dict()


def _invalid_case(category: str, variant: int = 0) -> tuple[str, str]:
    if isinstance(variant, bool) or not isinstance(variant, int) or variant < 0:
        raise ValueError("invalid-case variant must be a non-negative integer")
    value = _base_ir_dict()
    if category == "syntax_error":
        return "{" + " " * variant, "ir"
    if category == "type_error":
        value["nodes"][0]["primitive"]["parameters"]["size"] = [20, f"bad-{variant}", 4]
    elif category == "invalid_reference":
        value["roots"] = [f"absent-{variant}"]
    elif category == "constraint_inconsistency":
        value["constraints"][0]["parameters"]["value"] = [21 + variant / 1000, 10, 4]
    elif category == "non_finite":
        value["title"] = f"non-finite-{variant}"
        value["nodes"][0]["primitive"]["parameters"]["size"][0] = math.nan
        return json.dumps(value), "ir"
    elif category == "duplicate_id":
        value["title"] = f"duplicate-{variant}"
        value["nodes"].append(value["nodes"][0])
    elif category == "cycle":
        transform = value["nodes"][0]["transform"]
        left, right = f"a-{variant}", f"b-{variant}"
        value["nodes"] = [
            {"id": left, "composition": "union", "children": [right], "transform": transform, "role": "composition"},
            {"id": right, "composition": "union", "children": [left], "transform": transform, "role": "composition"},
        ]
        value["roots"] = [left]
        value["constraints"] = []
    elif category == "semantic_input_error":
        return f"a plate with four {variant + 1} mm holes", "prompt"
    elif category not in {
        "type_error",
        "invalid_reference",
        "constraint_inconsistency",
        "non_finite",
        "duplicate_id",
        "cycle",
    }:
        raise ValueError(f"unknown invalid-case category: {category}")
    return json.dumps(value), "ir"


def _run_invalid_taxonomy(config: ResearchConfig) -> tuple[dict[str, Any], str]:
    categories = (
        "syntax_error",
        "type_error",
        "invalid_reference",
        "constraint_inconsistency",
        "non_finite",
        "duplicate_id",
        "cycle",
        "semantic_input_error",
    )
    counts = {category: {"cases": 0, "rejected": 0} for category in categories}
    records: list[dict[str, Any]] = []
    for index in range(config.invalid_cases):
        category = categories[index % len(categories)]
        variant = index // len(categories)
        source, source_type = _invalid_case(category, variant)
        rejected = False
        message = ""
        if source_type == "prompt":
            document = TextToCAD().build(source)
            rejected = not document.validation.valid
            message = "; ".join(document.validation.errors)
        else:
            try:
                parse_ir_json(source)
            except IRParseError as exc:
                rejected = True
                message = str(exc)
        counts[category]["cases"] += 1
        counts[category]["rejected"] += int(rejected)
        records.append(
            {
                "case_id": f"NCI-{index + 1:04d}",
                "category": category,
                "fixture_variant": variant,
                "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                "rejected": rejected,
                "message": message,
            }
        )
    total_rejected = sum(record["rejected"] for record in records)
    unique_source_count = len({record["source_sha256"] for record in records})
    return (
        {
            "experiment_id": EXPERIMENT_IDS["invalid_taxonomy"],
            "cases": config.invalid_cases,
            "unique_source_count": unique_source_count,
            "category_count": len(categories),
            "rejected": total_rejected,
            "rejection_rate": total_rejected / config.invalid_cases,
            "statistical_interval": None,
            "interval_reason": "deterministic generated fixtures are not an independent random sample",
            "claim_boundary": "regression coverage over generated malformed fixtures, not a population rejection rate",
            "by_category": counts,
        },
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
    )


def _run_constraint_ablation(config: ResearchConfig) -> dict[str, Any]:
    with_constraints = 0
    without_constraints = 0
    for index in range(config.constraint_ablation_cases):
        size = [20.0 + index / 10, 10.0, 4.0]
        constraint = Constraint("dimension", target="body", parameters={"parameter": "size", "value": size})
        corrupted_size = [size[0] + 1.0, size[1], size[2]]
        node = Node("body", primitive=Primitive("box", {"size": corrupted_size}))
        constrained = CADProgram("corrupted", (node,), ("body",), (constraint,))
        unconstrained = CADProgram("corrupted", (node,), ("body",))
        with_constraints += int(not validate_program(constrained).valid)
        without_constraints += int(not validate_program(unconstrained).valid)
    return {
        "experiment_id": EXPERIMENT_IDS["constraint_ablation"],
        "cases": config.constraint_ablation_cases,
        "corruption_detection_with_constraints": with_constraints / config.constraint_ablation_cases,
        "corruption_detection_without_constraints": without_constraints / config.constraint_ablation_cases,
        "claim_boundary": "detects parameter drift against declared constraints; does not infer design intent",
    }


def _run_editability(config: ResearchConfig) -> dict[str, Any]:
    successes = 0
    latencies: list[float] = []
    for index in range(config.edit_cases):
        original = CADProgram(
            f"editable {index}",
            (Node("body", primitive=Primitive("box", {"size": [20.0 + index / 10, 10.0, 4.0]})),),
            ("body",),
        )
        node = original.nodes[0]
        edited_size = [float(node.primitive.parameters["size"][0]) + 5, 10.0, 4.0] if node.primitive else []
        edited = replace(original, nodes=(replace(node, primitive=Primitive("box", {"size": edited_size})),))
        started = perf_counter()
        report = validate_program(edited)
        if report.valid:
            recovered = parse_ir_json(serialize_ir_json(edited))
            success = recovered.nodes[0].primitive is not None and recovered.nodes[0].primitive.parameters["size"] == edited_size
            success = success and bool(program_to_scad(recovered))
        else:
            success = False
        latencies.append((perf_counter() - started) * 1000)
        successes += int(success)
    return {
        "experiment_id": EXPERIMENT_IDS["editability"],
        "cases": config.edit_cases,
        "successful_parameter_edits": successes,
        "parameter_edit_success_rate": successes / config.edit_cases,
        "wilson_95": _wilson(successes, config.edit_cases),
        "mean_edit_validate_export_ms": statistics.fmean(latencies),
        "claim_boundary": "automated declared-parameter edit, not a human usability study",
    }


def _complexity_program(depth: int) -> CADProgram:
    nodes: list[Node] = [Node("leaf_0", primitive=Primitive("box", {"size": [10, 10, 10]}))]
    child = "leaf_0"
    for level in range(1, depth):
        leaf = f"leaf_{level}"
        group = f"group_{level}"
        nodes.append(Node(leaf, primitive=Primitive("sphere", {"radius": 1}), transform=Transform((level * 0.1, 0, 0))))
        nodes.append(Node(group, composition="union", children=(child, leaf), role="composition"))
        child = group
    return CADProgram(f"complexity depth {depth}", tuple(nodes), (child,))


def _run_complexity() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for depth in (1, 2, 4, 8, 16, 32, 64, 128, 129):
        program = _complexity_program(depth)
        started = perf_counter()
        report = validate_program(program)
        if report.valid:
            scad_bytes = len(program_to_scad(program).encode("utf-8"))
        else:
            scad_bytes = 0
        rows.append(
            {
                "depth": depth,
                "node_count": len(program.nodes),
                "valid": report.valid,
                "error_codes": sorted({error.code for error in report.errors}),
                "validate_export_ms": (perf_counter() - started) * 1000,
                "scad_bytes": scad_bytes,
            }
        )
    return {"experiment_id": EXPERIMENT_IDS["complexity"], "rows": rows}


def _reuse_kernel_artifacts(
    *,
    validation_path: Path,
    ir_path: Path,
    scad_path: Path,
    stl_path: Path,
    render_path: Path,
    ir_text: str,
    scad_text: str,
    base_record: dict[str, Any],
    expected_extents: list[float],
) -> dict[str, Any] | None:
    """Revalidate a matching interrupted-run sample without recompiling it."""

    required_paths = (validation_path, ir_path, scad_path, stl_path, render_path)
    if any(not path.is_file() or path.stat().st_size == 0 for path in required_paths):
        return None
    try:
        previous = json.loads(validation_path.read_text(encoding="utf-8"))
        if not isinstance(previous, dict) or previous.get("passed") is not True:
            return None
        if any(previous.get(field) != base_record[field] for field in ("task_id", "family", "prompt")):
            return None
        if ir_path.read_text(encoding="utf-8") != ir_text or scad_path.read_text(encoding="utf-8") != scad_text:
            return None
        if render_path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        mesh = verify_stl(stl_path, expected_extents_mm=expected_extents)
    except (json.JSONDecodeError, OSError, RuntimeError, UnicodeDecodeError, ValueError):
        return None
    previous_validation_sha256 = _sha256_file(validation_path)
    return {
        **base_record,
        "expected_extents_mm": expected_extents,
        "mesh": mesh,
        "passed": True,
        "resumed_verified_artifact": True,
        "previous_validation_sha256": previous_validation_sha256,
        "artifact_sha256": {
            "ir": _sha256_file(ir_path),
            "scad": _sha256_file(scad_path),
            "stl": _sha256_file(stl_path),
            "render": _sha256_file(render_path),
        },
    }


def _run_kernel(
    config: ResearchConfig,
    tasks: list[BenchmarkTask],
    output_dir: Path,
) -> dict[str, Any]:
    executable = find_openscad()
    records: list[dict[str, Any]] = []
    if not executable:
        return {
            "experiment_id": EXPERIMENT_IDS["kernel"],
            "status": "not_run",
            "reason": "OpenSCAD not installed",
            "samples_requested": config.kernel_samples,
            "records": records,
        }
    selected: list[BenchmarkTask] = []
    by_family = {
        family: [task for task in tasks if task.family == family]
        for family in sorted({task.family for task in tasks})
    }
    offset = 0
    while len(selected) < config.kernel_samples:
        added = False
        for family_tasks in by_family.values():
            if offset < len(family_tasks):
                selected.append(family_tasks[offset])
                added = True
                if len(selected) == config.kernel_samples:
                    break
        if not added:
            break
        offset += 1
    selected = selected[: config.kernel_samples]
    kernel_dir = output_dir / "generated" / "kernel"
    for index, task in enumerate(selected):
        sample_dir = kernel_dir / f"{index + 1:03d}_{task.family}"
        document = TextToCAD(fn=config.fn).build(task.prompt)
        ir_path = sample_dir / "program.ncad.json"
        scad_path = sample_dir / "program.scad"
        stl_path = sample_dir / "program.stl"
        render_path = output_dir / "figures" / "kernel_examples" / f"{index + 1:03d}_{task.family}.png"
        validation_path = sample_dir / "validation.json"
        program = document.require_program()
        ir_text = serialize_ir_json(program)
        scad_text = program_to_scad(program, fn=config.fn)
        lower, upper = program_bounds(program)
        expected_extents = [upper[axis] - lower[axis] for axis in range(3)]
        started = perf_counter()
        record: dict[str, Any] = {
            "task_id": task.task_id,
            "family": task.family,
            "prompt": task.prompt,
            "ir": ir_path.relative_to(output_dir).as_posix(),
            "scad": scad_path.relative_to(output_dir).as_posix(),
            "stl": stl_path.relative_to(output_dir).as_posix(),
            "render": render_path.relative_to(output_dir).as_posix(),
        }
        reused = None
        if not config.force_recompile:
            reused = _reuse_kernel_artifacts(
                validation_path=validation_path,
                ir_path=ir_path,
                scad_path=scad_path,
                stl_path=stl_path,
                render_path=render_path,
                ir_text=ir_text,
                scad_text=scad_text,
                base_record=record,
                expected_extents=expected_extents,
            )
        if reused is not None:
            record = reused
            record["runtime_seconds"] = perf_counter() - started
            write_text_atomic(validation_path, _json(record))
            records.append(record)
            continue
        ir_path = write_text_atomic(ir_path, ir_text)
        scad_path = write_text_atomic(scad_path, scad_text)
        try:
            compile_scad(scad_path, stl_path, timeout=config.openscad_timeout_seconds)
            record["expected_extents_mm"] = expected_extents
            record["mesh"] = verify_stl(stl_path, expected_extents_mm=expected_extents)
            render_scad_png(scad_path, render_path, timeout=config.openscad_timeout_seconds)
            record["passed"] = True
            record["resumed_verified_artifact"] = False
            record["artifact_sha256"] = {
                "ir": _sha256_file(ir_path),
                "scad": _sha256_file(scad_path),
                "stl": _sha256_file(stl_path),
                "render": _sha256_file(render_path),
            }
        except RuntimeError as exc:
            record["passed"] = False
            record["error"] = str(exc)
        record["runtime_seconds"] = perf_counter() - started
        write_text_atomic(validation_path, _json(record))
        records.append(record)
    passed = sum(record["passed"] for record in records)
    return {
        "experiment_id": EXPERIMENT_IDS["kernel"],
        "status": "complete",
        "openscad": executable,
        "samples": len(records),
        "passed": passed,
        "force_recompile": config.force_recompile,
        "artifact_reuse_enabled": not config.force_recompile,
        "resumed_verified_samples": sum(bool(record.get("resumed_verified_artifact")) for record in records),
        "execution_validity": passed / len(records) if records else 0.0,
        "wilson_95": _wilson(passed, len(records)),
        "records": records,
    }


def _bar_chart(title: str, labels: list[str], values: list[float], *, percent: bool = True) -> str:
    width, height = 960, 520
    plot_left, plot_top, plot_width, plot_height = 210, 80, 680, 350
    rows: list[str] = []
    bar_height = min(48, plot_height / max(1, len(labels)) * 0.65)
    gap = plot_height / max(1, len(labels))
    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        y = plot_top + index * gap + (gap - bar_height) / 2
        bar_width = max(0, min(1, value)) * plot_width if percent else value * plot_width
        display = f"{value * 100:.1f}%" if percent else f"{value:.2f}"
        rows.append(f'<text x="{plot_left - 12}" y="{y + bar_height * 0.68:.1f}" text-anchor="end">{html.escape(label)}</text>')
        rows.append(f'<rect x="{plot_left}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" rx="6" />')
        rows.append(f'<text x="{plot_left + bar_width + 10:.1f}" y="{y + bar_height * 0.68:.1f}">{display}</text>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">'
        '<style>text{font-family:Inter,Arial,sans-serif;fill:#17202a;font-size:16px}rect{fill:#087e8b}.title{font-size:25px;font-weight:700}</style>'
        f'<rect width="{width}" height="{height}" fill="#fff"/><text class="title" x="40" y="42">{html.escape(title)}</text>'
        + "".join(rows)
        + '</svg>\n'
    )


def _complexity_chart(rows: list[dict[str, Any]]) -> str:
    valid_rows = [row for row in rows if row["valid"]]
    width, height = 960, 520
    left, top, plot_width, plot_height = 90, 70, 800, 370
    max_depth = max(row["depth"] for row in rows)
    max_latency = max(row["validate_export_ms"] for row in valid_rows) or 1
    points = " ".join(
        f'{left + row["depth"] / max_depth * plot_width:.1f},{top + plot_height - row["validate_export_ms"] / max_latency * plot_height:.1f}'
        for row in valid_rows
    )
    rejected = next(row for row in rows if not row["valid"])
    rejected_x = left + rejected["depth"] / max_depth * plot_width
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Hierarchy complexity versus latency">
<style>text{{font-family:Inter,Arial,sans-serif;fill:#17202a}}.title{{font-size:25px;font-weight:700}}.axis{{stroke:#17202a;stroke-width:2}}.curve{{fill:none;stroke:#087e8b;stroke-width:4}}.limit{{stroke:#d1495b;stroke-width:3;stroke-dasharray:8 8}}</style>
<rect width="{width}" height="{height}" fill="#fff"/><text class="title" x="40" y="40">Hierarchy complexity and enforced limit</text>
<line class="axis" x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}"/><line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}"/>
<polyline class="curve" points="{points}"/><line class="limit" x1="{rejected_x:.1f}" y1="{top}" x2="{rejected_x:.1f}" y2="{top + plot_height}"/>
<text x="{left + plot_width / 2}" y="485" text-anchor="middle">Hierarchy depth</text><text x="20" y="{top + plot_height / 2}" transform="rotate(-90 20 {top + plot_height / 2})" text-anchor="middle">validate + export latency (relative)</text>
<text x="{rejected_x - 8:.1f}" y="{top + 20}" text-anchor="end" fill="#d1495b">depth 129 rejected</text></svg>
"""


def run_research_suite(
    output_dir: Path,
    config: ResearchConfig | None = None,
    *,
    require_kernel: bool = False,
    run_id: str = RUN_ID,
) -> dict[str, Any]:
    config = config or ResearchConfig()
    config.validate()
    output_dir = output_dir.expanduser().resolve()
    project_root = _project_root()
    source_snapshot = _source_snapshot(project_root)
    provenance = _research_provenance(project_root, source_snapshot)
    if require_kernel:
        _require_archival_provenance(provenance)
    _prepare_fresh_output_dir(output_dir)
    write_text_atomic(output_dir / "config.json", _json(asdict(config)))

    tasks = generate_compiler_stress_tasks(config.compiler_tasks, config.seed)
    dataset_text = benchmark_jsonl(tasks)
    write_text_atomic(output_dir / "datasets" / "compiler_stress_v1.jsonl", dataset_text)
    compiler = run_benchmark(tasks, seed=config.seed)
    compiler["experiment_id"] = EXPERIMENT_IDS["compiler"]
    compiler["dataset_sha256"] = benchmark_hash(tasks)
    for system in compiler["systems"].values():
        correct = round(system["overall_semantic_exact_rate"] * len(tasks))
        system["semantic_exact_wilson_95"] = _wilson(correct, len(tasks))
    compiler["paired_tests_vs_neurocad"] = {
        name: _mcnemar_exact(compiler["systems"]["neurocad"]["records"], result["records"])
        for name, result in compiler["systems"].items()
        if name != "neurocad"
    }

    ir_stress, programs_jsonl, programs = _run_ir_stress(config)
    write_text_atomic(output_dir / "generated" / "ir_programs.jsonl", programs_jsonl)
    invalid, invalid_records = _run_invalid_taxonomy(config)
    write_text_atomic(output_dir / "analysis" / "invalid_cases.jsonl", invalid_records)
    constraint_ablation = _run_constraint_ablation(config)
    editability = _run_editability(config)
    complexity = _run_complexity()
    kernel = _run_kernel(config, tasks, output_dir)
    if require_kernel and kernel["status"] != "complete":
        raise RuntimeError("kernel execution was required but OpenSCAD was unavailable")
    if require_kernel and (kernel["execution_validity"] != 1.0 or kernel["samples"] != config.kernel_samples):
        raise RuntimeError("one or more required OpenSCAD kernel samples failed")

    systems = compiler["systems"]
    figure_dir = output_dir / "figures"
    ordered_systems = ["neurocad", "nearest_neighbor_retrieval", "raw_numbers_no_unit_normalization", "fixed_box"]
    write_text_atomic(
        figure_dir / "compiler_accuracy.svg",
        _bar_chart(
            "Controlled compiler semantic exactness",
            ordered_systems,
            [systems[name]["overall_semantic_exact_rate"] for name in ordered_systems],
        ),
    )
    categories = list(invalid["by_category"])
    write_text_atomic(
        figure_dir / "invalid_rejection.svg",
        _bar_chart(
            "Invalid-input rejection by predeclared category",
            categories,
            [invalid["by_category"][name]["rejected"] / invalid["by_category"][name]["cases"] for name in categories],
        ),
    )
    write_text_atomic(figure_dir / "complexity.svg", _complexity_chart(complexity["rows"]))

    selected_ids = [task.task_id for task in tasks[:8]]
    qualitative = {
        "selection_rule": "first eight task IDs before outcome inspection",
        "task_ids": selected_ids,
        "records": {
            name: [record for record in systems[name]["records"] if record["task_id"] in selected_ids]
            for name in ordered_systems
        },
    }
    write_text_atomic(output_dir / "analysis" / "qualitative_predeclared.json", _json(qualitative))

    results = {
        "suite_version": RESEARCH_SUITE_VERSION,
        "run_id": run_id,
        "claim_boundary": (
            "controlled deterministic compiler evidence only; no learned-model, open-world, human-usability, "
            "or historical typed-parser causal claim"
        ),
        "experiments": {
            EXPERIMENT_IDS["compiler"]: compiler,
            EXPERIMENT_IDS["ir_stress"]: ir_stress,
            EXPERIMENT_IDS["invalid_taxonomy"]: invalid,
            EXPERIMENT_IDS["constraint_ablation"]: constraint_ablation,
            EXPERIMENT_IDS["editability"]: editability,
            EXPERIMENT_IDS["kernel"]: kernel,
            EXPERIMENT_IDS["complexity"]: complexity,
        },
    }
    results_path = write_text_atomic(output_dir / "metrics" / "results.json", _json(results))
    deterministic_results = {
        "deterministic_results_version": DETERMINISTIC_RESULTS_VERSION,
        "timing_fields_excluded": True,
        "comparison_scope": (
            "Compare only runs with matching maintained-source, configuration, dependency-lock, Python, and OpenSCAD provenance."
        ),
        "results": _deterministic_copy(results),
    }
    deterministic_results_path = write_text_atomic(
        output_dir / "metrics" / "deterministic_results.json",
        _json(deterministic_results),
    )
    runtime_receipt = {
        "receipt_version": "neurocad-research-runtime-v1",
        "claim_boundary": (
            "Timing and environment observations are retained for diagnosis but are not deterministic scientific outcomes."
        ),
        "provenance": provenance,
        "timing_measurements": _timing_measurements(results),
    }
    runtime_receipt_path = write_text_atomic(
        output_dir / "metrics" / "runtime_receipt.json",
        _json(runtime_receipt),
    )
    write_text_atomic(
        output_dir / "logs" / "run.log",
        "\n".join(
            [
                f"run_id={run_id}",
                f"suite_version={RESEARCH_SUITE_VERSION}",
                f"compiler_tasks={config.compiler_tasks}",
                f"ir_programs={config.ir_programs}",
                f"invalid_cases={config.invalid_cases}",
                f"kernel_status={kernel['status']}",
                f"kernel_passed={kernel.get('passed', 0)}",
                "scientific_claim=controlled_compiler_only",
            ]
        )
        + "\n",
    )
    final_source_snapshot = _source_snapshot(project_root)
    if final_source_snapshot["sha256"] != source_snapshot["sha256"]:
        raise RuntimeError("maintained source changed while the research suite was running; no manifest was written")
    artifact_hashes = {
        path.relative_to(output_dir).as_posix(): _sha256_file(path)
        for path in sorted(output_dir.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "suite_version": RESEARCH_SUITE_VERSION,
        "run_id": run_id,
        "config_sha256": _sha256_text(_json(asdict(config))),
        "compiler_dataset_sha256": _sha256_text(dataset_text),
        "ir_programs_sha256": _sha256_text(programs_jsonl),
        "results": results_path.relative_to(output_dir).as_posix(),
        "deterministic_results": deterministic_results_path.relative_to(output_dir).as_posix(),
        "runtime_receipt": runtime_receipt_path.relative_to(output_dir).as_posix(),
        "scientific_sha256": {
            "config": _sha256_text(_json(asdict(config))),
            "compiler_dataset": _sha256_text(dataset_text),
            "ir_programs": _sha256_text(programs_jsonl),
            "deterministic_results": _sha256_file(deterministic_results_path),
            "maintained_source": source_snapshot["sha256"],
            "requirements_lock": provenance["requirements_lock"]["sha256"],
        },
        "scientific_hash_scope": (
            "The scientific_sha256 values exclude timing and host-load measurements and are comparable only after "
            "source, config, lock, Python, and OpenSCAD provenance match. artifact_sha256 values are snapshot-integrity "
            "hashes and may differ across machines."
        ),
        "provenance": provenance,
        "experiment_ids": EXPERIMENT_IDS,
        "model_checkpoint": None,
        "model_checkpoint_reason": "No learned model is implemented or claimed in the controlled compiler study.",
        "generated_program_count": len(programs),
        "kernel_required": require_kernel,
        "force_recompile": config.force_recompile,
        "artifact_reuse_allowed": not config.force_recompile,
        "artifact_sha256": artifact_hashes,
    }
    write_text_atomic(output_dir / "manifest.json", _json(manifest))
    return results
