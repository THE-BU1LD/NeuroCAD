from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from research.vericodegen.prompt_freeze import (
    PromptBundleError,
    build_receipt,
    freeze_prompt_bundle,
    load_bundle,
    render_prompt,
    shared_block,
    validate_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = ROOT / "research/vericodegen/prompt_bundle_v1.json"
SCHEMA_PATH = ROOT / "research/vericodegen/structured_output.schema.json"


def test_repository_prompt_bundle_is_valid():
    bundle = load_bundle(BUNDLE_PATH)
    assert validate_bundle(bundle) == []
    assert bundle["scientific_evidence"] is False


def test_both_arms_share_one_identical_rule_block():
    bundle = load_bundle(BUNDLE_PATH)
    shared = shared_block(bundle)
    direct = render_prompt(bundle, "direct")
    structured = render_prompt(bundle, "structured")
    for rule in bundle["shared_rules"]:
        assert rule in shared
        assert rule in direct
        assert rule in structured


def test_treatment_difference_is_explicit_in_output_contract():
    bundle = load_bundle(BUNDLE_PATH)
    direct = render_prompt(bundle, "direct")
    structured = render_prompt(bundle, "structured")
    assert "Return complete OpenSCAD source code only." in direct
    assert "do not emit a structured JSON specification" in direct
    assert "Return exactly one JSON object" in structured
    assert "Do not emit OpenSCAD source" in structured
    assert "vericodegen-structured-v1" in structured


def test_receipt_hashes_exact_rendered_bytes_and_schema():
    bundle = load_bundle(BUNDLE_PATH)
    schema_bytes = SCHEMA_PATH.read_bytes()
    receipt = build_receipt(bundle, schema_bytes=schema_bytes)
    direct = render_prompt(bundle, "direct").encode("utf-8")
    structured = render_prompt(bundle, "structured").encode("utf-8")
    assert receipt["direct_sha256"] == hashlib.sha256(direct).hexdigest()
    assert receipt["structured_sha256"] == hashlib.sha256(structured).hexdigest()
    assert receipt["structured_schema_sha256"] == hashlib.sha256(schema_bytes).hexdigest()
    assert receipt["prompt_byte_delta"] == len(structured) - len(direct)
    assert receipt["frozen"] is True
    assert receipt["outcomes_observed"] is False


def test_freeze_writes_exact_templates_and_receipt(tmp_path: Path):
    receipt = freeze_prompt_bundle(
        BUNDLE_PATH,
        repository_root=ROOT,
        output_dir=tmp_path,
    )
    direct_path = tmp_path / "direct_system_v1.txt"
    structured_path = tmp_path / "structured_system_v1.txt"
    receipt_path = tmp_path / "prompt_receipt_v1.json"
    assert direct_path.is_file()
    assert structured_path.is_file()
    assert receipt_path.is_file()
    assert hashlib.sha256(direct_path.read_bytes()).hexdigest() == receipt["direct_sha256"]
    assert hashlib.sha256(structured_path.read_bytes()).hexdigest() == receipt["structured_sha256"]
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt


def test_bundle_rejects_missing_shared_rules():
    bundle = load_bundle(BUNDLE_PATH)
    bundle["shared_rules"] = []
    errors = validate_bundle(bundle)
    assert any("at least three" in error for error in errors)


def test_bundle_rejects_unfrozen_structured_version():
    bundle = load_bundle(BUNDLE_PATH)
    bundle["structured"]["spec_version"] = "future-unfrozen-v2"
    errors = validate_bundle(bundle)
    assert any("structured.spec_version" in error for error in errors)


def test_bundle_rejects_unknown_fields():
    bundle = load_bundle(BUNDLE_PATH)
    bundle["direct"]["hidden_advantage"] = "extra tool access"
    errors = validate_bundle(bundle)
    assert any("direct has unsupported keys" in error for error in errors)


def test_unknown_arm_fails_closed():
    bundle = load_bundle(BUNDLE_PATH)
    with pytest.raises(PromptBundleError, match="arm must be"):
        render_prompt(bundle, "hybrid")
