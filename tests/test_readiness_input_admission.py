"""A malformed evidence package must never establish completion."""
import json

import pytest
import test_v3_readiness_audit as readiness_fixture

MODULE = readiness_fixture.MODULE


@pytest.fixture
def fixture():
    case = readiness_fixture.ReadinessTests()
    case.setUp()
    yield case
    case.doCleanups()


@pytest.mark.parametrize("value", [True, 1.0])
def test_schema_version_requires_integer(fixture, value):
    fixture.manifest["schema_version"] = value
    assert not fixture.run_audit()["complete"]


@pytest.mark.parametrize("text", ['{"status":"FAIL","status":"PASS","passed":5}',
                                  '{"status":"PASS","passed":5,"unused":NaN}',
                                  '{"status":"PASS","passed":5,"unused":1e999}'])
def test_ambiguous_or_nonfinite_json_is_rejected(fixture, text):
    fixture.evidence.write_text(text, encoding="utf-8")
    fixture.manifest["items"][0]["evidence"][0]["sha256"] = MODULE.sha256(fixture.evidence)
    assert not fixture.run_audit()["complete"]


@pytest.mark.parametrize("pointer", ["/-1", "/+0", "/00", "/ 0"])
def test_array_pointer_has_no_python_index_extensions(pointer):
    with pytest.raises(ValueError):
        MODULE.at_pointer(["PASS"], pointer)


def test_pointer_escape_must_be_valid():
    with pytest.raises(ValueError):
        MODULE.at_pointer({"~2": "PASS"}, "/~2")


def test_valid_pointer_controls():
    assert MODULE.at_pointer({"a/b": {"~": ["PASS"]}}, "/a~1b/~0/0") == "PASS"


@pytest.mark.parametrize("value", [None, [], "manifest"])
def test_malformed_manifest_returns_failure(fixture, value):
    assert MODULE.audit(fixture.root, value)["audit_status"] == "FAIL"


@pytest.mark.parametrize("field,value", [("items", [None]), ("items", "bad"),
                                         ("verified_source", None), ("verified_source", {"files": []})])
def test_malformed_containers_return_failure(fixture, field, value):
    fixture.manifest[field] = value
    assert fixture.run_audit()["audit_status"] == "FAIL"


def test_nested_booleans_do_not_equal_integers(fixture):
    fixture.evidence.write_text(json.dumps({"values": [True]}), encoding="utf-8")
    record = fixture.manifest["items"][0]["evidence"][0]
    record["sha256"] = MODULE.sha256(fixture.evidence)
    record["assertions"] = [{"pointer": "/values", "equals": [1]}]
    assert not fixture.run_audit()["complete"]


def test_bounded_evidence_read(fixture, monkeypatch):
    monkeypatch.setattr(MODULE, "MAX_JSON_BYTES", 10)
    assert not fixture.run_audit()["complete"]


def test_hash_matches_exact_parsed_bytes(fixture):
    with pytest.raises(ValueError, match="hash mismatch"):
        MODULE.read_json(fixture.evidence, "0" * 64)


def test_nested_boolean_in_object_does_not_equal_integer(fixture):
    fixture.evidence.write_text(json.dumps({"values": {"count": True}}), encoding="utf-8")
    record = fixture.manifest["items"][0]["evidence"][0]
    record["sha256"] = MODULE.sha256(fixture.evidence)
    record["assertions"] = [{"pointer": "/values", "equals": {"count": 1}}]
    assert not fixture.run_audit()["complete"]
