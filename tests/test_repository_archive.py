"""Checkout-only checks of historical archives deliberately excluded from sdist."""

import json
from pathlib import Path

from scripts.build_legacy_archive_index import build_index, verify_index

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_fake_step_export_is_hard_disabled() -> None:
    source = (ROOT / "legacy/python/cad_intelligence_core_allinone.py").read_text(encoding="utf-8")
    assert "Mesh " + "place" + "holder STEP" not in source
    assert "STEP export is unsupported" in source


def test_disconnected_experiments_remain_archived() -> None:
    assert (ROOT / "legacy/python/cad_master_kernel_legacy_broken.py").is_file()
    assert (ROOT / "legacy/README.md").is_file()


def test_legacy_archive_manifest_classifies_and_hashes_every_file(tmp_path: Path) -> None:
    manifest = build_index(ROOT / "legacy")
    recorded = json.loads((ROOT / "audit/legacy_archive_manifest.json").read_text(encoding="utf-8"))
    expected = {path.relative_to(ROOT / "legacy").as_posix() for path in (ROOT / "legacy").rglob("*") if path.is_file()}
    assert manifest["entry_count"] == len(expected)
    assert {entry["path"] for entry in manifest["entries"]} == expected
    assert all(len(entry["sha256"]) == 64 for entry in manifest["entries"])
    assert all(entry["capability_class"] and entry["failure_class"] for entry in manifest["entries"])
    assert any("known_broken_source" in entry["risks"] for entry in manifest["entries"])
    assert recorded == manifest

    output = tmp_path / "manifest.json"
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert verify_index(ROOT / "legacy", output)["status"] == "verified"
