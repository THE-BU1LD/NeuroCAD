from __future__ import annotations

import math

import pytest

from core.human_agency import (
    BehaviorCode,
    HASObservation,
    agreement_report,
    observations_from_records,
    pair_behavior_codes,
    summarize_has,
)


def _obs(pid: str, condition: str, rating: str, *, uptake: bool | None = None) -> HASObservation:
    return HASObservation(
        participant_id=pid,
        block_id=f"{pid}-{condition}",
        task_id="task-1",
        condition=condition,  # type: ignore[arg-type]
        has_rating=rating,
        objective_score=0.8,
        advice_uptake=uptake,
        response_time_s=45.0,
    )


def test_has_rejects_unaided_control() -> None:
    with pytest.raises(ValueError, match="AI-assisted"):
        HASObservation(
            participant_id="p1",
            block_id="b1",
            task_id="t1",
            condition="unaided",  # type: ignore[arg-type]
            has_rating="H3",
        )


@pytest.mark.parametrize("rating", ["H0", "H6", "3.5", "", None])
def test_has_rejects_invalid_categories(rating: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        HASObservation(
            participant_id="p1",
            block_id="b1",
            task_id="t1",
            condition="useful_advice",
            has_rating=rating,  # type: ignore[arg-type]
        )


def test_summary_is_distributional_and_ordinal() -> None:
    report = summarize_has(
        [
            _obs("p1", "useful_advice", "H2", uptake=True),
            _obs("p2", "useful_advice", "H3", uptake=False),
            _obs("p3", "useful_advice", "H3", uptake=True),
            _obs("p1", "plausible_wrong_advice", "H4", uptake=False),
            _obs("p2", "plausible_wrong_advice", "H3", uptake=True),
            _obs("p3", "plausible_wrong_advice", "H5", uptake=False),
        ]
    )

    useful = report["conditions"]["useful_advice"]  # type: ignore[index]
    wrong = report["conditions"]["plausible_wrong_advice"]  # type: ignore[index]
    assert useful["distribution"] == {"H1": 0, "H2": 1, "H3": 2, "H4": 0, "H5": 0}
    assert useful["median"] == "H3"
    assert wrong["median"] == "H4"
    assert "mean" not in useful
    assert len(report["paired_participant_transitions"]) == 3  # type: ignore[arg-type]


def test_duplicate_block_task_rejected() -> None:
    row = _obs("p1", "useful_advice", "H2")
    with pytest.raises(ValueError, match="duplicate HAS"):
        summarize_has([row, row])


def test_record_parser_rejects_extra_posthoc_columns() -> None:
    with pytest.raises(ValueError, match="unsupported fields"):
        observations_from_records(
            [
                {
                    "participant_id": "p1",
                    "block_id": "b1",
                    "task_id": "t1",
                    "condition": "useful_advice",
                    "has_rating": "H3",
                    "outcome_selected_item_difficulty": 0.9,
                }
            ]
        )


def test_behavior_pairing_and_kappa_perfect() -> None:
    codes = [
        BehaviorCode("p1", "b1", "t1", "a", "accepted"),
        BehaviorCode("p1", "b1", "t1", "b", "accepted"),
        BehaviorCode("p2", "b2", "t1", "a", "rejected"),
        BehaviorCode("p2", "b2", "t1", "b", "rejected"),
        BehaviorCode("p3", "b3", "t1", "a", "modified"),
        BehaviorCode("p3", "b3", "t1", "b", "modified"),
    ]
    pairs = pair_behavior_codes(codes, coder_a="a", coder_b="b")
    report = agreement_report(pairs)
    assert report["percent_agreement"] == 100.0
    assert report["cohens_kappa"] == 1.0


def test_behavior_kappa_known_case() -> None:
    report = agreement_report(
        [
            ("accepted", "accepted"),
            ("accepted", "rejected"),
            ("rejected", "rejected"),
            ("rejected", "accepted"),
        ]
    )
    assert report["percent_agreement"] == 50.0
    assert math.isclose(report["cohens_kappa"], 0.0, abs_tol=1e-12)


def test_duplicate_coder_item_rejected() -> None:
    duplicate = BehaviorCode("p1", "b1", "t1", "a", "accepted")
    codes = [
        duplicate,
        duplicate,
        BehaviorCode("p1", "b1", "t1", "b", "accepted"),
    ]
    with pytest.raises(ValueError, match="duplicate behavior code"):
        pair_behavior_codes(codes, coder_a="a", coder_b="b")
