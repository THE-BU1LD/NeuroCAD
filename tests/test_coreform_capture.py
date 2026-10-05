from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.validate_coreform_capture import validate_capture


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_capture(tmp_path: Path) -> Path:
    baseline = tmp_path / "baseline.step"
    baseline.write_text("synthetic baseline", encoding="utf-8")
    evidence = tmp_path / "geometry.txt"
    evidence.write_text("synthetic validation output", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "case_id": "synthetic-case",
        "purpose": "SYNTHETIC_SOFTWARE_TEST",
        "cubit_version": "not-run",
        "input_format": "STEP",
        "units": "mm",
        "source_reference": "synthetic fixture",
        "rights_status": "synthetic local fixture",
        "import_settings": {},
        "target_mesh_size": 3.0,
        "interface_assumptions": "none",
        "repair_description": "no repair",
        "mesh_settings": "not run",
        "as_imported_model": {"path": "baseline.step", "sha256": digest(baseline)},
        "repaired_model": None,
        "stages": {
            "geometry_before": {
                "status": "REPORTED_PASS",
                "command": "synthetic-check",
                "interpretation": "fixture only",
                "evidence": {"path": "geometry.txt", "sha256": digest(evidence)},
            },
            "geometry_after": {"status": "NOT_RUN", "command": None, "evidence": None},
            "tet_meshing": {"status": "NOT_RUN", "command": None, "evidence": None},
        },
    }
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_valid_capture_passes_integrity(tmp_path: Path) -> None:
    result = validate_capture(make_capture(tmp_path))
    assert result["integrity_passed"] is True
    assert result["stages"]["geometry_before"]["status"] == "REPORTED_PASS"


def test_hash_mismatch_rejected(tmp_path: Path) -> None:
    path = make_capture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["as_imported_model"]["sha256"] = "0" * 64
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="sha256 mismatch"):
        validate_capture(path)


def test_not_run_cannot_claim_evidence(tmp_path: Path) -> None:
    path = make_capture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["stages"]["tet_meshing"]["evidence"] = data["stages"]["geometry_before"]["evidence"]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="NOT_RUN must not carry evidence"):
        validate_capture(path)


def test_geometry_after_requires_repaired_model(tmp_path: Path) -> None:
    path = make_capture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["stages"]["geometry_after"] = dict(data["stages"]["geometry_before"])
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="without repaired_model"):
        validate_capture(path)


def test_repair_cannot_reuse_baseline_identity(tmp_path: Path) -> None:
    path = make_capture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["repaired_model"] = dict(data["as_imported_model"])
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="must be distinct"):
        validate_capture(path)


def test_tet_meshing_requires_model_basis(tmp_path: Path) -> None:
    path = make_capture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["stages"]["tet_meshing"] = dict(data["stages"]["geometry_before"])
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="model_basis"):
        validate_capture(path)


def test_path_escape_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.step"
    outside.write_text("outside", encoding="utf-8")
    path = make_capture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["as_imported_model"] = {"path": "../outside.step", "sha256": digest(outside)}
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="escapes capture directory"):
        validate_capture(path)


@pytest.mark.parametrize("version", [True, 1.0, False, 0, "1", None])
def test_schema_version_requires_exact_integer(tmp_path: Path, version: object) -> None:
    path = make_capture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["schema_version"] = version
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version must be integer 1"):
        validate_capture(path)


@pytest.mark.parametrize(
    "command", [" ", "\t\n", [None], [42], [True], [""], ["  "], [[]], ["validate", None]]
)
def test_executed_stage_requires_substantive_command(
    tmp_path: Path, command: object
) -> None:
    path = make_capture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["stages"]["geometry_before"]["command"] = command
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="command/procedure"):
        validate_capture(path)


@pytest.mark.parametrize(
    "original,replacement",
    [
        ('"schema_version": 1', '"schema_version": 2, "schema_version": 1'),
        ('"import_settings": {}', '"import_settings": {"units": "m", "units": "mm"}'),
        ('"status": "REPORTED_PASS"', '"status": "REPORTED_FAIL", "status": "REPORTED_PASS"'),
    ],
)
def test_duplicate_json_keys_rejected_at_every_level(
    tmp_path: Path, original: str, replacement: str
) -> None:
    path = make_capture(tmp_path)
    source = path.read_text(encoding="utf-8")
    assert source.count(original) == 1
    path.write_text(source.replace(original, replacement), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        validate_capture(path)


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e999", "-1e999"])
@pytest.mark.parametrize("field", ["import_settings", "mesh_settings"])
def test_nonfinite_numbers_in_settings_are_rejected(
    tmp_path: Path, token: str, field: str
) -> None:
    path = make_capture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data[field] = {"nested": ["__NUMBER__"]}
    source = json.dumps(data).replace('"__NUMBER__"', token)
    path.write_text(source, encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite JSON number"):
        validate_capture(path)


@pytest.mark.parametrize("status", ["REPORTED_PASS", "REPORTED_FAIL", "INCONCLUSIVE"])
@pytest.mark.parametrize("command", ["validate volume all verbose", ["validate", "volume", "all"]])
def test_valid_commands_preserve_all_reported_outcomes(
    tmp_path: Path, status: str, command: object
) -> None:
    path = make_capture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["stages"]["geometry_before"].update(status=status, command=command)
    path.write_text(json.dumps(data), encoding="utf-8")
    result = validate_capture(path)
    assert result["stages"]["geometry_before"]["status"] == status
    assert result["stages"]["geometry_before"]["command"] == command
    assert "does not establish geometry validity" in result["claim_boundary"]


def test_finite_nested_settings_and_unicode_remain_valid(tmp_path: Path) -> None:
    path = make_capture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["case_id"] = "synthetic-Δ"
    data["import_settings"] = {"tolerance": 1e-6, "nested": [True, None, 3.5]}
    data["mesh_settings"] = {"size": 3.0}
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert validate_capture(path)["case_id"] == "synthetic-Δ"


def test_all_not_run_stages_remain_valid(tmp_path: Path) -> None:
    path = make_capture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    for name in data["stages"]:
        data["stages"][name] = {"status": "NOT_RUN", "command": None, "evidence": None}
    path.write_text(json.dumps(data), encoding="utf-8")
    result = validate_capture(path)
    assert all(stage == {"status": "NOT_RUN"} for stage in result["stages"].values())
