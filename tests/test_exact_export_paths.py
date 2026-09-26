"""Non-native preflight tests for exact STEP artifact destinations."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.exact_build123d import Build123dBackend, Build123dCompileError
from core.feature_ir import Feature, FeatureProgram


class NativeExecutionAttempt(RuntimeError):
    pass


def _guarded_backend(monkeypatch: pytest.MonkeyPatch) -> Build123dBackend:
    backend = Build123dBackend.__new__(Build123dBackend)

    def refuse_native_work(program: FeatureProgram) -> dict:
        raise NativeExecutionAttempt("native CAD must not run during invalid-path preflight")

    monkeypatch.setattr(backend, "compile", refuse_native_work)
    return backend


def _program() -> FeatureProgram:
    return FeatureProgram(
        title="export path preflight",
        parameters=(),
        features=(Feature(id="body", kind="primitive_box", parameters={"size": [4.0, 3.0, 2.0]}),),
        outputs=("body",),
    )


@pytest.mark.parametrize(
    "filename",
    [
        "../outside.step",
        "/absolute.step",
        "nested/design.step",
        "nested\\design.step",
        "C:outside.step",
        "build-receipt.json",
        "requirements.json",
        "",
        ".",
        "..",
        "CON.step",
        "nul.stp",
        "LPT1.step",
        "bad\x00.step",
        "bad\n.step",
    ],
)
def test_unsafe_step_filename_fails_before_native_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, filename: str
) -> None:
    backend = _guarded_backend(monkeypatch)
    destination = tmp_path / "bundle"
    with pytest.raises(Build123dCompileError, match="filename"):
        backend.export_verified_step(_program(), destination, filename=filename)
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("filename", ["design.step", "custom.STEP", "part.stp"])
def test_plain_step_filename_reaches_compiler_and_cleans_failed_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, filename: str
) -> None:
    backend = _guarded_backend(monkeypatch)
    with pytest.raises(NativeExecutionAttempt):
        backend.export_verified_step(_program(), tmp_path / "bundle", filename=filename)
    assert list(tmp_path.iterdir()) == []


def test_dangling_output_symlink_is_rejected_before_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "bundle"
    target = tmp_path / "unrelated-target"
    try:
        destination.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    backend = _guarded_backend(monkeypatch)
    with pytest.raises(FileExistsError):
        backend.export_verified_step(_program(), destination)
    assert destination.is_symlink()
    assert not target.exists()
    assert not list(tmp_path.glob(".unrelated-target.*"))


def test_existing_output_directory_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "bundle"
    destination.mkdir()
    marker = destination / "existing.txt"
    marker.write_text("preserve me", encoding="utf-8")
    backend = _guarded_backend(monkeypatch)
    with pytest.raises(FileExistsError):
        backend.export_verified_step(_program(), destination)
    assert marker.read_text(encoding="utf-8") == "preserve me"
    assert not list(tmp_path.glob(".bundle.*"))
