import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs" / "vertexed_neurocad_source_inventory_v1.json"
BASE = ROOT / "docs" / "vertexed_neurocad_provenance_v1.json"
RESEARCH = ROOT / "docs" / "vertexed_neurocad_research_provenance_extension_v1.json"
PRODUCT_QA = ROOT / "docs" / "vertexed_neurocad_product_qa_provenance_extension_v1.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_ENTRY_COUNT = 48
EXPECTED_CANONICAL_DIGEST = "93a4856df5ca536100c7201bf0b6886b4747bbaac1d6937e98fbd862de08aadf"
EXPECTED_SNAPSHOT = "9efb041d3d56e0dc617f5808576beff696d08a69"
EXPECTED_ROOT = "portfolio/project2424/projects/T2424-0037"


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


def test_every_inventoried_blob_is_covered_by_the_provenance_surface_map():
    inventory = load(INVENTORY)
    base = load(BASE)
    research = load(RESEARCH)
    product_qa = load(PRODUCT_QA)
    surfaces = all_surfaces(base, research, product_qa)
    surface_paths = {surface["source_path"] for surface in surfaces}

    def covered(full_path):
        if full_path in surface_paths:
            return True
        return any(
            source_path.endswith("/") and full_path.startswith(source_path)
            for source_path in surface_paths
        )

    missing = []
    for entry in inventory["entries"]:
        full_path = f"{inventory['source_root']}/{entry['relative_path']}"
        if not covered(full_path):
            missing.append(full_path)

    assert not missing, f"historical blobs omitted from provenance surface map: {missing}"


def test_exact_blob_rows_cannot_disagree_with_frozen_inventory():
    inventory = load(INVENTORY)
    base = load(BASE)
    research = load(RESEARCH)
    product_qa = load(PRODUCT_QA)
    surfaces = all_surfaces(base, research, product_qa)

    expected = {
        f"{inventory['source_root']}/{entry['relative_path']}": entry["source_blob"]
        for entry in inventory["entries"]
    }

    for surface in surfaces:
        source_path = surface["source_path"]
        source_blob = surface.get("source_blob")
        if source_path in expected and source_blob is not None:
            assert source_blob == expected[source_path], source_path

    # The research extension also carries recovered exact blob identities for
    # rows that originally had only directory/tree provenance. Those identities
    # are equally required to agree with the frozen inventory.
    for source_path, source_blob in research.get("recovered_blob_identities", {}).items():
        if source_path in expected:
            assert source_blob == expected[source_path], source_path
