import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "vertexed_neurocad_provenance_v1.json"
RESEARCH_EXTENSION = ROOT / "docs" / "vertexed_neurocad_research_provenance_extension_v1.json"
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


def load_research_extension():
    return json.loads(RESEARCH_EXTENSION.read_text(encoding="utf-8"))


def assert_cross_link_exists(cross_link):
    if not cross_link.startswith(("https://", "http://")):
        assert (ROOT / cross_link).exists(), cross_link


def assert_historical_surface(surface, source_snapshot):
    assert surface["source_ref"] == source_snapshot
    assert surface["relation"] in ALLOWED_RELATIONS
    assert surface["canonical_destination"]
    assert surface["current_cross_link"]
    assert surface["note"].strip()

    source_blob = surface.get("source_blob")
    if source_blob is not None:
        assert HEX40.fullmatch(source_blob)

    source_tree = surface.get("source_tree")
    if source_tree is not None:
        assert HEX40.fullmatch(source_tree)

    destination = surface["canonical_destination"]
    if destination != "HISTORICAL_ONLY":
        assert (ROOT / destination).exists(), destination

    assert_cross_link_exists(surface["current_cross_link"])


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
        assert_historical_surface(surface, manifest["source_snapshot"])


def test_research_extension_is_bound_to_base_manifest_and_adds_unique_surfaces():
    manifest = load_manifest()
    extension = load_research_extension()

    assert extension["schema_version"] == 1
    assert extension["extends"] == MANIFEST.name
    assert extension["historical_source_repository"] == manifest["historical_source_repository"]
    assert extension["source_snapshot"] == manifest["source_snapshot"]
    assert extension["purpose"].strip()

    base_by_path = {surface["source_path"]: surface for surface in manifest["surfaces"]}
    recovered = extension["recovered_blob_identities"]
    assert recovered
    for source_path, source_blob in recovered.items():
        assert source_path in base_by_path, source_path
        assert HEX40.fullmatch(source_blob)

    additional = extension["additional_surfaces"]
    assert len(additional) >= 15
    additional_paths = [surface["source_path"] for surface in additional]
    assert len(additional_paths) == len(set(additional_paths)), "extension source paths must be unique"
    assert not set(additional_paths) & set(base_by_path), "extension must not duplicate base surface rows"

    for surface in additional:
        assert surface["category"] in REQUIRED_CATEGORIES
        assert_historical_surface(surface, manifest["source_snapshot"])

    assert len(base_by_path) + len(additional_paths) >= 35


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


def test_historical_diagnostic_and_s3_execution_surfaces_stay_non_authorizing():
    manifest = load_manifest()
    extension = load_research_extension()
    all_surfaces = manifest["surfaces"] + extension["additional_surfaces"]
    by_path = {surface["source_path"]: surface for surface in all_surfaces}

    protected_suffixes = (
        "benchmark/component_ablation_evaluate.mjs",
        ".github/workflows/neurocad-component-ablation.yml",
        "S3_SUCCESSOR_PROTOCOL_20260822.md",
        "benchmark/generate_s3_execution_authorization.mjs",
        "benchmark/s3_successor_manifest.json",
        "benchmark/s3_external_adapter_registry.json",
        "benchmark/validate_s3_external_adapter_registry.mjs",
    )
    for suffix in protected_suffixes:
        matches = [surface for path, surface in by_path.items() if path.endswith(suffix)]
        assert len(matches) == 1, suffix
        surface = matches[0]
        assert surface["canonical_destination"] == "HISTORICAL_ONLY"
        assert surface["relation"] == "INTENTIONALLY_NOT_MIGRATED"

    s3_surfaces = [
        surface
        for path, surface in by_path.items()
        if "S3_" in path or "/s3_" in path
    ]
    assert s3_surfaces
    assert all("authoriz" in surface["note"].lower() or "canonical s3" in surface["note"].lower() or "materialization" in surface["note"].lower() for surface in s3_surfaces)
