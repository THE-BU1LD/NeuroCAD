"""Deterministic authoring, leakage checks, freezing, and pilot selection for VeriCodeGen.

This module is intentionally provider-free. It never calls a model or external API.
Its job is to make a future benchmark auditable before any outcome is observed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from core.json_io import strict_json_loads

PROMPT_ID_RE = re.compile(r"^VCG-[0-9]{3}$")
TOKEN_RE = re.compile(r"[a-z0-9]+")
FAMILIES = ("in_distribution", "compositional", "ood_constraint_stress")
ALLOWED_TASK_KEYS = {
    "prompt_id",
    "prompt_text",
    "task_family",
    "required_relations",
    "hard_constraints",
    "semantic_rubric",
    "notes",
}
ALLOWED_CONSTRAINTS = {"watertight", "max_components", "volume", "extents", "bounds"}
AXES = ("x", "y", "z")


class BenchmarkError(ValueError):
    """Raised when benchmark authoring/freeze invariants are violated."""


def canonical_json(value: Any) -> str:
    """Return stable UTF-8 JSON text suitable for hashing and manifests."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_prompt(text: str) -> str:
    """Normalize superficial punctuation/spacing for duplicate checks."""

    return " ".join(TOKEN_RE.findall(text.lower()))


def _token_set(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


def jaccard_similarity(left: str, right: str) -> float:
    a = _token_set(left)
    b = _token_set(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            payload = strict_json_loads(raw)
        except json.JSONDecodeError as exc:
            raise BenchmarkError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise BenchmarkError(f"line {line_number}: task must be a JSON object")
        rows.append(payload)
    if not rows:
        raise BenchmarkError("benchmark file contains no tasks")
    return rows


def _validate_range(name: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, Mapping) or not value:
        errors.append(f"{name} must be a non-empty object")
        return
    unknown = sorted(set(value) - {"min", "max"})
    if unknown:
        errors.append(f"{name} has unsupported keys: {', '.join(unknown)}")
    for key in ("min", "max"):
        if key in value and (not isinstance(value[key], (int, float)) or isinstance(value[key], bool)):
            errors.append(f"{name}.{key} must be numeric")
    if (
        isinstance(value.get("min"), (int, float))
        and not isinstance(value.get("min"), bool)
        and isinstance(value.get("max"), (int, float))
        and not isinstance(value.get("max"), bool)
        and float(value["min"]) > float(value["max"])
    ):
        errors.append(f"{name}.min must be <= {name}.max")


def validate_task(task: Mapping[str, Any]) -> list[str]:
    """Validate one benchmark task without adding a runtime JSON-schema dependency."""

    errors: list[str] = []
    missing = sorted(
        {"prompt_id", "prompt_text", "task_family", "required_relations", "hard_constraints", "semantic_rubric"}
        - set(task)
    )
    if missing:
        errors.append(f"missing required keys: {', '.join(missing)}")
    unknown = sorted(set(task) - ALLOWED_TASK_KEYS)
    if unknown:
        errors.append(f"unsupported task keys: {', '.join(unknown)}")

    prompt_id = task.get("prompt_id")
    if not isinstance(prompt_id, str) or not PROMPT_ID_RE.fullmatch(prompt_id):
        errors.append("prompt_id must match VCG-000")

    prompt_text = task.get("prompt_text")
    if not isinstance(prompt_text, str) or not prompt_text.strip():
        errors.append("prompt_text must be non-empty")
    elif len(normalize_prompt(prompt_text).split()) < 5:
        errors.append("prompt_text must contain at least five normalized tokens")

    family = task.get("task_family")
    if family not in FAMILIES:
        errors.append(f"task_family must be one of {', '.join(FAMILIES)}")

    relations = task.get("required_relations")
    if not isinstance(relations, list):
        errors.append("required_relations must be a list")
    else:
        if any(not isinstance(item, str) or not item.strip() for item in relations):
            errors.append("required_relations entries must be non-empty strings")
        if len(set(relations)) != len(relations):
            errors.append("required_relations must not contain duplicates")

    constraints = task.get("hard_constraints")
    if not isinstance(constraints, Mapping) or not constraints:
        errors.append("hard_constraints must contain at least one machine-checkable constraint")
    else:
        unknown_constraints = sorted(set(constraints) - ALLOWED_CONSTRAINTS)
        if unknown_constraints:
            errors.append(f"unsupported hard constraints: {', '.join(unknown_constraints)}")

        if "watertight" in constraints and not isinstance(constraints["watertight"], bool):
            errors.append("hard_constraints.watertight must be boolean")

        if "max_components" in constraints:
            value = constraints["max_components"]
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                errors.append("hard_constraints.max_components must be an integer >= 1")

        if "volume" in constraints:
            _validate_range("hard_constraints.volume", constraints["volume"], errors)

        if "extents" in constraints:
            extents = constraints["extents"]
            if not isinstance(extents, Mapping) or not extents:
                errors.append("hard_constraints.extents must be a non-empty object")
            else:
                unknown_axes = sorted(set(extents) - set(AXES))
                if unknown_axes:
                    errors.append(f"hard_constraints.extents has unsupported axes: {', '.join(unknown_axes)}")
                for axis, rule in extents.items():
                    if axis in AXES:
                        _validate_range(f"hard_constraints.extents.{axis}", rule, errors)

        if "bounds" in constraints:
            bounds = constraints["bounds"]
            if not isinstance(bounds, Mapping) or not bounds:
                errors.append("hard_constraints.bounds must be a non-empty object")
            else:
                unknown_bounds = sorted(set(bounds) - {"min", "max"})
                if unknown_bounds:
                    errors.append(f"hard_constraints.bounds has unsupported keys: {', '.join(unknown_bounds)}")
                parsed: dict[str, Sequence[float]] = {}
                for side in ("min", "max"):
                    if side not in bounds:
                        continue
                    vector = bounds[side]
                    if (
                        not isinstance(vector, list)
                        or len(vector) != 3
                        or any(not isinstance(item, (int, float)) or isinstance(item, bool) for item in vector)
                    ):
                        errors.append(f"hard_constraints.bounds.{side} must be a numeric 3-vector")
                    else:
                        parsed[side] = vector
                if "min" in parsed and "max" in parsed:
                    for index, axis in enumerate(AXES):
                        if float(parsed["min"][index]) > float(parsed["max"][index]):
                            errors.append(f"hard_constraints.bounds min.{axis} must be <= max.{axis}")

    rubric = task.get("semantic_rubric")
    if not isinstance(rubric, list) or not rubric:
        errors.append("semantic_rubric must be a non-empty list")
    else:
        criteria: list[str] = []
        for index, entry in enumerate(rubric):
            if not isinstance(entry, Mapping):
                errors.append(f"semantic_rubric[{index}] must be an object")
                continue
            if set(entry) != {"criterion", "description"}:
                errors.append(f"semantic_rubric[{index}] must contain only criterion and description")
            criterion = entry.get("criterion")
            description = entry.get("description")
            if not isinstance(criterion, str) or not criterion.strip():
                errors.append(f"semantic_rubric[{index}].criterion must be non-empty")
            else:
                criteria.append(criterion.strip().lower())
            if not isinstance(description, str) or not description.strip():
                errors.append(f"semantic_rubric[{index}].description must be non-empty")
        if len(criteria) != len(set(criteria)):
            errors.append("semantic_rubric criteria must be unique within a task")

    notes = task.get("notes")
    if notes is not None and not isinstance(notes, str):
        errors.append("notes must be a string when present")

    return errors


def near_duplicate_pairs(
    tasks: Sequence[Mapping[str, Any]], *, threshold: float = 0.88
) -> list[tuple[str, str, float]]:
    """Return prompt pairs at or above a conservative token-Jaccard threshold."""

    if not 0 < threshold <= 1:
        raise BenchmarkError("near-duplicate threshold must be in (0, 1]")
    pairs: list[tuple[str, str, float]] = []
    for left_index, left in enumerate(tasks):
        left_text = str(left.get("prompt_text", ""))
        for right in tasks[left_index + 1 :]:
            score = jaccard_similarity(left_text, str(right.get("prompt_text", "")))
            if score >= threshold:
                pairs.append((str(left.get("prompt_id")), str(right.get("prompt_id")), score))
    return pairs


def validate_benchmark(
    tasks: Sequence[Mapping[str, Any]],
    *,
    expected_total: int | None = None,
    expected_per_family: int | None = None,
    near_duplicate_threshold: float = 0.88,
) -> list[str]:
    errors: list[str] = []
    ids: list[str] = []
    normalized_prompts: list[str] = []

    for index, task in enumerate(tasks):
        task_errors = validate_task(task)
        label = task.get("prompt_id", f"index-{index}")
        errors.extend(f"{label}: {error}" for error in task_errors)
        if isinstance(task.get("prompt_id"), str):
            ids.append(task["prompt_id"])
        if isinstance(task.get("prompt_text"), str):
            normalized_prompts.append(normalize_prompt(task["prompt_text"]))

    duplicate_ids = sorted(key for key, count in Counter(ids).items() if count > 1)
    if duplicate_ids:
        errors.append(f"duplicate prompt ids: {', '.join(duplicate_ids)}")

    duplicate_prompts = sorted(key for key, count in Counter(normalized_prompts).items() if count > 1)
    if duplicate_prompts:
        errors.append(f"exact normalized prompt duplicates found: {len(duplicate_prompts)}")

    if expected_total is not None:
        if len(tasks) != expected_total:
            errors.append(f"benchmark must contain exactly {expected_total} tasks; found {len(tasks)}")
        expected_ids = [f"VCG-{number:03d}" for number in range(1, expected_total + 1)]
        if sorted(ids) != expected_ids:
            errors.append("prompt ids must form the complete contiguous frozen sequence")

    family_counts = Counter(task.get("task_family") for task in tasks)
    if expected_per_family is not None:
        for family in FAMILIES:
            if family_counts[family] != expected_per_family:
                errors.append(
                    f"family {family} must contain exactly {expected_per_family} tasks; "
                    f"found {family_counts[family]}"
                )

    for left, right, score in near_duplicate_pairs(tasks, threshold=near_duplicate_threshold):
        errors.append(f"near-duplicate prompts: {left} vs {right} (token Jaccard={score:.3f})")

    return errors


def canonicalize_tasks(tasks: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return tasks sorted by prompt id with JSON-compatible copies."""

    copied = [json.loads(canonical_json(task)) for task in tasks]
    return sorted(copied, key=lambda task: task["prompt_id"])


def benchmark_jsonl(tasks: Iterable[Mapping[str, Any]]) -> str:
    return "".join(canonical_json(task) + "\n" for task in canonicalize_tasks(tasks))


def build_manifest(
    tasks: Sequence[Mapping[str, Any]],
    *,
    schema_sha256: str,
    benchmark_filename: str,
) -> dict[str, Any]:
    canonical = canonicalize_tasks(tasks)
    jsonl = benchmark_jsonl(canonical)
    task_hashes = {
        task["prompt_id"]: sha256_text(canonical_json(task))
        for task in canonical
    }
    return {
        "manifest_version": "vericodegen-benchmark-v1",
        "benchmark_file": benchmark_filename,
        "benchmark_sha256": sha256_text(jsonl),
        "schema_sha256": schema_sha256,
        "task_count": len(canonical),
        "family_counts": dict(sorted(Counter(task["task_family"] for task in canonical).items())),
        "task_sha256": task_hashes,
        "frozen": True,
        "outcomes_observed": False,
    }


def freeze_benchmark(
    source: str | Path,
    *,
    schema: str | Path,
    output_jsonl: str | Path,
    output_manifest: str | Path,
    expected_total: int = 120,
    expected_per_family: int = 40,
    near_duplicate_threshold: float = 0.88,
) -> dict[str, Any]:
    tasks = load_jsonl(source)
    errors = validate_benchmark(
        tasks,
        expected_total=expected_total,
        expected_per_family=expected_per_family,
        near_duplicate_threshold=near_duplicate_threshold,
    )
    if errors:
        raise BenchmarkError("benchmark freeze blocked:\n- " + "\n- ".join(errors))

    canonical_text = benchmark_jsonl(tasks)
    output_path = Path(output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_text.encode("utf-8"))

    manifest = build_manifest(
        canonicalize_tasks(tasks),
        schema_sha256=sha256_file(schema),
        benchmark_filename=output_path.name,
    )
    manifest_path = Path(output_manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def select_stratified_pilot(
    tasks: Sequence[Mapping[str, Any]],
    *,
    per_family: int,
    selection_salt: str,
) -> list[str]:
    """Select a stable, auditable pilot subset without Python RNG/version dependence."""

    if per_family < 1:
        raise BenchmarkError("per_family must be >= 1")
    if not selection_salt.strip():
        raise BenchmarkError("selection_salt must be non-empty")

    chosen: list[str] = []
    for family in FAMILIES:
        candidates = [task for task in tasks if task.get("task_family") == family]
        if len(candidates) < per_family:
            raise BenchmarkError(
                f"family {family} has {len(candidates)} tasks but pilot needs {per_family}"
            )
        ranked = sorted(
            candidates,
            key=lambda task: hashlib.sha256(
                f"{selection_salt}\0{family}\0{task['prompt_id']}".encode()
            ).hexdigest(),
        )
        chosen.extend(task["prompt_id"] for task in ranked[:per_family])
    return sorted(chosen)


def _cmd_validate(args: argparse.Namespace) -> int:
    tasks = load_jsonl(args.benchmark)
    errors = validate_benchmark(
        tasks,
        expected_total=args.expected_total,
        expected_per_family=args.expected_per_family,
        near_duplicate_threshold=args.near_duplicate_threshold,
    )
    if errors:
        raise BenchmarkError("benchmark validation failed:\n- " + "\n- ".join(errors))
    print(f"benchmark valid: {len(tasks)} tasks")
    return 0


def _cmd_freeze(args: argparse.Namespace) -> int:
    manifest = freeze_benchmark(
        args.source,
        schema=args.schema,
        output_jsonl=args.output_jsonl,
        output_manifest=args.output_manifest,
        expected_total=args.expected_total,
        expected_per_family=args.expected_per_family,
        near_duplicate_threshold=args.near_duplicate_threshold,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def _cmd_select(args: argparse.Namespace) -> int:
    tasks = load_jsonl(args.benchmark)
    selected = select_stratified_pilot(
        tasks,
        per_family=args.per_family,
        selection_salt=args.selection_salt,
    )
    payload = {
        "selection_version": "vericodegen-pilot-selection-v1",
        "selection_salt": args.selection_salt,
        "per_family": args.per_family,
        "pilot_task_ids": selected,
        "benchmark_sha256": sha256_text(benchmark_jsonl(tasks)),
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate an authored JSONL benchmark")
    validate.add_argument("benchmark", type=Path)
    validate.add_argument("--expected-total", type=int, default=None)
    validate.add_argument("--expected-per-family", type=int, default=None)
    validate.add_argument("--near-duplicate-threshold", type=float, default=0.88)
    validate.set_defaults(func=_cmd_validate)

    freeze = subparsers.add_parser("freeze", help="canonicalize and hash a final benchmark")
    freeze.add_argument("source", type=Path)
    freeze.add_argument("--schema", type=Path, required=True)
    freeze.add_argument("--output-jsonl", type=Path, required=True)
    freeze.add_argument("--output-manifest", type=Path, required=True)
    freeze.add_argument("--expected-total", type=int, default=120)
    freeze.add_argument("--expected-per-family", type=int, default=40)
    freeze.add_argument("--near-duplicate-threshold", type=float, default=0.88)
    freeze.set_defaults(func=_cmd_freeze)

    select = subparsers.add_parser("select-pilot", help="deterministically select a stratified pilot")
    select.add_argument("benchmark", type=Path)
    select.add_argument("--per-family", type=int, default=4)
    select.add_argument("--selection-salt", required=True)
    select.add_argument("--output", type=Path)
    select.set_defaults(func=_cmd_select)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
