"""Predeclared paired analysis for the VeriCodeGen successor study.

The implementation is provider-independent and consumes retained final trial rows.
It does not generate, repair, or select outcomes. The primary unit is prompt × seed,
with one direct and one structured observation per unit.
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from core.json_io import strict_json_loads

ARMS = ("direct", "structured")
FAMILIES = ("in_distribution", "compositional", "ood_constraint_stress")
FAILURE_MODES = {
    "syntax_compile_failure",
    "unsupported_operation",
    "missing_required_object",
    "wrong_dimension_unit",
    "spatial_relation_violation",
    "forbidden_connectivity_or_intersection",
    "semantic_misinterpretation",
    "verifier_ambiguity_error",
    "timeout_retry_exhaustion",
    "missing_final_artifact",
}
REQUIRED_FIELDS = {
    "prompt_id",
    "seed",
    "arm",
    "task_family",
    "hvr",
    "compile_success",
    "hard_constraints_passed",
    "retry_count",
    "generated_tokens",
    "wall_clock_seconds",
    "estimated_cost_usd",
    "failure_modes",
}


class AnalysisError(ValueError):
    """Raised when retained outcomes cannot support the frozen paired analysis."""


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = strict_json_loads(raw)
        except json.JSONDecodeError as exc:
            raise AnalysisError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise AnalysisError(f"line {line_number}: outcome row must be an object")
        rows.append(value)
    return rows


def _finite_nonnegative(name: str, value: Any, errors: list[str]) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        errors.append(f"{name} must be a finite number >= 0")


def validate_row(row: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(row))
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")

    prompt_id = row.get("prompt_id")
    if not isinstance(prompt_id, str) or not prompt_id.startswith("VCG-"):
        errors.append("prompt_id must be a VeriCodeGen id")
    seed = row.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        errors.append("seed must be an integer")
    if row.get("arm") not in ARMS:
        errors.append("arm must be direct or structured")
    if row.get("task_family") not in FAMILIES:
        errors.append("task_family is invalid")

    for field in ("hvr", "compile_success", "hard_constraints_passed"):
        if not isinstance(row.get(field), bool):
            errors.append(f"{field} must be boolean")

    retry_count = row.get("retry_count")
    if not isinstance(retry_count, int) or isinstance(retry_count, bool) or retry_count < 0:
        errors.append("retry_count must be an integer >= 0")
    generated_tokens = row.get("generated_tokens")
    if not isinstance(generated_tokens, int) or isinstance(generated_tokens, bool) or generated_tokens < 0:
        errors.append("generated_tokens must be an integer >= 0")
    _finite_nonnegative("wall_clock_seconds", row.get("wall_clock_seconds"), errors)
    _finite_nonnegative("estimated_cost_usd", row.get("estimated_cost_usd"), errors)

    modes = row.get("failure_modes")
    if not isinstance(modes, list):
        errors.append("failure_modes must be a list")
    else:
        unknown = sorted(set(modes) - FAILURE_MODES)
        if unknown:
            errors.append(f"unsupported failure_modes: {', '.join(unknown)}")
        if len(modes) != len(set(modes)):
            errors.append("failure_modes must not contain duplicates")

    if row.get("hvr") is True and (
        row.get("compile_success") is not True or row.get("hard_constraints_passed") is not True
    ):
        errors.append("hvr=true requires compile_success=true and hard_constraints_passed=true")

    return errors


def validate_paired_rows(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    grouped: dict[tuple[Any, Any], list[Mapping[str, Any]]] = defaultdict(list)
    for index, row in enumerate(rows):
        row_errors = validate_row(row)
        label = f"row[{index}]"
        errors.extend(f"{label}: {error}" for error in row_errors)
        grouped[(row.get("prompt_id"), row.get("seed"))].append(row)

    if not rows:
        errors.append("analysis requires at least one paired unit")

    for unit, unit_rows in grouped.items():
        arms = [str(row.get("arm")) for row in unit_rows]
        if sorted(arms) != ["direct", "structured"]:
            errors.append(f"paired unit {unit} must contain exactly one direct and one structured row")
        families = {row.get("task_family") for row in unit_rows}
        if len(families) != 1:
            errors.append(f"paired unit {unit} has inconsistent task_family labels")

    return errors


def pair_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Mapping[str, Any]]]:
    errors = validate_paired_rows(rows)
    if errors:
        raise AnalysisError("paired analysis blocked:\n- " + "\n- ".join(errors))
    grouped: dict[tuple[str, int], dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[(row["prompt_id"], row["seed"])][row["arm"]] = row
    return [grouped[key] for key in sorted(grouped)]


def exact_mcnemar_pvalue(structured_only: int, direct_only: int) -> float:
    """Two-sided exact McNemar/binomial p-value over discordant pairs."""

    if structured_only < 0 or direct_only < 0:
        raise AnalysisError("discordant counts must be non-negative")
    n = structured_only + direct_only
    if n == 0:
        return 1.0
    tail = min(structured_only, direct_only)
    probability = sum(math.comb(n, k) for k in range(tail + 1)) / (2**n)
    return min(1.0, 2.0 * probability)


def _percentile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise AnalysisError("cannot take percentile of empty values")
    if not 0 <= probability <= 1:
        raise AnalysisError("percentile probability must be in [0, 1]")
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


def paired_bootstrap_difference_ci(
    differences: Sequence[int],
    *,
    confidence: float = 0.95,
    replicates: int = 10000,
    seed: int = 20260831,
) -> tuple[float, float]:
    """Percentile CI over paired {-1,0,+1} HVR differences."""

    if not differences:
        raise AnalysisError("bootstrap requires at least one paired difference")
    if any(value not in (-1, 0, 1) for value in differences):
        raise AnalysisError("paired HVR differences must be -1, 0, or 1")
    if not 0 < confidence < 1:
        raise AnalysisError("confidence must be in (0, 1)")
    if replicates < 100:
        raise AnalysisError("bootstrap replicates must be >= 100")

    rng = random.Random(seed)  # Deterministic statistical resampling, not security.  # nosec B311
    n = len(differences)
    estimates: list[float] = []
    for _ in range(replicates):
        total = 0
        for _index in range(n):
            total += differences[rng.randrange(n)]
        estimates.append(total / n)
    alpha = 1.0 - confidence
    return (
        _percentile(estimates, alpha / 2),
        _percentile(estimates, 1 - alpha / 2),
    )


def _mean(values: Iterable[float]) -> float:
    materialized = list(values)
    return sum(materialized) / len(materialized) if materialized else 0.0


def _arm_summary(rows: Sequence[Mapping[str, Any]], arm: str) -> dict[str, Any]:
    arm_rows = [row for row in rows if row["arm"] == arm]
    return {
        "n": len(arm_rows),
        "hvr": _mean(float(row["hvr"]) for row in arm_rows),
        "compile_success_rate": _mean(float(row["compile_success"]) for row in arm_rows),
        "hard_constraint_satisfaction_rate": _mean(
            float(row["hard_constraints_passed"]) for row in arm_rows
        ),
        "mean_retry_count": _mean(float(row["retry_count"]) for row in arm_rows),
        "mean_generated_tokens": _mean(float(row["generated_tokens"]) for row in arm_rows),
        "mean_wall_clock_seconds": _mean(float(row["wall_clock_seconds"]) for row in arm_rows),
        "mean_estimated_cost_usd": _mean(float(row["estimated_cost_usd"]) for row in arm_rows),
        "failure_modes": dict(
            sorted(Counter(mode for row in arm_rows for mode in row["failure_modes"]).items())
        ),
    }


def analyze_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    confidence: float = 0.95,
    bootstrap_replicates: int = 10000,
    bootstrap_seed: int = 20260831,
) -> dict[str, Any]:
    pairs = pair_rows(rows)
    differences: list[int] = []
    structured_only = 0
    direct_only = 0
    both_pass = 0
    both_fail = 0

    for pair in pairs:
        direct = bool(pair["direct"]["hvr"])
        structured = bool(pair["structured"]["hvr"])
        difference = int(structured) - int(direct)
        differences.append(difference)
        if structured and not direct:
            structured_only += 1
        elif direct and not structured:
            direct_only += 1
        elif direct and structured:
            both_pass += 1
        else:
            both_fail += 1

    point = _mean(float(value) for value in differences)
    ci_low, ci_high = paired_bootstrap_difference_ci(
        differences,
        confidence=confidence,
        replicates=bootstrap_replicates,
        seed=bootstrap_seed,
    )
    direct_hvr = _mean(float(pair["direct"]["hvr"]) for pair in pairs)
    structured_hvr = _mean(float(pair["structured"]["hvr"]) for pair in pairs)

    family_reports: dict[str, Any] = {}
    for family in FAMILIES:
        family_rows = [row for row in rows if row["task_family"] == family]
        if family_rows:
            family_pairs = pair_rows(family_rows)
            family_differences = [
                int(pair["structured"]["hvr"]) - int(pair["direct"]["hvr"])
                for pair in family_pairs
            ]
            family_reports[family] = {
                "paired_units": len(family_pairs),
                "direct_hvr": _mean(float(pair["direct"]["hvr"]) for pair in family_pairs),
                "structured_hvr": _mean(float(pair["structured"]["hvr"]) for pair in family_pairs),
                "difference": _mean(float(value) for value in family_differences),
            }

    return {
        "analysis_version": "vericodegen-analysis-v1",
        "paired_units": len(pairs),
        "primary": {
            "endpoint": "hard_verifiability_rate",
            "contrast": "structured_minus_direct",
            "direct_hvr": direct_hvr,
            "structured_hvr": structured_hvr,
            "difference": point,
            "confidence": confidence,
            "paired_bootstrap_percentile_ci": [ci_low, ci_high],
            "bootstrap_replicates": bootstrap_replicates,
            "bootstrap_seed": bootstrap_seed,
            "mcnemar_exact_two_sided_p": exact_mcnemar_pvalue(structured_only, direct_only),
            "discordance": {
                "structured_only_pass": structured_only,
                "direct_only_pass": direct_only,
                "both_pass": both_pass,
                "both_fail": both_fail,
            },
        },
        "arms": {
            "direct": _arm_summary(rows, "direct"),
            "structured": _arm_summary(rows, "structured"),
        },
        "by_task_family": family_reports,
        "interpretation_gate": (
            "Secondary endpoints and strata are descriptive/exploratory and do not override "
            "the frozen primary HVR endpoint."
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outcomes", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--bootstrap-replicates", type=int, default=10000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260831)
    args = parser.parse_args()

    report = analyze_rows(
        load_jsonl(args.outcomes),
        bootstrap_replicates=args.bootstrap_replicates,
        bootstrap_seed=args.bootstrap_seed,
    )
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
