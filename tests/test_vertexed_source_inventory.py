import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs" / "vertexed_neurocad_source_inventory_v1.json"
BASE = ROOT / "docs" / "vertexed_neurocad_provenance_v1.json"
RESEARCH = ROOT / "docs" / "vertexed_neurocad_research_provenance_extension_v1.json"
PRODUCT_QA = ROOT / "docs" / "vertexed_neurocad_product_qa_provenance_extension_v1.json"
REVIEWER_GUIDE = ROOT / "docs" / "HISTORICAL_VERTEXED_PROVENANCE.md"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_ENTRY_COUNT = 48
EXPECTED_CANONICAL_DIGEST = "93a4856df5ca536100c7201bf0b6886b4747bbaac1d6937e98fbd862de08aadf"
EXPECTED_SNAPSHOT = "9efb041d3d56e0dc617f5808576beff696d08a69"
EXPECTED_ROOT = "portfolio/project2424/projects/T2424-0037"
EXPECTED_TREE = "f741417e9710c3044044465bfeabc7a3cf185ca0"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def all_surfaces(base, research, product_qa):
    return (
        base["surfaces"]
        + research["additional_surfaces"]
        + product_qa["additional_surfaces"]
    )


def test_frozen_project2424_inventory_has_exact_identity_and_no_omissions():
    inventory = load(INVENTORY)
    base = load(BASE)
    research = load(RESEARCH)
    product_qa = load(PRODUCT_QA)

    assert inventory["schema_version"] == 1
    assert inventory["historical_source_repository"] == "vertex-studyAI/vertexED.ai"
    assert inventory["source_snapshot"] == EXPECTED_SNAPSHOT
    assert inventory["source_root"] == EXPECTED_ROOT
    assert inventory["source_tree"] == EXPECTED_TREE
    assert "does not authorize experiments" in inventory["scope"]

    # The inventory must be bound to exactly the same frozen source snapshot as
    # every provenance manifest. A later source ref cannot silently substitute.
    assert base["source_snapshot"] == EXPECTED_SNAPSHOT
    assert research["source_snapshot"] == EXPECTED_SNAPSHOT
    assert product_qa["source_snapshot"] == EXPECTED_SNAPSHOT

    entries = inventory["entries"]
    assert len(entries) == EXPECTED_ENTRY_COUNT

    paths = [entry["relative_path"] for entry in entries]
    assert len(paths) == len(set(paths)), "inventory paths must be unique"
    assert all(path and not path.startswith("/") and ".." not in Path(path).parts for path in paths)
    assert all(HEX40.fullmatch(entry["source_blob"]) for entry in entries)

    # Bind the complete 48-blob inventory to a compact independent checksum so
    # deleting, adding, renaming, or changing any recorded blob identity fails.
    canonical = "".join(
        f"{entry['relative_path']}\t{entry['source_blob']}\n"
        for entry in sorted(entries, key=lambda item: item["relative_path"])
    )
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == EXPECTED_CANONICAL_DIGEST


def test_manifest_rows_inside_frozen_subtree_resolve_to_inventory():
    inventory = load(INVENTORY)
    base = load(BASE)
    research = load(RESEARCH)
    product_qa = load(PRODUCT_QA)
    surfaces = all_surfaces(base, research, product_qa)

    exact_paths = {
        f"{inventory['source_root']}/{entry['relative_path']}": entry["source_blob"]
        for entry in inventory["entries"]
    }
    directory_prefixes = {
        f"{inventory['source_root']}/src/",
        f"{inventory['source_root']}/web/",
    }

    relevant = [
        surface for surface in surfaces
        if surface["source_path"].startswith(f"{inventory['source_root']}/")
    ]
    assert relevant

    for surface in relevant:
        source_path = surface["source_path"]
        if source_path.endswith("/"):
            assert source_path in directory_prefixes, source_path
            assert any(path.startswith(source_path) for path in exact_paths), source_path
        else:
            assert source_path in exact_paths, source_path
            source_blob = surface.get("source_blob")
            if source_blob is not None:
                assert source_blob == exact_paths[source_path], source_path


def test_recovered_blob_rows_cannot_disagree_with_frozen_inventory():
    inventory = load(INVENTORY)
    research = load(RESEARCH)
    expected = {
        f"{inventory['source_root']}/{entry['relative_path']}": entry["source_blob"]
        for entry in inventory["entries"]
    }

    recovered = research.get("recovered_blob_identities", {})
    assert recovered
    for source_path, source_blob in recovered.items():
        if source_path.startswith(f"{inventory['source_root']}/"):
            assert source_path in expected, source_path
            assert source_blob == expected[source_path], source_path


def test_reviewer_guide_exposes_inventory_and_frozen_tree_identity():
    guide = REVIEWER_GUIDE.read_text(encoding="utf-8")
    assert INVENTORY.name in guide
    assert EXPECTED_ROOT in guide
    assert EXPECTED_TREE in guide
    assert "complete 48-blob inventory" in guide
