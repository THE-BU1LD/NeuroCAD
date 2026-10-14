"""Adversarial development fixtures; these are not an independent benchmark."""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from core.conversational_parser import parse_conversation
from core.language_comparison import compare_runs, load_run, main
from core.language_evaluation import evaluate, score_proposal, validate_challenge
from core.project import parse_project
from core.requirement_ir import (
    Requirement,
    RequirementBinding,
    RequirementIR,
    RequirementIRParseError,
    RequirementValue,
    requirement_coverage,
    requirement_ir_from_dict,
    validate_requirement_ir,
)

ROOT = Path(__file__).resolve().parents[1]


def requirement():
    return RequirementIR("width", (Requirement("width", "dimension", "must", "width", 0, 5, "width", "explicit",
                                            "exact_dimension", RequirementValue(80, "mm")),))


@pytest.mark.parametrize("field", ["id", "kind", "strength", "provenance", "verification", "target", "source_start", "source_end"])
@pytest.mark.parametrize("value", [[], {}, None, True])
def test_malformed_fields_have_structured_errors(field, value):
    raw = requirement().to_dict()
    raw["requirements"][0][field] = value
    with pytest.raises(RequirementIRParseError):
        requirement_ir_from_dict(raw)


@pytest.mark.parametrize("field", ["source", "value", "tolerance", "metadata"])
def test_nonstring_source_and_float_overflow_are_rejected(field):
    raw = requirement().to_dict()
    if field == "source":
        raw[field] = None
    elif field == "metadata":
        raw[field] = {"number": 10**400}
    else:
        raw["requirements"][0]["value"][field] = 10**400
    with pytest.raises(RequirementIRParseError):
        requirement_ir_from_dict(raw)


@pytest.mark.parametrize("field,value", [("requirements", None), ("requirements", (None,)), ("metadata", None)])
def test_direct_document_validation_does_not_crash(field, value):
    document = replace(requirement(), **{field: value})
    assert not validate_requirement_ir(document).structurally_valid
    assert not requirement_coverage(document, ()).complete_for_must


def test_empty_feature_universe_is_not_an_omitted_universe():
    bindings = (RequirementBinding("width", ("invented",), "exact_dimension"),)
    assert requirement_coverage(requirement(), bindings).complete_for_must
    report = requirement_coverage(requirement(), bindings, known_feature_ids=())
    assert not report.complete_for_must
    assert report.missing_must == ("width",)
    assert report.invalid_bindings[0].code == "unknown_feature"


@pytest.mark.parametrize("binding", [None, RequirementBinding([], (), "exact_dimension"),
                                     RequirementBinding("width", ([],), "exact_dimension")])
def test_bad_bindings_fail_closed(binding):
    assert not requirement_coverage(requirement(), (binding,)).complete_for_must


def challenge(tmp_path):
    raw = json.loads((ROOT / "docs/examples/conversation/language-challenge-v1.json").read_text(encoding="utf-8"))
    raw["cases"] = [raw["cases"][0], raw["cases"][20]]
    path = tmp_path / "challenge.json"
    # Deliberate CRLF and Unicode test preservation of input bytes on every OS.
    raw["provenance"]["description"] = "Constructed – developer fixture"
    path.write_bytes((json.dumps(raw, ensure_ascii=False, indent=2) + "\n").replace("\n", "\r\n").encode())
    return raw, path


def test_validation_does_not_normalize_callers_labels_in_place(tmp_path):
    raw, _ = challenge(tmp_path)
    before = copy.deepcopy(raw)
    normalized = validate_challenge(raw)
    normalized["cases"][0]["history"].append("modified")
    assert raw == before


@pytest.mark.parametrize("when", ["before", "after"])
def test_mutated_project_never_earns_success(tmp_path, when):
    _, path = challenge(tmp_path)

    class Provider:
        def interpret(self, source, project, *, recent_messages):
            if when == "before":
                object.__setattr__(project, "project_id", "mutated-valid-id")
            proposal = parse_conversation(source, project)
            if when == "after":
                object.__setattr__(project, "project_id", "mutated-valid-id")
            return proposal

    summary = evaluate(path, tmp_path / "run", provider=Provider())
    assert summary["input_mutation_count"] == 2
    assert summary["semantic_exact_count"] == summary["fail_closed_count"] == summary["passed_count"] == 0
    assert load_run(tmp_path / "run")["summary"] == summary


def test_mutated_history_does_not_change_frozen_challenge_or_earn_credit(tmp_path):
    _, path = challenge(tmp_path)

    class Provider:
        def interpret(self, source, project, *, recent_messages):
            recent_messages.append("rewritten context")
            return parse_conversation(source, project)

    summary = evaluate(path, tmp_path / "run", provider=Provider())
    assert (tmp_path / "run/challenge.json").read_bytes() == path.read_bytes()
    assert summary["input_mutation_count"] == 2
    assert summary["passed_count"] == 0
    load_run(tmp_path / "run")


def test_unknown_status_is_not_successful_rejection(tmp_path):
    raw, _ = challenge(tmp_path)
    case = raw["cases"][1]
    project = parse_project(json.dumps(raw["projects"][case["project"]]))
    proposal = replace(parse_conversation(case["source"], project), status="invented")
    assert not score_proposal(proposal, case["expected"], project)["fail_closed"]


def reseal(directory):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for name in manifest["files"]:
        manifest["files"][name] = hashlib.sha256((directory / name).read_bytes()).hexdigest()
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_matched_comparison_separates_semantic_rejection_and_harm(tmp_path):
    _, path = challenge(tmp_path)
    evaluate(path, tmp_path / "left")

    class RejectAll:
        def interpret(self, source, project, *, recent_messages):
            proposal = parse_conversation(source, project)
            return replace(proposal, candidate=None, status="clarification")

    evaluate(path, tmp_path / "right", provider=RejectAll(), provider_label="reject-all-control")
    result = compare_runs(tmp_path / "left", tmp_path / "right")
    assert result["endpoints"]["semantic_exact"]["left_only"] == 1
    assert result["endpoints"]["semantic_exact"]["right_minus_left_rate"] == -1
    assert result["endpoints"]["fail_closed"]["both_true"] == 1
    assert result["endpoints"]["unsafe_acceptance"]["both_false"] == 2
    assert main([str(tmp_path / "left"), str(tmp_path / "right"), "--output", str(tmp_path / "comparison.json")]) == 0
    with pytest.raises(SystemExit):
        main([str(tmp_path / "left"), str(tmp_path / "right"), "--output", str(tmp_path / "comparison.json")])


@pytest.mark.parametrize("mutation", ["bytes", "partial", "duplicate", "score", "summary", "policy", "integrity"])
def test_comparison_refuses_corrupt_and_resealed_inconsistent_reports(tmp_path, mutation):
    _, path = challenge(tmp_path)
    directory = tmp_path / "run"
    evaluate(path, directory)
    results_path = directory / "results.jsonl"
    rows = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines()]
    if mutation in {"bytes", "partial"}:
        results_path.write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
    elif mutation in {"duplicate", "score"}:
        if mutation == "duplicate":
            rows[1] = rows[0]
        else:
            rows[0]["semantic_exact"] = False
        results_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    else:
        target = directory / ("receipt.json" if mutation == "policy" else "summary.json")
        raw = json.loads(target.read_text(encoding="utf-8"))
        if mutation == "policy":
            raw["execution_policy"]["runner_retries"] = 3
        elif mutation == "integrity":
            raw["integrity_valid"] = False
        else:
            raw["semantic_exact_count"] = 999
        target.write_text(json.dumps(raw), encoding="utf-8")
    if mutation != "bytes":
        reseal(directory)
    with pytest.raises(ValueError):
        load_run(directory)


def test_comparison_requires_identical_dataset_bytes(tmp_path):
    _, path = challenge(tmp_path)
    evaluate(path, tmp_path / "left")
    path.write_bytes(path.read_bytes() + b"\n")
    evaluate(path, tmp_path / "right")
    with pytest.raises(ValueError, match="same frozen"):
        compare_runs(tmp_path / "left", tmp_path / "right")


def test_embedded_project_overflow_rejects_before_creating_run(tmp_path):
    raw, path = challenge(tmp_path)
    raw["projects"][raw["cases"][0]["project"]]["spec"]["wall_mm"] = 10**400
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="finite"):
        evaluate(path, tmp_path / "run")
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize("mutation", ["status", "preserve", "nan-metadata"])
def test_malformed_provider_output_is_retained_as_error(tmp_path, mutation):
    _, path = challenge(tmp_path)

    class Provider:
        def interpret(self, source, project, *, recent_messages):
            proposal = parse_conversation(source, project)
            values = {"status": {"status": []}, "preserve": {"preserve": ({"field": []},)},
                      "nan-metadata": {"provider_metadata": {"x": float("nan")}}}
            return replace(proposal, **values[mutation])

    summary = evaluate(path, tmp_path / "run", provider=Provider())
    assert summary["provider_error_count"] == 2
    assert summary["passed_count"] == 0
    load_run(tmp_path / "run")


def test_source_drift_invalidates_completed_run(tmp_path, monkeypatch):
    from core import language_evaluation

    _, path = challenge(tmp_path)
    identities = iter([{"example.py": "before"}, {"example.py": "after"}])
    monkeypatch.setattr(language_evaluation, "_source_identity", lambda: next(identities))
    summary = evaluate(path, tmp_path / "run")
    assert summary["completed_cases"] == 2
    assert not summary["integrity_valid"]
    with pytest.raises(ValueError, match="identity"):
        load_run(tmp_path / "run")
