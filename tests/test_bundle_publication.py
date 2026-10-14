"""Output ownership survives publication races and dangling destination links."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from core import generation, workflow
from core.enclosure import EnclosureSpec, LidSpec, build_enclosure
from core.integrations import exchange, verify_exchange_bundle
from core.project import EnclosureProject


def _run(kind: str, destination: Path) -> Any:
    if kind == "generation":
        return generation.generate_artifacts(generation.GenerationRequest(
            prompt="a 20 x 30 x 4 mm plate",
            output_dir=str(destination),
            formats=("ir", "scad"),
        ))
    spec = EnclosureSpec(
        outer_size_mm=(60, 40, 20), wall_mm=2, profile="fdm_standard",
        lid=LidSpec("friction", thickness_mm=2, clearance_mm=0.3, lip_height_mm=2),
        title="publication control",
    )
    if kind == "project":
        return workflow.build_project_bundle(EnclosureProject("publication", spec), destination)
    return exchange.export_openscad_bundle(build_enclosure(spec), destination)


def _symlink(path: Path, target: Path) -> None:
    try:
        path.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlink creation is unavailable")


@pytest.mark.parametrize("kind", ["generation", "project", "exchange"])
def test_new_bundle_is_complete_and_staging_is_removed(tmp_path: Path, kind: str) -> None:
    destination = tmp_path / "bundle"
    bundle = _run(kind, destination)
    assert (destination / "manifest.json").is_file()
    assert list(destination.glob("*.scad"))
    assert sorted(path.name for path in tmp_path.iterdir()) == ["bundle"]
    if kind == "generation":
        assert generation.verify_artifact_bundle(destination)["status"] == "verified"
    elif kind == "project":
        assert workflow.verify_project_bundle(destination)["valid"]
    else:
        assert verify_exchange_bundle(bundle)["valid"]


@pytest.mark.parametrize("kind", ["generation", "project", "exchange"])
def test_dangling_destination_link_is_preserved_without_writing_its_target(tmp_path: Path, kind: str) -> None:
    destination, target = tmp_path / "bundle", tmp_path / "other-writer-target"
    _symlink(destination, target)
    original_inode = destination.lstat().st_ino
    with pytest.raises(FileExistsError):
        _run(kind, destination)
    assert destination.is_symlink() and destination.lstat().st_ino == original_inode
    assert not target.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == ["bundle"]


@pytest.mark.parametrize("kind", ["generation", "project", "exchange"])
@pytest.mark.parametrize("collision", ["empty-directory", "nonempty-directory", "file", "dangling-link"])
def test_late_destination_preserves_other_writer_and_cleans_only_own_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, collision: str,
) -> None:
    destination = tmp_path / "bundle"
    target = tmp_path / "other-writer-target"
    module: ModuleType = {"generation": generation, "project": workflow, "exchange": exchange}[kind]
    writer_name = "write_json_atomic" if kind == "exchange" else "write_text_atomic"
    original_write = getattr(module, writer_name)
    created_inodes: list[int] = []

    def write_then_collide(path: Path, payload: Any, **kwargs: Any) -> Path:
        result = original_write(path, payload, **kwargs)
        if path.name == "manifest.json":
            if collision in {"empty-directory", "nonempty-directory"}:
                destination.mkdir()
                if collision == "nonempty-directory":
                    (destination / "keep.txt").write_text("other writer", encoding="utf-8")
            elif collision == "file":
                destination.write_text("other writer", encoding="utf-8")
            else:
                _symlink(destination, target)
            created_inodes.append(destination.lstat().st_ino)
        return result

    monkeypatch.setattr(module, writer_name, write_then_collide)
    with pytest.raises(OSError):
        _run(kind, destination)
    assert created_inodes == [destination.lstat().st_ino]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["bundle"]
    if collision == "empty-directory":
        assert list(destination.iterdir()) == []
    elif collision == "nonempty-directory":
        assert [path.name for path in destination.iterdir()] == ["keep.txt"]
        assert (destination / "keep.txt").read_text(encoding="utf-8") == "other writer"
    elif collision == "file":
        assert destination.read_text(encoding="utf-8") == "other writer"
    else:
        assert destination.is_symlink() and not target.exists()
