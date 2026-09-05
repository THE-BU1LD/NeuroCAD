import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "vertexed_neurocad_provenance_v1.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_CATEGORIES = {
    "runtime_product",
    "e2e_browser",
    "scripts_workflows",
    "product_tests",
    "public_alpha_release",
    "research_protocol_result",
    "claim_ledger",
    "project2424_evidence_alias",
    "external_pilot",
}
ALLOWED_RELATIONS = {
    "IDENTICAL",
    "MIGRATED_NON_SCIENTIFIC",
    "INTENTIONALLY_NOT_MIGRATED",
}


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_historical_provenance_manifest_is_fail_closed_and_complete_by_category():
    manifest = load_manifest()

    assert manifest["schema_version"] == 1
    assert manifest["historical_source_repository"] == "vertex-studyAI/vertexED.ai"
    assert manifest["canonical_repository"] == "THE-BU1LD/NeuroCAD"
    assert manifest["generated_for_issue"] == 44
    assert HEX40.fullmatch(manifest["source_snapshot"])

    integrity = manifest["integrity_boundary"]
    assert integrity["migration_is_not_scientific_validation"] is True
    assert integrity["typed_parser_causal_claim"] == "FALSIFIED_VALIDATION_DOMINANT"
    assert integrity["stage2_outcome_access"] == "UNCHANGED"
    assert integrity["s3_outcome_access"] == "UNCHANGED"
    assert integrity["frozen_results_must_not_be_rewritten"] is True

    surfaces = manifest["surfaces"]
    assert len(surfaces) >= 20
    assert {surface["category"] for surface in surfaces} == REQUIRED_CATEGORIES

    source_paths = [surface["source_path"] for surface in surfaces]
    assert len(source_paths) == len(set(source_paths)), "historical source paths must be unique"

    for surface in surfaces:
        assert surface["source_ref"] == manifest["source_snapshot"]
        assert surface["relation"] in ALLOWED_RELATIONS
        assert surface["canonical_destination"]
        assert surface["current_cross_link"]
        assert surface["note"].strip()

        source_blob = surface.get("source_blob")
        if source_blob is not None:
            assert HEX40.fullmatch(source_blob)

        destination = surface["canonical_destination"]
        if destination != "HISTORICAL_ONLY":
            assert (ROOT / destination).exists(), destination

        cross_link = surface["current_cross_link"]
        if not cross_link.startswith(("https://", "http://")):
            assert (ROOT / cross_link).exists(), cross_link


def test_frozen_historical_claims_are_not_mislabelled_as_migrated_results():
    manifest = load_manifest()
    frozen_markers = (
        "NEUROCAD_COMPONENT_ABLATION_PROTOCOL_20260814.md",
        "NEUROCAD_COMPONENT_ABLATION_RESULT_20260814.md",
        "NEUROCAD_INDEPENDENT_ARTIFACT_AUDIT_20260814.md",
    )

    by_path = {surface["source_path"]: surface for surface in manifest["surfaces"]}
    for marker in frozen_markers:
        matches = [surface for path, surface in by_path.items() if path.endswith(marker)]
        assert len(matches) == 1
        surface = matches[0]
        assert surface["canonical_destination"] == "HISTORICAL_ONLY"
        assert surface["relation"] == "INTENTIONALLY_NOT_MIGRATED"
        assert surface["current_cross_link"] == "docs/RESEARCH_STATUS.md"
