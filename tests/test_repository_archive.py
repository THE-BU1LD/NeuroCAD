"""Checkout-only checks of historical archives deliberately excluded from sdist."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_fake_step_export_is_hard_disabled() -> None:
    source = (ROOT / "legacy/python/cad_intelligence_core_allinone.py").read_text(encoding="utf-8")
    assert "Mesh " + "place" + "holder STEP" not in source
    assert "STEP export is unsupported" in source


def test_disconnected_experiments_remain_archived() -> None:
    assert (ROOT / "legacy/python/cad_master_kernel_legacy_broken.py").is_file()
    assert (ROOT / "legacy/README.md").is_file()
