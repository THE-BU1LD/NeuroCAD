import hashlib
import json
from pathlib import Path

import pytest

from research.s3.external_adapters import CATEGORY, SOURCES, STATUS, adapt_rows, main


def test_cadtestbench_adapter_binds_prompt_only_provenance():
    rows = [{"sample_id": "42", "prompt": "Create a plate with four mounting holes."}]
    first = adapt_rows("cadtestbench", rows)
    second = adapt_rows("cadtestbench", rows)

    assert first == second
    record = first[0]
    assert record["candidate_id"] == "EXT-CADTESTBENCH-42"
    assert record["category"] == CATEGORY == "external_unmapped"
    assert record["status"] == STATUS == "CANDIDATE_NOT_EVALUATED"
    assert record["source_revision"] == "e29283cc61db7329039d95b429766a50bfd37f89"
    assert record["source_license"] == "MIT"
    assert record["source_dataset_revision"] == "2b9a4a972d142d2bc634d072e9d4485f171ced06"
    assert record["source_dataset_license"] == "MIT"
    assert len(record["source_dataset_receipt_sha256"]) == 64
    assert len(record["source_row_sha256"]) == 64


def test_cadtestbench_public_prompt_artifacts_are_content_pinned():
    spec = SOURCES["cadtestbench"]
    assert [(a.path, a.sha256, a.size_bytes) for a in spec.dataset_artifacts] == [
        (
            "samples/abstract.parquet",
            "67a5779bc5114ce4db6bc9be89bf22c25e707bc83e7431214cddfac23f980536",
            17545,
        ),
        (
            "samples/detailed.parquet",
            "76b2d20def7946e1e3216b72a8acb83825c489c373b23ac514b77885ae275b37",
            33726,
        ),
    ]


def test_cadgenbench_adapter_accepts_edit_request_without_assigning_internal_taxonomy():
    [record] = adapt_rows(
        "cadgenbench",
        [{"id": "edit-007", "edit_request": "Increase the bore diameter to 12 mm."}],
    )
    assert record["candidate_id"] == "EXT-CADGENBENCH-edit-007"
    assert record["category"] == "external_unmapped"
    assert record["source_revision"] == "33304cf771fc5639144b1df9611e347251052cf8"
    assert record["source_license"] == "Apache-2.0"
    assert record["source_dataset_repository"] == "HuggingAI4Engineering/cadgenbench-data"
    assert record["source_dataset_revision"] == "569ea565cef25ee690e39bf89941f940027633d6"
    assert record["source_dataset_license"] == "ODC-By-1.0"


@pytest.mark.parametrize(
    "field",
    ["score", "result", "output", "ground_truth", "prediction", "metrics", "cadtest_results"],
)
def test_adapters_fail_closed_on_outcome_bearing_fields(field):
    row = {"sample_id": "1", "prompt": "Create a cube.", field: "must not be inspected"}
    with pytest.raises(ValueError, match="outcome-bearing"):
        adapt_rows("cadtestbench", [row])


def test_duplicate_source_ids_are_rejected():
    with pytest.raises(ValueError, match="duplicate source id"):
        adapt_rows(
            "cadtestbench",
            [
                {"sample_id": "same", "prompt": "Create a cube."},
                {"sample_id": "same", "prompt": "Create a sphere."},
            ],
        )


def test_exactly_one_prompt_and_id_field_are_required():
    with pytest.raises(ValueError, match="exactly one prompt"):
        adapt_rows("cadtestbench", [{"sample_id": "1", "prompt": "A", "detailed_prompt": "B"}])
    with pytest.raises(ValueError, match="exactly one source id"):
        adapt_rows("cadtestbench", [{"sample_id": "1", "id": "1", "prompt": "A"}])


def test_invalid_source_export_digest_is_rejected():
    with pytest.raises(ValueError, match="source_export_sha256"):
        adapt_rows("cadtestbench", [{"sample_id": "1", "prompt": "A"}], source_export_sha256="not-a-digest")


def test_cli_refuses_overwrite_and_binds_exact_input_bytes(tmp_path: Path):
    source = tmp_path / "prompt_only.jsonl"
    output = tmp_path / "adapted.jsonl"
    source_bytes = (json.dumps({"sample_id": "9", "prompt": "Create a 20 mm cube."}) + "\n").encode()
    source.write_bytes(source_bytes)
    expected_export_sha256 = hashlib.sha256(source_bytes).hexdigest()

    assert main(["--source", "cadtestbench", "--input", str(source), "--output", str(output)]) == 0
    parsed = [json.loads(line) for line in output.read_text().splitlines()]
    assert parsed[0]["status"] == "CANDIDATE_NOT_EVALUATED"
    assert parsed[0]["source_export_sha256"] == expected_export_sha256
    assert parsed[0]["source_dataset_revision"] == "2b9a4a972d142d2bc634d072e9d4485f171ced06"

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        main(["--source", "cadtestbench", "--input", str(source), "--output", str(output)])


def test_source_specs_are_pinned_and_licenses_are_explicit():
    assert SOURCES["cadtestbench"].revision == "e29283cc61db7329039d95b429766a50bfd37f89"
    assert SOURCES["cadtestbench"].license_spdx == "MIT"
    assert SOURCES["cadtestbench"].dataset_revision == "2b9a4a972d142d2bc634d072e9d4485f171ced06"
    assert SOURCES["cadgenbench"].revision == "33304cf771fc5639144b1df9611e347251052cf8"
    assert SOURCES["cadgenbench"].license_spdx == "Apache-2.0"
    assert SOURCES["cadgenbench"].dataset_revision == "569ea565cef25ee690e39bf89941f940027633d6"
    assert SOURCES["cadgenbench"].dataset_license_spdx == "ODC-By-1.0"
