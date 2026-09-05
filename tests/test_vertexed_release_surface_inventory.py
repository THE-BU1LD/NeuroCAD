import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs" / "vertexed_neurocad_release_surface_inventory_v1.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_SNAPSHOT = "9efb041d3d56e0dc617f5808576beff696d08a69"
EXPECTED_ROOT_TREE = "c5aeb156a9c09f0408dfa3dd20bd770076b5ee76"
EXPECTED_CANONICAL_SHA256 = "e7e297c5346b67f75c39d98e3a625c79f1e8021ecbc5fdb873e7d8ebfd58fc34"
EXPECTED_ENTRIES = {
    "scripts/publish-neurocad-alpha.mjs": "c20b2281810537cf532edad62582e965abaa8fd0",
    "scripts/neurocad-alpha-openscad-qa.mjs": "bc8d0e46c70a954a5cea2c61c41af9c3c7f3f4de",
    "tests/neurocadProductQa.test.mjs": "30dd2cdb0dc157ae9c05270ea6a4233212c0cec9",
    "tests/neurocadPublicRoute.test.mjs": "1cf180a181864a6cc230fada099f45a2819e2cbb",
    "tests/neurocadCdnWorkflowGuard.test.mjs": "8bcdf171055291b063219219a339bc1a5fba7b12",
    "e2e/neurocad-alpha.spec.ts": "1dc0b945024657bea790edb2ecd4b8b571cd8c42",
}


def load_inventory():
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def canonical_sha256(value):
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_release_surface_inventory_is_exact_and_hash_bound():
    inventory = load_inventory()

    assert inventory["schema_version"] == 1
    assert inventory["historical_source_repository"] == "vertex-studyAI/vertexED.ai"
    assert inventory["source_snapshot"] == EXPECTED_SNAPSHOT
    assert inventory["source_root_tree"] == EXPECTED_ROOT_TREE
    assert inventory["entry_count"] == len(EXPECTED_ENTRIES)
    assert canonical_sha256(inventory) == EXPECTED_CANONICAL_SHA256

    entries = inventory["entries"]
    assert len(entries) == len(EXPECTED_ENTRIES)
    assert len({entry["path"] for entry in entries}) == len(entries)
    assert {entry["path"]: entry["blob_sha"] for entry in entries} == EXPECTED_ENTRIES

    for entry in entries:
        assert HEX40.fullmatch(entry["blob_sha"])
        assert entry["role"].strip()
        assert not entry["path"].startswith("portfolio/project2424/projects/T2424-0037/")


def test_release_surface_inventory_stays_historical_and_non_authorizing():
    inventory = load_inventory()
    boundary = inventory["integrity_boundary"]

    assert boundary == {
        "inventory_is_provenance_only": True,
        "inventory_is_not_scientific_validation": True,
        "inventory_does_not_authorize_execution": True,
        "historical_product_qa_is_not_successor_evidence": True,
    }
    assert "outside portfolio/project2424/projects/T2424-0037" in inventory["scope"]
