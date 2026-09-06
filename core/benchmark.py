from __future__ import annotations

import hashlib
import json
import random
import re
import statistics
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from text_to_cad import TextToCAD

from .artifacts import write_text_atomic
from .ir import CADProgram
from .program_evaluation import evaluate_program

BENCHMARK_VERSION = "neurocad-benchmark-v1"
DEFAULT_SEED = 20260902


@dataclass(frozen=True)
class BenchmarkTask:
    task_id: str
    split: str
    family: str
    prompt: str
    expected: dict[str, Any]
    intervention_pair: str | None = None
    intervention_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def generate_benchmark(seed: int = DEFAULT_SEED) -> list[BenchmarkTask]:
    rng = random.Random(seed)  # Deterministic experiment seed, not a security value.  # nosec B311
    tasks: list[BenchmarkTask] = []

    def add(split: str, family: str, prompt: str, expected: dict[str, Any], pair: str | None = None, key: str | None = None) -> None:
        tasks.append(BenchmarkTask(f"NCB-{len(tasks) + 1:03d}", split, family, prompt, expected, pair, key))

    for _ in range(8):
        width, depth, thickness = rng.randrange(60, 181, 10), rng.randrange(40, 121, 10), rng.choice([2, 3, 4, 5])
        count, diameter = rng.choice([2, 4, 6]), rng.choice([3, 4, 5])
        add("train", "plate_holes", f"a {width} x {depth} x {thickness} mm plate with {count} {diameter} mm holes", {"kind": "box", "size": [width, depth, thickness], "hole_count": count, "hole_diameter": diameter})
    for _ in range(4):
        size = [rng.randrange(30, 101, 10), rng.randrange(20, 81, 10), rng.randrange(5, 41, 5)]
        add("train", "box", f"a {size[0]} x {size[1]} x {size[2]} mm box", {"kind": "box", "size": size, "hole_count": 0, "slot_count": 0})
    for _ in range(4):
        radius, height = rng.randrange(5, 31, 5), rng.randrange(20, 101, 10)
        add("train", "cylinder", f"a cylinder with radius {radius} mm and height {height} mm", {"kind": "cylinder", "radius": radius, "height": height})
    for _ in range(4):
        radius = rng.randrange(5, 31, 5)
        add("train", "sphere", f"a sphere with radius {radius} mm", {"kind": "sphere", "radius": radius})

    for _ in range(4):
        width, depth, thickness = rng.randrange(60, 181, 10), rng.randrange(40, 121, 10), rng.choice([2, 3, 4, 5])
        add("validation", "lexical_generalization", f"a plate {width} mm wide {depth} mm deep and {thickness} mm thick", {"kind": "box", "size": [width, depth, thickness], "hole_count": 0, "slot_count": 0})
    for _ in range(4):
        width, depth, thickness = rng.randrange(80, 161, 10), rng.randrange(50, 111, 10), rng.choice([3, 4, 5])
        count, slot_length, slot_width = rng.choice([1, 2, 3]), rng.choice([10, 12, 16]), rng.choice([3, 4, 5])
        add("validation", "composition", f"a {width} x {depth} x {thickness} mm plate with {count} {slot_length} x {slot_width} mm slots", {"kind": "box", "size": [width, depth, thickness], "slot_count": count, "slot_size": [slot_length, slot_width]})
    for _ in range(4):
        width_cm, depth_cm, thickness_cm = rng.choice([8, 10, 12]), rng.choice([5, 6, 7]), rng.choice([0.2, 0.3, 0.4])
        add("validation", "unit_perturbation", f"a {width_cm} x {depth_cm} x {thickness_cm} cm plate", {"kind": "box", "size": [width_cm * 10, depth_cm * 10, thickness_cm * 10], "hole_count": 0, "slot_count": 0})

    for _ in range(4):
        width, depth, height = rng.randrange(70, 141, 10), rng.randrange(50, 101, 10), rng.randrange(20, 61, 10)
        wall = rng.choice([1.5, 2.0, 2.5, 3.0])
        add("test", "enclosure", f"a {width} x {depth} x {height} mm enclosure with {wall} mm wall thickness", {"kind": "box", "size": [width, depth, height], "wall_thickness": wall, "open_top": True})
    for _ in range(4):
        width_in, depth_in, thickness_in = rng.choice([2, 3, 4]), rng.choice([1, 2]), rng.choice([0.1, 0.125, 0.2])
        add("test", "held_out_units", f"a {width_in} by {depth_in} by {thickness_in} inch plate", {"kind": "box", "size": [width_in * 25.4, depth_in * 25.4, thickness_in * 25.4], "hole_count": 0, "slot_count": 0})

    interventions = [
        ("holes-count", "hole_count", "a 100 x 60 x 4 mm plate with {value} 4 mm holes", 2, 4),
        ("holes-diameter", "hole_diameter", "a 100 x 60 x 4 mm plate with four {value} mm holes", 3, 5),
        ("plate-width", "size", "a {value} x 60 x 4 mm plate", 80, 120),
        ("slot-count", "slot_count", "a 100 x 60 x 4 mm plate with {value} 12 x 4 mm slots", 1, 2),
    ]
    for pair, key, template, left, right in interventions:
        for value in (left, right):
            expected: dict[str, Any] = {"kind": "box", "size": [100, 60, 4], "hole_count": 0, "slot_count": 0}
            if pair == "holes-count":
                expected.update({"hole_count": value, "hole_diameter": 4})
            elif pair == "holes-diameter":
                expected.update({"hole_count": 4, "hole_diameter": value})
            elif pair == "plate-width":
                expected["size"] = [value, 60, 4]
            else:
                expected.update({"slot_count": value, "slot_size": [12, 4]})
            word_value = {1: "one", 2: "two", 4: "four"}.get(value, value)
            add("test", "counterfactual_intervention", template.format(value=word_value), expected, pair, key)
    return tasks


def benchmark_jsonl(tasks: list[BenchmarkTask]) -> str:
    return "".join(json.dumps(task.to_dict(), sort_keys=True, separators=(",", ":")) + "\n" for task in tasks)


def benchmark_hash(tasks: list[BenchmarkTask]) -> str:
    return hashlib.sha256(benchmark_jsonl(tasks).encode("utf-8")).hexdigest()


def write_benchmark(path: Path, tasks: list[BenchmarkTask]) -> Path:
    return write_text_atomic(path, benchmark_jsonl(tasks))


def program_signature(program: CADProgram) -> dict[str, Any]:
    leaves = [node for node in program.nodes if node.primitive is not None]
    if not leaves:
        raise ValueError("program has no primitive nodes")
    body = next((node for node in leaves if node.id == "body"), leaves[0])
    if body.primitive is None:
        raise ValueError("selected body is not a primitive")
    signature: dict[str, Any] = {"kind": body.primitive.kind}
    signature.update(body.primitive.parameters)
    holes = [node for node in leaves if node.id.startswith("hole_")]
    slots = [node for node in leaves if node.id.startswith("slot_")]
    signature["hole_count"] = len(holes)
    signature["slot_count"] = len(slots)
    if holes:
        hole_primitive = holes[0].primitive
        if hole_primitive is None:
            raise ValueError("hole node is not a primitive")
        signature["hole_diameter"] = 2 * float(hole_primitive.parameters["radius"])
    if slots:
        slot_primitive = slots[0].primitive
        if slot_primitive is None:
            raise ValueError("slot node is not a primitive")
        signature["slot_size"] = list(slot_primitive.parameters["size"][:2])
    cavity = next((node for node in leaves if node.id == "cavity"), None)
    if cavity is not None and body.primitive.kind in {"box", "rounded_box"}:
        if cavity.primitive is None:
            raise ValueError("cavity node is not a primitive")
        outer = body.primitive.parameters["size"]
        inner = cavity.primitive.parameters["size"]
        signature["wall_thickness"] = (float(outer[0]) - float(inner[0])) / 2
        signature["open_top"] = True
    return signature


def _equal(expected: Any, actual: Any, tolerance: float = 1e-6) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(key in actual and _equal(value, actual[key], tolerance) for key, value in expected.items())
    if isinstance(expected, (list, tuple)):
        return isinstance(actual, (list, tuple)) and len(expected) == len(actual) and all(_equal(left, right, tolerance) for left, right in zip(expected, actual, strict=True))
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return isinstance(actual, (int, float)) and not isinstance(actual, bool) and abs(float(expected) - float(actual)) <= tolerance
    return expected == actual


def _neurocad_predict(task: BenchmarkTask) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    started = perf_counter()
    try:
        document = TextToCAD().build(task.prompt)
        if not document.validation.valid:
            return None, {"valid": False, "errors": list(document.validation.errors), "latency_ms": (perf_counter() - started) * 1000}
        program = document.require_program()
        evaluation = evaluate_program(program)
        signature = program_signature(program)
        return signature, {"valid": True, "evaluation": evaluation.to_dict(), "latency_ms": (perf_counter() - started) * 1000}
    except (ValueError, KeyError, TypeError) as exc:
        return None, {"valid": False, "errors": [str(exc)], "latency_ms": (perf_counter() - started) * 1000}


def _fixed_box_predict(task: BenchmarkTask) -> tuple[dict[str, Any], dict[str, Any]]:
    return {"kind": "box", "size": [80, 80, 80], "hole_count": 0, "slot_count": 0}, {"valid": True, "latency_ms": 0.0}


def _raw_number_predict(task: BenchmarkTask) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    started = perf_counter()
    numbers = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", task.prompt)]
    if "cylinder" in task.prompt and len(numbers) >= 2:
        signature = {"kind": "cylinder", "radius": numbers[0], "height": numbers[1], "hole_count": 0, "slot_count": 0}
    elif "sphere" in task.prompt and numbers:
        signature = {"kind": "sphere", "radius": numbers[0], "hole_count": 0, "slot_count": 0}
    elif len(numbers) >= 3:
        signature = {"kind": "box", "size": numbers[:3], "hole_count": 0, "slot_count": 0}
    else:
        return None, {"valid": False, "latency_ms": (perf_counter() - started) * 1000}
    return signature, {"valid": True, "latency_ms": (perf_counter() - started) * 1000}


PREDICTORS: dict[str, Callable[[BenchmarkTask], tuple[dict[str, Any] | None, dict[str, Any]]]] = {
    "neurocad": _neurocad_predict,
    "fixed_box": _fixed_box_predict,
    "raw_numbers_no_unit_normalization": _raw_number_predict,
}


def _nearest_neighbor_predictor(tasks: list[BenchmarkTask]) -> Callable[[BenchmarkTask], tuple[dict[str, Any], dict[str, Any]]]:
    train = [task for task in tasks if task.split == "train"]
    if not train:
        raise ValueError("nearest-neighbor baseline requires train-labelled tasks")

    def tokens(prompt: str) -> set[str]:
        return set(re.findall(r"[a-z]+|\d+(?:\.\d+)?", prompt.lower()))

    indexed = [(task, tokens(task.prompt)) for task in train]

    def predict(task: BenchmarkTask) -> tuple[dict[str, Any], dict[str, Any]]:
        started = perf_counter()
        query = tokens(task.prompt)

        def score(candidate: tuple[BenchmarkTask, set[str]]) -> tuple[float, str]:
            train_task, train_tokens = candidate
            union = query | train_tokens
            similarity = len(query & train_tokens) / len(union) if union else 1.0
            return similarity, train_task.task_id

        neighbor, _ = max(indexed, key=score)
        return deepcopy(neighbor.expected), {
            "valid": True,
            "neighbor_task_id": neighbor.task_id,
            "latency_ms": (perf_counter() - started) * 1000,
        }

    return predict


def _intervention_score(tasks: list[BenchmarkTask], records: list[dict[str, Any]]) -> float | None:
    by_id = {record["task_id"]: record for record in records}
    pairs: dict[str, list[BenchmarkTask]] = {}
    for task in tasks:
        if task.intervention_pair:
            pairs.setdefault(task.intervention_pair, []).append(task)
    scores: list[bool] = []
    for members in pairs.values():
        if len(members) != 2:
            continue
        left, right = members
        left_actual, right_actual = by_id[left.task_id].get("actual"), by_id[right.task_id].get("actual")
        if left_actual is None or right_actual is None:
            scores.append(False)
            continue
        expected_changed = {key for key in set(left.expected) | set(right.expected) if not _equal(left.expected.get(key), right.expected.get(key))}
        actual_changed = {key for key in set(left_actual) | set(right_actual) if not _equal(left_actual.get(key), right_actual.get(key))}
        scores.append(actual_changed == expected_changed and left.intervention_key in actual_changed)
    return sum(scores) / len(scores) if scores else None


def _validate_task_set(tasks: list[BenchmarkTask]) -> None:
    if not tasks:
        raise ValueError("benchmark requires at least one task")
    if any(not isinstance(task, BenchmarkTask) for task in tasks):
        raise TypeError("every benchmark entry must be a BenchmarkTask")
    ids = [task.task_id for task in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("benchmark task IDs must be unique")
    splits = {task.split for task in tasks}
    if splits != {"train", "validation", "test"}:
        raise ValueError("benchmark must contain non-empty train, validation, and test splits")
    for task in tasks:
        if not task.task_id.strip() or not task.family.strip() or not task.prompt.strip():
            raise ValueError("benchmark task IDs, families, and prompts must be non-empty")
        if not isinstance(task.expected, dict) or not task.expected:
            raise ValueError(f"benchmark task {task.task_id} requires a non-empty expected signature")
    intervention_pairs: dict[str, list[BenchmarkTask]] = {}
    for task in tasks:
        if task.intervention_pair:
            intervention_pairs.setdefault(task.intervention_pair, []).append(task)
    for pair, members in intervention_pairs.items():
        if len(members) != 2 or any(not member.intervention_key for member in members):
            raise ValueError(f"intervention pair {pair!r} must contain exactly two tasks with an intervention key")


def run_benchmark(tasks: list[BenchmarkTask] | None = None, *, seed: int = DEFAULT_SEED) -> dict[str, Any]:
    tasks = generate_benchmark(seed) if tasks is None else tasks
    _validate_task_set(tasks)
    systems: dict[str, Any] = {}
    predictors = {**PREDICTORS, "nearest_neighbor_retrieval": _nearest_neighbor_predictor(tasks)}
    for name, predictor in predictors.items():
        records: list[dict[str, Any]] = []
        for task in tasks:
            actual, details = predictor(task)
            records.append(
                {
                    "task_id": task.task_id,
                    "split": task.split,
                    "family": task.family,
                    "passed": actual is not None and _equal(task.expected, actual),
                    "expected": task.expected,
                    "actual": actual,
                    "details": details,
                }
            )
        splits: dict[str, Any] = {}
        for split in ("train", "validation", "test"):
            subset = [record for record in records if record["split"] == split]
            splits[split] = {
                "tasks": len(subset),
                "semantic_exact_rate": sum(record["passed"] for record in subset) / len(subset),
                "valid_output_rate": sum(record["actual"] is not None for record in subset) / len(subset),
                "mean_latency_ms": statistics.fmean(record["details"]["latency_ms"] for record in subset),
            }
        systems[name] = {
            "overall_semantic_exact_rate": sum(record["passed"] for record in records) / len(records),
            "intervention_consistency_rate": _intervention_score(tasks, records),
            "splits": splits,
            "records": records,
            "failures": [record for record in records if not record["passed"]],
        }
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "seed": seed,
        "task_count": len(tasks),
        "benchmark_sha256": benchmark_hash(tasks),
        "scientific_claim_status": "engineering baseline only; historical typed-parser causal claim remains falsified",
        "systems": systems,
    }


def save_benchmark_results(path: Path, results: dict[str, Any]) -> Path:
    return write_text_atomic(path, json.dumps(results, indent=2, sort_keys=True) + "\n")
