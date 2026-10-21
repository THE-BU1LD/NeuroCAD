from pathlib import Path


def test_demo_receipt_binds_the_active_implementation_without_claiming_physical_validation() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (root / "demo" / "build_demo_kit.sh").read_text(encoding="utf-8")

    assert '"implementation": source_provenance()' in script
    assert '"implementation_sha256"' in script
    assert '"source_revision_status"' in script
    assert "user_supplied_unverified" in script
    assert '"physical_validation": "not performed"' in script
    assert "NEUROCAD_SOURCE_REVISION must be a full hexadecimal Git revision" in script


def test_demo_instructions_explain_the_receipt_provenance_boundary() -> None:
    root = Path(__file__).resolve().parents[1]
    readme = (root / "demo" / "README.md").read_text(encoding="utf-8")

    assert "NEUROCAD_SOURCE_REVISION" in readme
    assert "does not validate a release" in readme
    assert "user_supplied_unverified" in readme
