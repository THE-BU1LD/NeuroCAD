from __future__ import annotations

from types import SimpleNamespace

import pytest

from research.vericodegen import offline_ledger_smoke


def test_git_head_returns_exact_resolved_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        offline_ledger_smoke.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="abc1234\n", stderr=""),
    )
    assert offline_ledger_smoke._git_head() == "abc1234"


def test_git_head_fails_cleanly_without_repository_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        offline_ledger_smoke.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        ),
    )
    with pytest.raises(offline_ledger_smoke.OfflineSmokeError, match="requires a real Git checkout"):
        offline_ledger_smoke._git_head()
