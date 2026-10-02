from __future__ import annotations

import json
from dataclasses import replace

import pytest

from core.conversational_parser import apply_proposal, parse_conversation, validate_edit_payload
from core.enclosure import CutoutSpec, EnclosureSpec, LidSpec
from core.language_provider import ChatLanguageProvider, LanguageProviderError
from core.project import EnclosureProject, serialize_project, update_project, write_project
from neurocad_cli import build_parser


@pytest.fixture
def project():
    return EnclosureProject("language-test", EnclosureSpec(
        outer_size_mm=(80, 60, 30), wall_mm=2, floor_mm=2, profile="fdm_standard",
        lid=LidSpec("friction", 2.5, 0.3, lip_height_mm=2),
        cutouts=(CutoutSpec("power", "circular", "front", (0, 10), diameter_mm=4),),
    ))


def payload(source, instruction):
    return {"actions": [{"instruction": instruction, "evidence": {"text": source, "start": 0, "end": len(source)}}],
            "preserve": [], "questions": [], "unsupported": [], "acknowledged": []}


@pytest.mark.parametrize("text", [
    "please make the walls like 3mm thick", "wals thikness 0.3 cm", "set wall thickness to 3 millimetres",
    "okay just walls 3 mm please", "walls 0.11811023622047245 inches",
])
def test_messy_supported_phrasing_and_units(project, text):
    before = serialize_project(project)
    result = parse_conversation(text, project)
    assert result.status == "proposal"
    assert result.candidate.spec.wall_mm == pytest.approx(3)
    assert result.candidate.spec.cutouts == project.spec.cutouts
    assert serialize_project(project) == before
    assert result.to_dict()["requires_review"]
    for action in result.actions:
        ev = action["evidence"]
        assert text[ev["start"]:ev["end"]] == ev["text"]


def test_context_preservation_and_negation(project):
    text = "walls 3mm and dont move the outside and dont lose that hole"
    result = parse_conversation(text, project)
    assert result.status == "proposal"
    assert result.candidate.spec.outer_size_mm == project.spec.outer_size_mm
    assert result.candidate.spec.cutouts == project.spec.cutouts
    assert {"outer_size_mm", "cutouts", "corner_radius_mm"} <= {p["field"] for p in result.preserve}


def test_explicit_correction_is_audited(project):
    result = parse_conversation("walls 2.5mm no actually 3mm", project)
    assert result.status == "proposal"
    assert result.candidate.spec.wall_mm == 3
    assert any("Superseded" in item["reason"] for item in result.acknowledged)
    assert len(result.actions) == 1


@pytest.mark.parametrize("text", ["make it thicker", "wall thickness 3", "walls 3mm and walls 4mm", "walls 2mm and walls 3mm"])
def test_missing_units_or_conflicting_values_need_clarification(project, text):
    result = parse_conversation(text, project)
    assert result.status == "clarification"
    assert result.questions and result.candidate is None


def test_protected_boundary_conflict_and_invalid_geometry_publish_no_candidate(project):
    conflict = parse_conversation("resize enclosure to 90 x 60 x 30 mm and keep the outside same", project)
    assert conflict.status == "clarification" and conflict.candidate is None
    invalid = parse_conversation("walls 40mm", project)
    assert invalid.status == "rejected" and invalid.candidate is None


def test_ambiguous_hole_reference_is_not_guessed(project):
    second = CutoutSpec("other", "circular", "rear", (10, 10), diameter_mm=4)
    multiple = replace(project, spec=replace(project.spec, cutouts=(*project.spec.cutouts, second)))
    result = parse_conversation("walls 3mm and dont move that hole", multiple)
    assert result.status == "clarification" and result.candidate is None


def test_no_silent_partial_application(project):
    result = parse_conversation("walls 3mm and add a warp drive", project)
    assert result.status == "unsupported" and result.candidate is None
    assert result.unsupported


def test_apply_requires_review_and_exact_context(project):
    proposal = parse_conversation("walls 3mm", project)
    with pytest.raises(ValueError, match="confirmation"):
        apply_proposal(proposal, project)
    with pytest.raises(ValueError, match="Project changed"):
        apply_proposal(proposal, update_project(project, "wall_mm", 2.5, reason="independent edit"), confirmed=True)
    assert apply_proposal(proposal, project, confirmed=True).spec.wall_mm == 3
    forged = replace(proposal, candidate=replace(project, spec=replace(project.spec, wall_mm=4)))
    with pytest.raises(ValueError, match="does not match"):
        apply_proposal(forged, project, confirmed=True)


@pytest.mark.parametrize("mutation", ["offset", "extra", "bool_offset", "unknown_field", "bad_instruction"])
def test_invalid_provider_proposals_cannot_bypass_validation(project, mutation):
    source = "make walls three millimeters"
    raw = payload(source, "set wall thickness to 3 mm")
    if mutation == "offset":
        raw["actions"][0]["evidence"]["end"] -= 1
    elif mutation == "extra":
        raw["execute_python"] = "print('unsafe')"
    elif mutation == "bool_offset":
        raw["actions"][0]["evidence"]["start"] = False
    elif mutation == "unknown_field":
        raw["preserve"] = [{"field": "secret", "evidence": raw["actions"][0]["evidence"]}]
    else:
        raw["actions"][0]["instruction"] = "execute python print('unsafe')"
    if mutation == "bad_instruction":
        assert validate_edit_payload(source, project, raw).candidate is None
    else:
        with pytest.raises(ValueError):
            validate_edit_payload(source, project, raw)


def test_uncovered_requirements_block_provider_proposal(project):
    source = "walls 3mm and keep the hole"
    raw = payload(source[:9], "set wall thickness to 3 mm")
    result = validate_edit_payload(source, project, raw)
    assert result.status == "unsupported" and result.candidate is None


def test_provider_request_contains_context_history_and_strict_schema(project, monkeypatch):
    source = "nah use three millimeters for those walls"
    provider = ChatLanguageProvider(endpoint="https://example.test/v1/chat/completions", model="test-model")
    def complete(request):
        assert request["response_format"]["json_schema"]["strict"]
        context = json.loads(request["messages"][1]["content"])
        assert context["project"]["project_id"] == project.project_id
        assert context["recent_messages"] == ["we are editing the enclosure"]
        assert context["source"] == source
        return {"model": "test-model", "choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(payload(source, "set wall thickness to 3 mm"))}}]}
    monkeypatch.setattr(provider, "complete", complete)
    result = provider.interpret(source, project, recent_messages=["we are editing the enclosure"])
    assert result.status == "proposal" and result.candidate.spec.wall_mm == 3
    assert result.to_dict()["requires_review"]


@pytest.mark.parametrize("response", [
    {}, {"choices": []}, {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
    {"choices": [{"finish_reason": "stop", "message": {"refusal": "no", "content": None}}]},
    {"choices": [{"finish_reason": "stop", "message": {"content": "not JSON"}}]},
])
def test_provider_refusals_truncation_and_invalid_json_fail_closed(project, monkeypatch, response):
    provider = ChatLanguageProvider(endpoint="http://127.0.0.1:11434/v1/chat/completions", model="test")
    monkeypatch.setattr(provider, "complete", lambda request: response)
    with pytest.raises(LanguageProviderError):
        provider.interpret("walls 3mm", project)


@pytest.mark.parametrize("endpoint", ["file:///etc/passwd", "http://remote.test/v1", "https://user:pass@example.test/v1",
                                      "https://example.test/v1?key=secret"])
def test_provider_configuration_rejects_unsafe_transport(endpoint):
    with pytest.raises(ValueError):
        ChatLanguageProvider(endpoint=endpoint, model="test")


def test_cli_writes_only_new_proposal_and_never_modifies_project(project, tmp_path, capsys):
    original, output = tmp_path / "project.json", tmp_path / "proposal.json"
    write_project(original, project)
    before = original.read_bytes()
    args = build_parser().parse_args(["enclosure", "understand", str(original), "walls 3mm", "-o", str(output)])
    assert args.func(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "proposal"
    assert original.read_bytes() == before
    assert json.loads(output.read_text(encoding="utf-8"))["candidate"]["spec"]["wall_mm"] == 3
    with pytest.raises((ValueError, FileExistsError)):
        args.func(args)
    assert original.read_bytes() == before


def test_cli_review_and_apply_revalidates_saved_proposal(project, tmp_path, capsys):
    baseline, proposal, output = tmp_path / "base.json", tmp_path / "proposal.json", tmp_path / "reviewed.json"
    write_project(baseline, project)
    before = baseline.read_bytes()
    proposal.write_text(json.dumps(parse_conversation("walls 3mm", project).to_dict()), encoding="utf-8")
    parser = build_parser()
    argv = ["enclosure", "apply-proposal", str(baseline), str(proposal), "-o", str(output)]
    args = parser.parse_args(argv)
    with pytest.raises(ValueError, match="--confirm"):
        args.func(args)
    assert not output.exists()
    args = parser.parse_args([*argv, "--confirm"])
    assert args.func(args) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["spec"]["wall_mm"] == 3
    assert baseline.read_bytes() == before
    tampered = json.loads(proposal.read_text(encoding="utf-8"))
    tampered["candidate"]["spec"]["wall_mm"] = 4
    proposal.write_text(json.dumps(tampered), encoding="utf-8")
    args = parser.parse_args(["enclosure", "apply-proposal", str(baseline), str(proposal), "-o", str(tmp_path / "forged.json"), "--confirm"])
    with pytest.raises(ValueError, match="differs"):
        args.func(args)
    assert not (tmp_path / "forged.json").exists()


def test_outer_preservation_also_blocks_radius_changes(project):
    result = parse_conversation("corner radius 4mm and keep the outside same", project)
    assert result.status == "clarification" and result.candidate is None


def test_unit_conversion_preserves_numeric_precision(project):
    result = parse_conversation("walls 3.123456789 mm", project)
    assert result.candidate.spec.wall_mm == 3.123456789


def test_mixed_unit_dimensions_and_multi_clause_edits(project):
    result = parse_conversation("make that box 9cm x 65mm x 3.2cm and walls 3mm", project)
    assert result.status == "proposal"
    assert result.candidate.spec.outer_size_mm == (90, 65, 32)
    assert result.candidate.spec.wall_mm == 3


def test_transport_posts_schema_and_never_follows_redirects(monkeypatch):
    import core.language_provider as module
    state = {}
    class Response:
        status = 200
        def read(self, limit):
            state["limit"] = limit
            return b'{"choices": []}'
    class Connection:
        def __init__(self, host, port, timeout):
            state["host"] = host
            state["timeout"] = timeout
        def request(self, method, path, body, headers):
            state.update(method=method, path=path, body=json.loads(body), headers=headers)
        def getresponse(self):
            return Response()
        def close(self):
            state["closed"] = True
    monkeypatch.setattr(module.http.client, "HTTPSConnection", Connection)
    provider = ChatLanguageProvider(endpoint="https://example.test/v1/chat/completions", model="test", api_key="test-token")
    assert provider.complete({"model": "test"}) == {"choices": []}
    assert state["method"] == "POST" and state["path"] == "/v1/chat/completions"
    assert state["headers"]["Authorization"] == "Bearer test-token"
    assert state["closed"] and state["limit"] == module.MAX_RESPONSE_BYTES + 1
    Response.status = 302
    with pytest.raises(LanguageProviderError, match="HTTP 302"):
        provider.complete({"model": "test"})


@pytest.mark.parametrize("raw", [b'x' * 262145, b'{"a":1,"a":2}', b'{"a":NaN}', b'[]'])
def test_transport_rejects_unbounded_or_invalid_responses(monkeypatch, raw):
    import core.language_provider as module
    class Connection:
        status = 200
        def __init__(self, *args, **kwargs):
            pass
        def request(self, *args, **kwargs):
            pass
        def getresponse(self):
            return self
        def read(self, limit):
            return raw
        def close(self):
            pass
    monkeypatch.setattr(module.http.client, "HTTPSConnection", Connection)
    provider = ChatLanguageProvider(endpoint="https://example.test/v1/chat/completions", model="test")
    with pytest.raises(LanguageProviderError):
        provider.complete({"model": "test"})
