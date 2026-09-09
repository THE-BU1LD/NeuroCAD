import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BASE = DOCS / "vertexed_neurocad_provenance_v1.json"
RESEARCH = DOCS / "vertexed_neurocad_research_provenance_extension_v1.json"
OOD = DOCS / "vertexed_neurocad_ood_provenance_extension_v1.json"
INVENTORY = DOCS / "vertexed_neurocad_workflow_inventory_v1.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SNAPSHOT = "9efb041d3d56e0dc617f5808576beff696d08a69"
ROOT_TREE = "c5aeb156a9c09f0408dfa3dd20bd770076b5ee76"
EXPECTED_WORKFLOWS = {
    ".github/workflows/neurocad-alpha-browser.yml": "c2387bb5d5dcc0cd25f2408591feb6b7063b6c0a",
    ".github/workflows/neurocad-alpha-openscad.yml": "9aad9b48cb4332c560b6706299c199ba799a8722",
    ".github/workflows/neurocad-alpha-public-cdn.yml": "b804066240b759e0670226c343f09b65f7bdb0e0",
    ".github/workflows/neurocad-component-ablation.yml": "64ebf3457a7dd8dd661e75e61fd5a50ee637f1f6",
    ".github/workflows/neurocad-ood-benchmark.yml": "b88a666c0b229c3d0f84a2a839e952728260d44e",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_frozen_workflow_inventory_is_exact_and_fail_closed():
    inventory = load(INVENTORY)

    assert inventory["schema_version"] == 1
    assert inventory["historical_source_repository"] == "vertex-studyAI/vertexED.ai"
    assert inventory["source_snapshot"] == SNAPSHOT
    assert inventory["source_root_tree"] == ROOT_TREE
    assert inventory["entry_count"] == 5
    assert inventory["scope"] == (
        ".github/workflows entries whose basename contains neurocad at the frozen source snapshot"
    )

    boundary = inventory["integrity_boundary"]
    assert boundary == {
        "inventory_is_provenance_only": True,
        "inventory_is_not_scientific_validation": True,
        "inventory_does_not_authorize_execution": True,
        "historical_outcomes_must_not_be_reopened": True,
    }

    entries = inventory["entries"]
    assert len(entries) == inventory["entry_count"]
    paths = [entry["path"] for entry in entries]
    assert len(paths) == len(set(paths))
    assert set(paths) == set(EXPECTED_WORKFLOWS)

    for entry in entries:
        path = entry["path"]
        assert path.startswith(".github/workflows/")
        assert "neurocad" in Path(path).name.lower()
        assert HEX40.fullmatch(entry["blob_sha"])
        assert entry["blob_sha"] == EXPECTED_WORKFLOWS[path]
        assert entry["provenance_owner"] in {
            BASE.name,
            RESEARCH.name,
            OOD.name,
        }


def test_every_frozen_neurocad_workflow_has_a_manifest_owner():
    inventory = load(INVENTORY)
    manifests = {
        BASE.name: load(BASE)["surfaces"],
        RESEARCH.name: load(RESEARCH)["additional_surfaces"],
        OOD.name: load(OOD)["additional_surfaces"],
    }

    mapped = set()
    for entry in inventory["entries"]:
        owner = entry["provenance_owner"]
        rows = [row for row in manifests[owner] if row["source_path"] == entry["path"]]
        assert len(rows) == 1, (owner, entry["path"])
        row = rows[0]
        assert row["source_ref"] == SNAPSHOT
        assert row["canonical_destination"] == "HISTORICAL_ONLY"
        assert row["relation"] == "INTENTIONALLY_NOT_MIGRATED"
        if "source_blob" in row:
            assert row["source_blob"] == entry["blob_sha"]
        mapped.add(entry["path"])

    assert mapped == set(EXPECTED_WORKFLOWS)


def test_ood_extension_recovers_only_the_missing_workflow_and_contract_test():
    extension = load(OOD)

    assert extension["schema_version"] == 1
    assert extension["extends"] == RESEARCH.name
    assert extension["historical_source_repository"] == "vertex-studyAI/vertexED.ai"
    assert extension["source_snapshot"] == SNAPSHOT
    assert "without reopening" in extension["purpose"].lower()
    assert extension["integrity_boundary"] == {
        "historical_only": True,
        "scientific_status_unchanged": True,
        "successor_authorization_unchanged": True,
        "outcome_access_unchanged": True,
    }

    rows = extension["additional_surfaces"]
    assert len(rows) == 2
    by_path = {row["source_path"]: row for row in rows}
    assert set(by_path) == {
        ".github/workflows/neurocad-ood-benchmark.yml",
        "tests/nlpToCadOodBenchmark.test.mjs",
    }

    expected_blobs = {
        ".github/workflows/neurocad-ood-benchmark.yml": EXPECTED_WORKFLOWS[
            ".github/workflows/neurocad-ood-benchmark.yml"
        ],
        "tests/nlpToCadOodBenchmark.test.mjs": "00002a21ff7f8c29a8a3d924e84fd1f4d385ca7a",
    }
    for path, row in by_path.items():
        assert row["source_ref"] == SNAPSHOT
        assert row["source_blob"] == expected_blobs[path]
        assert HEX40.fullmatch(row["source_blob"])
        assert row["canonical_destination"] == "HISTORICAL_ONLY"
        assert row["relation"] == "INTENTIONALLY_NOT_MIGRATED"
        assert row["current_cross_link"] == "docs/RESEARCH_STATUS.md"
        note = row["note"].lower()
        assert "historical" in note
        assert any(token in note for token in ("successor", "held-out", "outcome"))


def test_ood_extension_does_not_duplicate_earlier_manifest_paths():
    base_paths = {row["source_path"] for row in load(BASE)["surfaces"]}
    research_paths = {row["source_path"] for row in load(RESEARCH)["additional_surfaces"]}
    ood_paths = {row["source_path"] for row in load(OOD)["additional_surfaces"]}

    assert not ood_paths & base_paths
    assert not ood_paths & research_paths
