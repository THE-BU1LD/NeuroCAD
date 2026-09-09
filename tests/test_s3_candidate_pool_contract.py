import csv
from collections import Counter
from pathlib import Path

POOL = Path("research/s3/benchmark_candidate_pool_v0.csv")
EXPECTED_CATEGORIES = {
    "primitive_solids",
    "dimensional_edits",
    "bores_cutouts",
    "patterns",
    "fillets_chamfers",
    "assemblies_compositions",
    "ambiguous_constraints",
    "invalid_underspecified",
    "multi_step_edits",
    "constraint_interactions",
    "reference_frame_language",
}
EXPECTED_FIELDS = ["candidate_id", "category", "prompt", "provenance", "status"]
EXPECTED_STATUS = "CANDIDATE_NOT_EVALUATED"


def load_rows():
    with POOL.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def test_candidate_pool_schema_is_pre_outcome_only():
    fields, _ = load_rows()
    assert fields == EXPECTED_FIELDS


def test_candidate_pool_has_exactly_110_rows():
    _, rows = load_rows()
    assert len(rows) == 110


def test_candidate_ids_are_unique_and_contiguous():
    _, rows = load_rows()
    ids = [row["candidate_id"] for row in rows]
    assert len(ids) == len(set(ids))
    assert ids == [f"S3C-{index:03d}" for index in range(1, 111)]


def test_taxonomy_is_exactly_the_declared_11_categories():
    _, rows = load_rows()
    assert {row["category"] for row in rows} == EXPECTED_CATEGORIES


def test_taxonomy_is_balanced_at_10_candidates_per_category():
    _, rows = load_rows()
    counts = Counter(row["category"] for row in rows)
    assert counts == Counter({category: 10 for category in EXPECTED_CATEGORIES})


def test_every_candidate_remains_explicitly_not_evaluated():
    _, rows = load_rows()
    assert {row["status"] for row in rows} == {EXPECTED_STATUS}


def test_provenance_is_present_and_pre_outcome():
    _, rows = load_rows()
    for row in rows:
        provenance = row["provenance"].strip().lower()
        assert provenance
        assert "not derived from evaluation outcomes" in provenance


def test_prompts_are_nonempty_and_have_no_exact_duplicates():
    _, rows = load_rows()
    prompts = [" ".join(row["prompt"].split()).casefold() for row in rows]
    assert all(prompts)
    assert len(prompts) == len(set(prompts))
