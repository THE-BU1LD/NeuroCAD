from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.vericodegen import safe_trial_ledger as safe
from research.vericodegen import trial_ledger as ledger
from research.vericodegen.arm_adapter import ArmAdapterError


def test_unknown_geometry_kind_is_unsupported_operation() -> None:
    exc = ArmAdapterError("kind must be one of: box, cylinder, sphere")
    assert safe.classify_adapter_error(exc) == "unsupported_operation"


def test_generic_adapter_failure_remains_syntax_compile_failure() -> None:
    exc = ArmAdapterError("structured response is not valid JSON")
    assert safe.classify_adapter_error(exc) == "syntax_compile_failure"


def test_over_budget_capture_rejects_before_analysis_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = tmp_path / "manifest.json"
    capture_path = tmp_path / "capture.jsonl"
    outdir = tmp_path / "out"
    manifest_path.write_text('{"cost_cap_usd": 1.0}\n', encoding="utf-8")
    capture_path.write_text(
        json.dumps({"estimated_cost_usd": 1.01}) + "\n", encoding="utf-8"
    )

    monkeypatch.setattr(
        safe,
        "_frozen_preflight",
        lambda _kwargs: {"cost_cap_usd": 1.0},
    )
    monkeypatch.setattr(
        ledger,
        "load_capture_jsonl",
        lambda _path: [{"estimated_cost_usd": 1.01}],
    )

    called = False

    def _should_not_run(**_kwargs: object) -> dict[str, object]:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(ledger, "evaluate_capture", _should_not_run)

    with pytest.raises(ledger.TrialLedgerError, match="exceeds frozen cost cap"):
        safe.evaluate_capture(
            manifest_path=manifest_path,
            capture_path=capture_path,
            outdir=outdir,
        )

    assert called is False
    assert not (outdir / "attempts_evaluated.jsonl").exists()
    assert not (outdir / "finals_for_analysis.jsonl").exists()
    assert not (outdir / "summary.json").exists()

    rejection = json.loads((outdir / "rejection.json").read_text(encoding="utf-8"))
    assert rejection["accepted"] is False
    assert rejection["scientific_evidence"] is False
    assert rejection["reason"] == "cost_cap_exceeded"
    assert rejection["total_estimated_cost_usd"] == pytest.approx(1.01)
    assert rejection["cost_cap_usd"] == pytest.approx(1.0)


def test_frozen_provenance_is_checked_before_capture_is_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = tmp_path / "manifest.json"
    capture_path = tmp_path / "capture.jsonl"
    manifest_path.write_text('{"cost_cap_usd": 2.0}\n', encoding="utf-8")
    capture_path.write_text(
        json.dumps({"estimated_cost_usd": 0.25}) + "\n", encoding="utf-8"
    )

    events: list[str] = []

    def _frozen(_kwargs: object) -> dict[str, float]:
        events.append("frozen")
        return {"cost_cap_usd": 2.0}

    def _capture(_path: Path) -> list[dict[str, float]]:
        events.append("capture")
        return [{"estimated_cost_usd": 0.25}]

    def _evaluate(**_kwargs: object) -> dict[str, bool]:
        events.append("evaluate")
        return {"ok": True}

    monkeypatch.setattr(safe, "_frozen_preflight", _frozen)
    monkeypatch.setattr(ledger, "load_capture_jsonl", _capture)
    monkeypatch.setattr(ledger, "evaluate_capture", _evaluate)

    result = safe.evaluate_capture(
        manifest_path=manifest_path,
        capture_path=capture_path,
        outdir=tmp_path / "out",
    )

    assert result == {"ok": True}
    assert events == ["frozen", "capture", "evaluate"]


def test_safe_evaluation_installs_classifier_only_for_wrapped_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = tmp_path / "manifest.json"
    capture_path = tmp_path / "capture.jsonl"
    manifest_path.write_text('{"cost_cap_usd": 2.0}\n', encoding="utf-8")
    capture_path.write_text(
        json.dumps({"estimated_cost_usd": 0.25}) + "\n", encoding="utf-8"
    )

    monkeypatch.setattr(
        safe,
        "_frozen_preflight",
        lambda _kwargs: {"cost_cap_usd": 2.0},
    )
    monkeypatch.setattr(
        ledger,
        "load_capture_jsonl",
        lambda _path: [{"estimated_cost_usd": 0.25}],
    )

    original = ledger._classify_adapter_error

    def _observe_classifier(**_kwargs: object) -> dict[str, object]:
        assert ledger._classify_adapter_error(
            ArmAdapterError("kind must be one of: box, cylinder")
        ) == "unsupported_operation"
        return {"ok": True}

    monkeypatch.setattr(ledger, "evaluate_capture", _observe_classifier)

    result = safe.evaluate_capture(
        manifest_path=manifest_path,
        capture_path=capture_path,
        outdir=tmp_path / "out",
    )

    assert result == {"ok": True}
    assert ledger._classify_adapter_error is original
