"""Protocol-guarded analysis helpers for NeuroCAD's human-AI pilot.

This module intentionally keeps the HAS-derived required-human-involvement
rating separate from objective task performance and from behavioral reliance.
H1-H5 is ordinal; no function here exposes a mean or treats the labels as a
validated latent psychological score.

The implementation follows the dated NeuroCAD amendment prompted by
Professor Jessie Chin's 2026-09-10 recommendation.  It is secondary/process
measurement code only and must not be used to redefine the frozen primary
endpoint or to choose which advice items count as useful/wrong after outcomes.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from statistics import median
from typing import Literal

HAS_LABELS: tuple[str, ...] = ("H1", "H2", "H3", "H4", "H5")
HAS_ANCHORS: dict[str, str] = {
    "H1": "The AI could handle the task entirely without my involvement.",
    "H2": "The AI needed my input at a few key points to achieve better task performance.",
    "H3": "The AI and I needed to work together as approximately equal partners.",
    "H4": "The AI needed my input to successfully complete the task.",
    "H5": "Successful task completion fully relied on my involvement.",
}
ASSISTED_CONDITIONS: tuple[str, ...] = ("useful_advice", "plausible_wrong_advice")
BehaviorCategory = Literal["accepted", "modified", "rejected", "not_observable"]


def _clean_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    out = value.strip()
    if len(out) > 128:
        raise ValueError(f"{field} must be at most 128 characters")
    if any(ord(ch) < 32 for ch in out):
        raise ValueError(f"{field} must not contain control characters")
    return out


def _finite_optional(value: object, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric or null")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{field} must be finite")
    return out


def _has_label(value: object) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        value = f"H{value}"
    if not isinstance(value, str):
        raise TypeError("has_rating must be H1-H5")
    value = value.strip().upper()
    if value not in HAS_LABELS:
        raise ValueError("has_rating must be one of H1, H2, H3, H4, H5")
    return value


@dataclass(frozen=True)
class HASObservation:
    """One block-level required-human-involvement self-report.

    The observation is valid only for an AI-assisted block.  Objective score,
    advice behavior and response time are optional triangulation fields and are
    not combined into the HAS rating.
    """

    participant_id: str
    block_id: str
    task_id: str
    condition: Literal["useful_advice", "plausible_wrong_advice"]
    has_rating: str
    objective_score: float | None = None
    advice_uptake: bool | None = None
    response_time_s: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "participant_id", _clean_id(self.participant_id, "participant_id"))
        object.__setattr__(self, "block_id", _clean_id(self.block_id, "block_id"))
        object.__setattr__(self, "task_id", _clean_id(self.task_id, "task_id"))
        if self.condition not in ASSISTED_CONDITIONS:
            raise ValueError(
                "HAS is defined only for AI-assisted blocks; condition must be "
                "'useful_advice' or 'plausible_wrong_advice'"
            )
        object.__setattr__(self, "has_rating", _has_label(self.has_rating))
        score = _finite_optional(self.objective_score, "objective_score")
        response_time = _finite_optional(self.response_time_s, "response_time_s")
        if response_time is not None and response_time < 0:
            raise ValueError("response_time_s must be non-negative")
        if self.advice_uptake is not None and not isinstance(self.advice_uptake, bool):
            raise TypeError("advice_uptake must be bool or null")
        object.__setattr__(self, "objective_score", score)
        object.__setattr__(self, "response_time_s", response_time)

    @property
    def ordinal(self) -> int:
        """Return the order index solely for ordering/transitions, never averaging."""
        return HAS_LABELS.index(self.has_rating) + 1

    def to_dict(self) -> dict[str, object]:
        return {
            "participant_id": self.participant_id,
            "block_id": self.block_id,
            "task_id": self.task_id,
            "condition": self.condition,
            "has_rating": self.has_rating,
            "objective_score": self.objective_score,
            "advice_uptake": self.advice_uptake,
            "response_time_s": self.response_time_s,
        }


@dataclass(frozen=True)
class BehaviorCode:
    """Independent coder label for observable advice-handling behavior."""

    participant_id: str
    block_id: str
    task_id: str
    coder_id: str
    category: BehaviorCategory

    def __post_init__(self) -> None:
        for field in ("participant_id", "block_id", "task_id", "coder_id"):
            object.__setattr__(self, field, _clean_id(getattr(self, field), field))
        if self.category not in {"accepted", "modified", "rejected", "not_observable"}:
            raise ValueError("unsupported behavior category")

    @property
    def item_key(self) -> tuple[str, str, str]:
        return (self.participant_id, self.block_id, self.task_id)


def _ordinal_quartiles(values: Sequence[int]) -> tuple[int, int, int]:
    """Return median and Tukey-style lower/upper medians for an ordinal sample."""
    if not values:
        raise ValueError("at least one ordinal value is required")
    ordered = sorted(values)
    n = len(ordered)
    med = int(median(ordered))
    if n == 1:
        return ordered[0], ordered[0], ordered[0]
    lower = ordered[: n // 2]
    upper = ordered[(n + 1) // 2 :]
    return int(median(lower)), med, int(median(upper))


def summarize_has(observations: Iterable[HASObservation]) -> dict[str, object]:
    """Summarize H1-H5 without treating the ordinal response as continuous.

    Returns full distributions, median/IQR labels, and paired participant
    transitions where each participant has observations in both assisted
    conditions.  Repeated blocks are reduced to the participant-condition
    median category solely for the transition display.
    """

    rows = tuple(observations)
    if not rows:
        raise ValueError("no HAS observations supplied")

    seen: set[tuple[str, str, str]] = set()
    by_condition: dict[str, list[HASObservation]] = defaultdict(list)
    by_participant_condition: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in rows:
        key = (row.participant_id, row.block_id, row.task_id)
        if key in seen:
            raise ValueError(f"duplicate HAS observation for participant/block/task: {key}")
        seen.add(key)
        by_condition[row.condition].append(row)
        by_participant_condition[(row.participant_id, row.condition)].append(row.ordinal)

    condition_summaries: dict[str, object] = {}
    for condition in ASSISTED_CONDITIONS:
        group = by_condition.get(condition, [])
        counts = Counter(row.has_rating for row in group)
        summary: dict[str, object] = {
            "n": len(group),
            "distribution": {label: counts.get(label, 0) for label in HAS_LABELS},
        }
        if group:
            q1, med, q3 = _ordinal_quartiles([row.ordinal for row in group])
            summary["median"] = f"H{med}"
            summary["iqr"] = [f"H{q1}", f"H{q3}"]
            uptake = [row.advice_uptake for row in group if row.advice_uptake is not None]
            if uptake:
                summary["advice_uptake"] = {
                    "n_observed": len(uptake),
                    "accepted": sum(bool(value) for value in uptake),
                    "rejected_or_overridden": sum(not bool(value) for value in uptake),
                }
        condition_summaries[condition] = summary

    participants = {row.participant_id for row in rows}
    transitions: list[dict[str, object]] = []
    for participant_id in sorted(participants):
        useful = by_participant_condition.get((participant_id, "useful_advice"))
        wrong = by_participant_condition.get((participant_id, "plausible_wrong_advice"))
        if not useful or not wrong:
            continue
        useful_med = int(median(sorted(useful)))
        wrong_med = int(median(sorted(wrong)))
        transitions.append(
            {
                "participant_id": participant_id,
                "useful_advice": f"H{useful_med}",
                "plausible_wrong_advice": f"H{wrong_med}",
                "direction": "higher_required_human_involvement"
                if wrong_med > useful_med
                else "lower_required_human_involvement"
                if wrong_med < useful_med
                else "no_category_change",
            }
        )

    return {
        "measure": "HAS-derived required-human-involvement rating",
        "scale_type": "ordinal",
        "conditions": condition_summaries,
        "paired_participant_transitions": transitions,
        "interpretation_guard": (
            "Do not interpret higher H labels as inherently better collaboration, "
            "a validated latent agency score, or a replacement for objective task performance."
        ),
    }


def pair_behavior_codes(
    codes: Iterable[BehaviorCode],
    *,
    coder_a: str,
    coder_b: str,
) -> tuple[tuple[BehaviorCategory, BehaviorCategory], ...]:
    """Pair two coders on exactly the shared task items.

    Duplicate coding by the same coder for the same item is rejected rather
    than silently overwritten.
    """

    coder_a = _clean_id(coder_a, "coder_a")
    coder_b = _clean_id(coder_b, "coder_b")
    if coder_a == coder_b:
        raise ValueError("coder_a and coder_b must differ")

    lookup: dict[tuple[str, tuple[str, str, str]], BehaviorCategory] = {}
    for code in codes:
        key = (code.coder_id, code.item_key)
        if key in lookup:
            raise ValueError(f"duplicate behavior code for coder/item: {key}")
        lookup[key] = code.category

    items_a = {item for coder, item in lookup if coder == coder_a}
    items_b = {item for coder, item in lookup if coder == coder_b}
    shared = sorted(items_a & items_b)
    if not shared:
        raise ValueError("the two coders have no shared coded items")
    return tuple((lookup[(coder_a, item)], lookup[(coder_b, item)]) for item in shared)


def agreement_report(
    pairs: Iterable[tuple[BehaviorCategory, BehaviorCategory]],
) -> dict[str, object]:
    """Compute exact agreement and unweighted Cohen's kappa.

    The behavior labels are nominal.  ``not_observable`` remains a real category
    so missing evidence cannot be silently converted into agreement.
    """

    rows = tuple(pairs)
    if not rows:
        raise ValueError("at least one coder pair is required")

    valid: tuple[BehaviorCategory, ...] = (
        "accepted",
        "modified",
        "rejected",
        "not_observable",
    )
    for left, right in rows:
        if left not in valid or right not in valid:
            raise ValueError("unsupported behavior category in coder pair")

    n = len(rows)
    observed = sum(1 for left, right in rows if left == right) / n
    left_counts = Counter(left for left, _ in rows)
    right_counts = Counter(right for _, right in rows)
    expected = sum((left_counts[label] / n) * (right_counts[label] / n) for label in valid)
    if math.isclose(expected, 1.0):
        kappa: float | None = 1.0 if math.isclose(observed, 1.0) else None
    else:
        kappa = (observed - expected) / (1.0 - expected)

    confusion: dict[str, dict[str, int]] = {
        left: {right: 0 for right in sorted(valid)} for left in sorted(valid)
    }
    for left, right in rows:
        confusion[left][right] += 1

    return {
        "n_shared_items": n,
        "percent_agreement": 100.0 * observed,
        "cohens_kappa": kappa,
        "confusion_matrix": confusion,
        "coding_note": (
            "Behavioral agreement is a triangulation check only; it is not the HAS self-report "
            "and must not be averaged with HAS or objective performance."
        ),
    }


def observations_from_records(records: Iterable[Mapping[str, object]]) -> tuple[HASObservation, ...]:
    """Build observations from strict record mappings.

    Extra columns are rejected so accidental identifiers or post-hoc variables
    do not silently enter the analysis surface.
    """

    allowed = {
        "participant_id",
        "block_id",
        "task_id",
        "condition",
        "has_rating",
        "objective_score",
        "advice_uptake",
        "response_time_s",
    }
    required = {"participant_id", "block_id", "task_id", "condition", "has_rating"}
    out: list[HASObservation] = []
    for index, record in enumerate(records):
        keys = set(record)
        missing = required - keys
        extra = keys - allowed
        if missing:
            raise ValueError(f"record {index} missing fields: {', '.join(sorted(missing))}")
        if extra:
            raise ValueError(f"record {index} has unsupported fields: {', '.join(sorted(extra))}")
        condition = record["condition"]
        if condition not in ASSISTED_CONDITIONS:
            raise ValueError(f"record {index} uses a non-assisted/unknown condition")
        objective_score = _finite_optional(record.get("objective_score"), "objective_score")
        response_time_s = _finite_optional(record.get("response_time_s"), "response_time_s")
        out.append(
            HASObservation(
                participant_id=_clean_id(record["participant_id"], "participant_id"),
                block_id=_clean_id(record["block_id"], "block_id"),
                task_id=_clean_id(record["task_id"], "task_id"),
                condition=condition,  # type: ignore[arg-type]
                has_rating=_has_label(record["has_rating"]),
                objective_score=objective_score,
                advice_uptake=record.get("advice_uptake"),  # type: ignore[arg-type]
                response_time_s=response_time_s,
            )
        )
    return tuple(out)
