"""Adversarial ledger development cases; no benchmark or physical evidence."""
import hashlib
import json

import pytest

import core.evaluation_ledger as ledger

IDENTITIES = {"source_commit": "1" * 40, "dataset_revision": "2" * 40,
              "dataset_manifest_sha256": "3" * 64, "protocol_sha256": "4" * 64}
METRICS = {"passed": True, "requirements_passed": 2, "requirements_total": 2}


def run(path, **kwargs):
    return ledger.run_scheduled_evaluation(
        kwargs.pop("ids", ["one", "two"]), path,
        identities=kwargs.pop("identities", dict(IDENTITIES)),
        load=kwargs.pop("load", lambda item: item),
        execute=kwargs.pop("execute", lambda item: dict(METRICS)), **kwargs)


def audit(path, **kwargs):
    return ledger.audit_scheduled_evaluation(path, **kwargs)


class AdapterError(Exception):
    pass


@pytest.mark.parametrize("stage", ["load", "execute"])
@pytest.mark.parametrize("error", [AssertionError, AdapterError])
def test_ordinary_adapter_exceptions_retain_all_ids(tmp_path, stage, error):
    calls = []
    def broken(item):
        calls.append(item)
        if item == "one":
            raise error("do not leak private sample contents")
        return item if stage == "load" else dict(METRICS)
    result = run(tmp_path / "run", **{stage: broken})
    assert calls == ["one", "two"]
    assert result["correct_completion_denominator"] == 2
    assert result["correct_completion_numerator"] == 1
    assert result["outcomes"][0]["error_type"] == error.__name__
    assert result["outcomes"][0]["status"] == stage.replace("execute", "execution") + "_error"
    assert not result["valid_for_inference"]
    assert "private sample" not in (tmp_path / "run" / "summary.json").read_text(encoding="utf-8")


@pytest.mark.parametrize("key,value", [
    ("dataset_manifest_sha256", "3" * 40), ("protocol_sha256", "4" * 40),
    ("source_commit", "g" * 40), ("dataset_revision", "2" * 39),
    ("source_commit", True),
])
def test_identity_type_and_algorithm_are_checked_before_writes(tmp_path, key, value):
    calls = []
    with pytest.raises((TypeError, ValueError)):
        run(tmp_path / "run", identities={**IDENTITIES, key: value}, load=calls.append)
    assert not calls
    assert not (tmp_path / "run").exists()


def test_schedule_consumption_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "MAX_SAMPLES", 3, raising=False)
    consumed = []
    def ids():
        for i in range(4):
            consumed.append(i)
            yield f"id{i}"
        raise AssertionError("schedule read beyond admission limit")
    with pytest.raises(ValueError):
        run(tmp_path / "run", ids=ids())
    assert consumed == list(range(4))
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize("artifact,mode", [
    ("manifest.json", "change"), ("one.json", "change"), ("one.json", "delete"),
])
def test_in_run_evidence_mutation_never_reports_valid(tmp_path, artifact, mode):
    path = tmp_path / "run"
    def load(item):
        if item == "two":
            target = path / artifact
            if mode == "delete":
                target.unlink()
            else:
                target.write_text('{"substituted":true}\n')
        return item
    result = run(path, load=load)
    assert not result["valid_for_inference"]
    assert result["status"] == "INTEGRITY_ERROR"
    assert result["correct_completion_denominator"] == 2
    assert result["integrity_issues"]


@pytest.mark.parametrize("error", [KeyboardInterrupt, SystemExit, MemoryError])
def test_cancellation_and_resource_failure_leave_no_completion_marker(tmp_path, error):
    def execute(item):
        raise error()
    path = tmp_path / "run"
    with pytest.raises(error):
        run(path, execute=execute)
    assert (path / "manifest.json").exists()
    assert not (path / "summary.json").exists()


def test_overlarge_counts_are_retained_as_execution_errors(tmp_path):
    result = run(tmp_path / "run", execute=lambda item: {
        "passed": True, "requirements_passed": 2**64, "requirements_total": 2**64})
    assert not result["valid_for_inference"]
    assert all(row["status"] == "execution_error" for row in result["outcomes"])


def test_valid_offline_audit_recomputes_endpoints(tmp_path):
    path = tmp_path / "run"
    result = run(path)
    check = audit(path, expected_manifest_sha256=result["manifest_sha256"])
    assert check["integrity_verified"] is True
    assert check["valid_for_inference"] is True
    assert check["recomputed"]["correct_completion_numerator"] == 2
    assert check["recomputed"]["correct_completion_denominator"] == 2


@pytest.mark.parametrize("mutation", ["numerator", "bool_denominator", "drop_row", "duplicate_id",
    "row_metrics", "delete_row", "duplicate_json_key", "manifest", "unavailable_claim"])
def test_offline_audit_rejects_modified_receipts(tmp_path, mutation):
    path = tmp_path / "run"
    run(path)
    summary_path = path / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if mutation == "numerator":
        summary["correct_completion_numerator"] = 99
    elif mutation == "bool_denominator":
        summary["correct_completion_denominator"] = True
    elif mutation == "drop_row":
        summary["outcomes"].pop()
    elif mutation == "duplicate_id":
        summary["outcomes"][1]["id"] = "one"
    elif mutation == "unavailable_claim":
        summary["requirement_unavailable_samples"] = 1
    elif mutation == "row_metrics":
        row = json.loads((path / "one.json").read_text(encoding="utf-8"))
        row["metrics"]["passed"] = False
        (path / "one.json").write_text(json.dumps(row))
    elif mutation == "delete_row":
        (path / "one.json").unlink()
    elif mutation == "manifest":
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        manifest["identities"]["protocol_sha256"] = "e" * 64
        (path / "manifest.json").write_text(json.dumps(manifest))
    elif mutation == "duplicate_json_key":
        summary_path.write_text(summary_path.read_text(encoding="utf-8").replace('"outcome_count": 2', '"outcome_count": 99, "outcome_count": 2'))
    if mutation not in {"duplicate_json_key"}:
        summary_path.write_text(json.dumps(summary))
    check = audit(path)
    assert check["integrity_verified"] is False
    assert check["valid_for_inference"] is False
    assert check["issues"]


def test_expected_manifest_anchor_is_enforced(tmp_path):
    path = tmp_path / "run"
    run(path)
    assert not audit(path, expected_manifest_sha256="0" * 64)["integrity_verified"]


def test_incomplete_run_audit_never_reexecutes(tmp_path):
    path = tmp_path / "run"
    def load(item):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        run(path, load=load)
    before = hashlib.sha256((path / "manifest.json").read_bytes()).hexdigest()
    check = audit(path)
    assert not check["valid_for_inference"]
    assert check["scheduled_count"] == 2
    assert before == hashlib.sha256((path / "manifest.json").read_bytes()).hexdigest()
    assert not (path / "summary.json").exists()


def test_retained_execution_failure_is_integrity_valid_but_not_inference_valid(tmp_path):
    path = tmp_path / "run"
    def execute(item):
        raise RuntimeError()
    run(path, execute=execute)
    check = audit(path)
    assert check["integrity_verified"]
    assert not check["valid_for_inference"]
    assert check["recomputed"]["correct_completion_denominator"] == 2


def test_legacy_version_is_not_silently_promoted(tmp_path):
    path = tmp_path / "run"
    run(path)
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    manifest["version"] = "neurocad-evaluation-ledger-v1"
    (path / "manifest.json").write_text(json.dumps(manifest))
    assert not audit(path)["integrity_verified"]


def test_expected_summary_anchor_is_enforced(tmp_path):
    path = tmp_path / "run"
    run(path)
    expected = hashlib.sha256((path / "summary.json").read_bytes()).hexdigest()
    assert audit(path, expected_summary_sha256=expected)["integrity_verified"]
    assert not audit(path, expected_summary_sha256="0" * 64)["integrity_verified"]


@pytest.mark.parametrize("replacement", ["NaN", "1e10000", "[" * 257 + "]" * 257])
def test_malformed_json_is_rejected(tmp_path, replacement):
    path = tmp_path / "run"
    run(path)
    (path / "summary.json").write_text(replacement)
    assert not audit(path)["integrity_verified"]


def test_symlink_outcome_is_not_accepted(tmp_path):
    path = tmp_path / "run"
    run(path)
    row = path / "one.json"
    outside = tmp_path / "outside.json"
    outside.write_bytes(row.read_bytes())
    row.unlink()
    row.symlink_to(outside)
    assert not audit(path)["integrity_verified"]


def test_read_limit_is_enforced_without_unbounded_reads(tmp_path, monkeypatch):
    path = tmp_path / "run"
    run(path)
    monkeypatch.setattr(ledger, "MAX_DOCUMENT_BYTES", 8)
    assert not audit(path)["integrity_verified"]


def test_audit_preserves_bytes_and_cli_exit_status(tmp_path, monkeypatch, capsys):
    path = tmp_path / "run"
    run(path)
    before = {p.name: p.read_bytes() for p in path.iterdir()}
    monkeypatch.setattr("sys.argv", ["ledger-audit", str(path)])
    assert ledger.main() == 0
    assert json.loads(capsys.readouterr().out)["integrity_verified"]
    assert before == {p.name: p.read_bytes() for p in path.iterdir()}
    monkeypatch.setattr("sys.argv", ["ledger-audit", str(tmp_path / "absent")])
    assert ledger.main() == 2
    assert not json.loads(capsys.readouterr().out)["integrity_verified"]


def test_persistence_failure_remains_auditable_without_claiming_success(tmp_path, monkeypatch):
    original = ledger._write
    def write(path, value):
        if path.name == "one.json":
            raise OSError()
        return original(path, value)
    monkeypatch.setattr(ledger, "_write", write)
    path = tmp_path / "run"
    run(path)
    check = audit(path)
    assert check["integrity_verified"]
    assert not check["valid_for_inference"]
    assert check["recomputed"]["status"] == "INCOMPLETE_OR_ERROR"
