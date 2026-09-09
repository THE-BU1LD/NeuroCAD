from __future__ import annotations

from pathlib import Path

import pytest

from text_to_cad import TextToCAD


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "prompt",
    [
        "an aircraft with span 800 mm and length 900 mm",
        "a car with length 350 mm width 160 mm height 110 mm",
        "a motor with radius 45 mm and height 80 mm",
        "a desk 400 mm wide 250 mm deep and 120 mm high",
    ],
)
def test_quarantined_legacy_domains_fail_closed(prompt: str) -> None:
    """Plausible legacy generators must never re-enter the supported pipeline."""

    document = TextToCAD().build(prompt)

    assert document.program is None
    assert document.scad == ""
    assert not document.validation.valid
    assert any("unsupported domain" in error for error in document.validation.errors)


def test_research_truth_preserves_falsified_historical_claim() -> None:
    text = (ROOT / "RESEARCH_TRUTH.md").read_text(encoding="utf-8").casefold()

    assert "historical typed-parser causal claim is falsified" in text
    assert "evidence_partial" in text


def test_model_card_cannot_imply_a_trained_neurocad_model() -> None:
    text = (ROOT / "MODEL_CARD.md").read_text(encoding="utf-8").casefold()

    assert "contains no trained model" in text
    assert "deterministic compiler" in text


def test_primary_question_keeps_the_compiler_scope_explicit() -> None:
    text = (ROOT / "QUESTION.md").read_text(encoding="utf-8").casefold()

    assert "controlled compiler, not learned generation" in text
    assert "general text-to-cad intelligence" not in text


def test_conference_gate_remains_partial_until_external_evidence_exists() -> None:
    text = (ROOT / "audit" / "CONFERENCE_READINESS_CHECKLIST.md").read_text(encoding="utf-8").casefold()

    assert "evidence_partial" in text
    assert "independent, licensed, hashed prompt/spec set" in text
