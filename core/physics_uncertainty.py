"""Deterministic uncertainty wrappers for bounded analytical physics models."""

from __future__ import annotations

import itertools
import math
import random
import statistics
from dataclasses import fields
from typing import Any, Callable

from .physics_context import canonical_sha256

UNCERTAINTY_VERSION = "neurocad-physics-uncertainty-v1"


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _numeric_results(report: dict[str, Any]) -> dict[str, float]:
    raw = report.get("results")
    if not isinstance(raw, dict):
        raise TypeError("physics evaluator must return a results object")
    return {
        name: float(value)
        for name, value in raw.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))
    }


def _selected_outputs(report: dict[str, Any], requested: Any) -> list[str]:
    available = _numeric_results(report)
    if requested is None:
        if not available:
            raise ValueError("physics result has no scalar numeric outputs for uncertainty propagation")
        return sorted(available)
    if not isinstance(requested, list) or not requested or any(not isinstance(item, str) or not item for item in requested):
        raise ValueError("uncertainty.outputs must be a non-empty list of result names")
    if len(set(requested)) != len(requested):
        raise ValueError("uncertainty.outputs must be unique")
    missing = sorted(set(requested) - set(available))
    if missing:
        raise ValueError(f"uncertainty outputs are not scalar numeric results: {', '.join(missing)}")
    return list(requested)


def _bounds(raw: Any, base_inputs: dict[str, Any], input_type: type[Any]) -> dict[str, tuple[float, float]]:
    if not isinstance(raw, dict) or not raw:
        raise ValueError("uncertainty.inputs must define at least one bounded input")
    allowed = {field.name for field in fields(input_type)}
    if len(raw) > 12:
        raise ValueError("uncertainty propagation supports at most 12 varying inputs")
    result: dict[str, tuple[float, float]] = {}
    for name, value in raw.items():
        if name not in allowed or name not in base_inputs:
            raise ValueError(f"uncertainty input {name!r} is not a supplied model input")
        if not isinstance(base_inputs[name], (int, float)) or isinstance(base_inputs[name], bool):
            raise ValueError(f"uncertainty input {name!r} is not a top-level numeric scalar")
        if not isinstance(value, dict) or set(value) != {"lower", "upper"}:
            raise ValueError(f"uncertainty.inputs.{name} requires exactly lower and upper")
        lower = _finite(value["lower"], f"uncertainty.inputs.{name}.lower")
        upper = _finite(value["upper"], f"uncertainty.inputs.{name}.upper")
        base = _finite(base_inputs[name], f"inputs.{name}")
        if lower >= upper:
            raise ValueError(f"uncertainty.inputs.{name} requires lower < upper")
        if not lower <= base <= upper:
            raise ValueError(f"base inputs.{name} must lie within its uncertainty bounds")
        result[name] = (lower, upper)
    return result


def _evaluate(
    input_type: type[Any],
    evaluator: Callable[[Any], dict[str, Any]],
    base_inputs: dict[str, Any],
    changes: dict[str, float],
) -> dict[str, Any]:
    inputs = {**base_inputs, **changes}
    return evaluator(input_type(**inputs))


def propagate_uncertainty(
    input_type: type[Any],
    evaluator: Callable[[Any], dict[str, Any]],
    base_inputs: dict[str, Any],
    raw: Any,
) -> dict[str, Any]:
    """Apply interval-corner, seeded Monte Carlo, or local-sensitivity analysis."""

    if not isinstance(raw, dict):
        raise TypeError("uncertainty must be an object")
    allowed = {"method", "inputs", "outputs", "samples", "seed", "step_fraction"}
    extra = sorted(set(raw) - allowed)
    missing = sorted({"method", "inputs"} - set(raw))
    if extra or missing:
        raise ValueError(f"uncertainty requires method and inputs; unsupported={extra}, missing={missing}")
    method = raw["method"]
    if method not in {"interval", "monte_carlo", "local_sensitivity"}:
        raise ValueError("uncertainty.method must be interval, monte_carlo, or local_sensitivity")
    bounds = _bounds(raw["inputs"], base_inputs, input_type)
    base_report = evaluator(input_type(**base_inputs))
    outputs = _selected_outputs(base_report, raw.get("outputs"))
    base_values = _numeric_results(base_report)
    common: dict[str, Any] = {
        "schema_version": UNCERTAINTY_VERSION,
        "method": method,
        "input_bounds": {name: {"lower": pair[0], "upper": pair[1]} for name, pair in bounds.items()},
        "outputs": outputs,
        "base_input_sha256": canonical_sha256(base_inputs),
        "claim_boundary": "screening uncertainty over declared scalar ranges; not a probability or global-proof claim unless explicitly stated",
    }

    if method == "interval":
        if "samples" in raw or "seed" in raw or "step_fraction" in raw:
            raise ValueError("interval uncertainty does not accept samples, seed, or step_fraction")
        evaluations: list[dict[str, Any]] = []
        names = list(bounds)
        for corner in itertools.product((0, 1), repeat=len(names)):
            changes = {name: bounds[name][choice] for name, choice in zip(names, corner, strict=True)}
            evaluations.append(_evaluate(input_type, evaluator, base_inputs, changes))
        summary = {}
        for output in outputs:
            values = [_numeric_results(report)[output] for report in evaluations]
            summary[output] = {"minimum": min(values), "maximum": max(values), "base": base_values[output]}
        return {
            **common,
            "evaluation_count": len(evaluations),
            "result_envelopes": summary,
            "method_boundary": "all declared box corners evaluated; this is not a rigorous global interval bound for non-monotone interiors",
        }

    if method == "monte_carlo":
        if "step_fraction" in raw:
            raise ValueError("monte_carlo uncertainty does not accept step_fraction")
        samples = raw.get("samples", 1_000)
        seed = raw.get("seed", 0)
        if isinstance(samples, bool) or not isinstance(samples, int) or not 2 <= samples <= 10_000:
            raise ValueError("uncertainty.samples must be an integer from 2 to 10000")
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**63 - 1:
            raise ValueError("uncertainty.seed must be an integer from 0 to 2^63-1")
        generator = random.Random(seed)
        collected: dict[str, list[float]] = {output: [] for output in outputs}
        failed_constraints = 0
        for _ in range(samples):
            changes = {name: generator.uniform(lower, upper) for name, (lower, upper) in bounds.items()}
            report = _evaluate(input_type, evaluator, base_inputs, changes)
            numeric = _numeric_results(report)
            for output in outputs:
                collected[output].append(numeric[output])
            results = report["results"]
            if isinstance(results, dict) and results.get("constraint_satisfied") is False:
                failed_constraints += 1
        summary = {
            output: {
                "mean": statistics.fmean(values),
                "sample_standard_deviation": statistics.stdev(values),
                "minimum": min(values),
                "p05": _percentile(values, 0.05),
                "p50": _percentile(values, 0.50),
                "p95": _percentile(values, 0.95),
                "maximum": max(values),
                "base": base_values[output],
            }
            for output, values in collected.items()
        }
        return {
            **common,
            "sample_count": samples,
            "seed": seed,
            "uniform_independent_sampling": True,
            "result_statistics": summary,
            "observed_constraint_failure_fraction": failed_constraints / samples,
            "method_boundary": "finite seeded samples from independent uniform input distributions; percentiles are empirical, not certified tails",
        }

    if "samples" in raw or "seed" in raw:
        raise ValueError("local_sensitivity uncertainty does not accept samples or seed")
    step_fraction = _finite(raw.get("step_fraction", 1e-4), "uncertainty.step_fraction")
    if not 0 < step_fraction <= 0.1:
        raise ValueError("uncertainty.step_fraction must be greater than zero and at most 0.1")
    sensitivities: dict[str, Any] = {}
    for name, (lower, upper) in bounds.items():
        base = _finite(base_inputs[name], f"inputs.{name}")
        delta = min((upper - lower) * step_fraction, base - lower, upper - base)
        if delta <= 0:
            raise ValueError(f"local_sensitivity requires base inputs.{name} strictly inside its bounds")
        lower_values = _numeric_results(_evaluate(input_type, evaluator, base_inputs, {name: base - delta}))
        upper_values = _numeric_results(_evaluate(input_type, evaluator, base_inputs, {name: base + delta}))
        sensitivities[name] = {
            "step": delta,
            "derivatives": {output: (upper_values[output] - lower_values[output]) / (2.0 * delta) for output in outputs},
        }
    return {
        **common,
        "step_fraction": step_fraction,
        "local_derivatives": sensitivities,
        "base_results": {output: base_values[output] for output in outputs},
        "method_boundary": "central finite differences at the declared base point; derivatives are local and step-size dependent",
    }
