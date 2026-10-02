from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from core.conversational_parser import parse_conversation
from core.language_evaluation import evaluate, main, score_proposal, validate_challenge
from core.language_provider import LanguageProviderError
from core.project import enclosure_spec_to_dict, parse_project

ROOT = Path(__file__).resolve().parents[1]


def challenge():
    return json.loads((ROOT / "docs/examples/conversation/language-challenge-v1.json").read_text(encoding="utf-8"))


def small_challenge(tmp_path, *, cases=None):
    raw = challenge()
    raw["cases"] = cases or [raw["cases"][0], raw["cases"][20]]
    path = tmp_path / "challenge.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def test_separate_semantic_and_rejection_endpoints(tmp_path):
    path = small_challenge(tmp_path)
    summary = evaluate(path, tmp_path / "results")
    assert summary["semantic_exact_rate"] == 1
    assert summary["fail_closed_rate"] == 1
    assert summary["baseline_unchanged"]
    assert not summary["live_provider_evaluated"]
    receipt = json.loads((tmp_path / "results/receipt.json").read_text(encoding="utf-8"))
    assert receipt["outcomes_observed"] is False
    assert (tmp_path / "results/challenge.json").read_bytes() == path.read_bytes()
    assert len((tmp_path / "results/results.jsonl").read_text(encoding="utf-8").splitlines()) == 2


def test_valid_but_wrong_geometry_does_not_count_as_understanding():
    raw = challenge()
    project = parse_project(json.dumps(raw["projects"]["one-hole"]))
    proposal = parse_conversation("walls 4mm", project)
    scored = score_proposal(proposal, raw["cases"][0]["expected"], project)
    assert scored["wrong_candidate"]
    assert not scored["semantic_exact"]
    assert not scored["passed"]


def test_unrelated_edit_fails_complete_spec_scoring():
    raw = challenge()
    project = parse_project(json.dumps(raw["projects"]["one-hole"]))
    proposal = parse_conversation("walls 3mm and floor thickness 3mm", project)
    assert not score_proposal(proposal, raw["cases"][0]["expected"], project)["passed"]


def test_unsafe_acceptance_is_separate_from_provider_error():
    raw = challenge()
    project = parse_project(json.dumps(raw["projects"]["one-hole"]))
    proposal = parse_conversation("walls 3mm", project)
    scored = score_proposal(proposal, raw["cases"][20]["expected"], project)
    assert scored["unsafe_acceptance"]
    assert not scored["fail_closed"]


def test_container_protection_implies_feature_and_lid_protection():
    raw = challenge()
    project = parse_project(json.dumps(raw["projects"]["one-hole"]))
    expected = copy.deepcopy(raw["cases"][0]["expected"])
    expected["preserve"] = ["cutout:power", "lid.thickness_mm"]
    proposal = parse_conversation("walls 3mm and dont move outside", project)
    assert score_proposal(proposal, expected, project)["passed"]
    assert not score_proposal(parse_conversation("walls 3mm", project), expected, project)["passed"]


def test_stale_context_cannot_score_exact():
    raw = challenge()
    project = parse_project(json.dumps(raw["projects"]["one-hole"]))
    proposal = replace(parse_conversation("walls 3mm", project), baseline_sha256="0" * 64)
    assert not score_proposal(proposal, raw["cases"][0]["expected"], project)["passed"]


def test_provider_never_sees_labels_and_gets_history(tmp_path):
    raw = challenge()
    case = raw["cases"][0]
    case["history"] = ["We are discussing walls."]
    calls = []

    class Provider:
        def interpret(self, source, project, *, recent_messages):
            calls.append((source, enclosure_spec_to_dict(project.spec), recent_messages))
            return parse_conversation(source, project)

    summary = evaluate(small_challenge(tmp_path, cases=[case]), tmp_path / "results", provider=Provider(), provider_label="controlled")
    assert calls[0][0] == case["source"]
    assert calls[0][2] == case["history"]
    assert summary["passed_count"] == 1
    assert not summary["live_provider_evaluated"]


def test_transport_error_is_not_successful_rejection_or_leaked(tmp_path):
    class Provider:
        def interpret(self, source, project, *, recent_messages):
            raise LanguageProviderError("secret-token-do-not-save")

    summary = evaluate(small_challenge(tmp_path), tmp_path / "results", provider=Provider())
    assert summary["provider_error_count"] == 2
    assert summary["fail_closed_count"] == 0
    assert summary["passed_count"] == 0
    assert "secret-token" not in (tmp_path / "results/results.jsonl").read_text(encoding="utf-8")


@pytest.mark.parametrize("mutation", ["duplicate-id", "missing-spec", "extra-case-key", "unknown-project", "invalid-history",
                                     "bad-status", "unknown-protection", "bad-provenance", "invalid-spec"])
def test_invalid_annotations_fail_before_output(tmp_path, mutation):
    raw = challenge()
    case = raw["cases"][0]
    if mutation == "duplicate-id":
        raw["cases"][1]["id"] = case["id"]
    elif mutation == "missing-spec":
        case["expected"]["spec"] = None
    elif mutation == "extra-case-key":
        case["surprise"] = True
    elif mutation == "unknown-project":
        case["project"] = "missing"
    elif mutation == "invalid-history":
        case["history"] = [1]
    elif mutation == "bad-status":
        case["expected"]["status"] = []
    elif mutation == "unknown-protection":
        case["expected"]["preserve"] = ["bad-field"]
    elif mutation == "bad-provenance":
        raw["provenance"]["kind"] = "independent-because-i-say-so"
    else:
        case["expected"]["spec"]["wall_mm"] = 40
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        evaluate(path, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_new_destination_and_cli_exit_codes(tmp_path):
    path = small_challenge(tmp_path)
    assert main([str(path), "--output-dir", str(tmp_path / "results")]) == 0
    with pytest.raises(ValueError):
        evaluate(path, tmp_path / "results")
    raw = challenge()
    path2 = small_challenge(tmp_path, cases=[raw["cases"][10]])
    assert main([str(path2), "--output-dir", str(tmp_path / "gaps")]) == 2


def test_live_declaration_requires_provider_and_external_is_not_verified(tmp_path):
    path = small_challenge(tmp_path)
    with pytest.raises(ValueError):
        evaluate(path, tmp_path / "results", live_provider=True)
    raw = challenge()
    raw["provenance"]["kind"] = "external-annotated"
    assert validate_challenge(raw)["provenance"]["kind"] == "external-annotated"
    path.write_text(json.dumps(raw), encoding="utf-8")
    summary = evaluate(path, tmp_path / "external")
    assert summary["independent_authorship_verified"] is False
