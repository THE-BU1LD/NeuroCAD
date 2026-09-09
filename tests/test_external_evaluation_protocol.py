from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "protocols" / "EXTERNAL_EVALUATION_V0.md"


def _protocol_text() -> str:
    return PROTOCOL.read_text(encoding="utf-8")


def test_external_evaluation_protocol_is_preoutcome_and_not_misreported() -> None:
    text = _protocol_text()

    assert "**Protocol ID:** NC-EXT-EVAL-V0" in text
    assert "PREOUTCOME / DATA_NOT_MATERIALIZED / NOT_EXECUTED" in text
    assert "OUTCOMES_NOT_OBSERVED" in text
    assert "EVIDENCE_PARTIAL" in text
    assert "Merely adding this protocol does **not** close that gate." in text


def test_external_evaluation_protocol_requires_independent_authorship_and_adjudication() -> None:
    text = _protocol_text()

    assert "did not implement the evaluated parser rules" in text
    assert "A separate adjudicator must independently verify each reference signature or rejection label" in text
    assert "author and adjudicator are the same person" in text


def test_external_evaluation_protocol_freezes_source_and_data_before_outcome_access() -> None:
    text = _protocol_text()

    required_receipt_fields = (
        "exact Git commit SHA",
        "source-snapshot SHA-256",
        "`requirements-research.lock` SHA-256",
        "challenge JSONL SHA-256",
        "scoring implementation SHA-256",
        "explicit `outcomes_observed=false`",
    )
    for field in required_receipt_fields:
        assert field in text
    assert "If any required identity is missing, the run remains `NOT_AUTHORIZED`." in text


def test_external_evaluation_protocol_separates_validity_and_rejection_endpoints() -> None:
    text = _protocol_text()

    assert "**Valid semantic exact rate:**" in text
    assert "**Fail-closed rejection rate:**" in text
    assert "must not be averaged into one headline score" in text


def test_external_evaluation_protocol_forbids_post_outcome_rescue() -> None:
    text = _protocol_text()

    assert "No adaptive prompt rewriting after failures." in text
    assert "No parser edits after label access inside the confirmatory run." in text
    assert "No exclusion is allowed because NeuroCAD or a comparator failed." in text
    assert "cannot be used to rehabilitate the falsified historical typed-parser causal claim" in text


def test_external_evaluation_protocol_requires_stronger_comparator_for_comparative_claims() -> None:
    text = _protocol_text()

    assert "strong grammar-independent comparator is additionally required" in text
    assert "weaken comparative claims rather than substitute a weaker baseline post hoc" in text
