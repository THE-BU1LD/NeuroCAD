from pathlib import Path

import pytest

from core.artifacts import write_text_atomic


def test_no_replace_publication_preserves_existing_revision(tmp_path: Path) -> None:
    target = tmp_path / "revision.json"
    write_text_atomic(target, "original", overwrite=False)
    with pytest.raises(FileExistsError):
        write_text_atomic(target, "replacement", overwrite=False)
    assert target.read_text(encoding="utf-8") == "original"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["revision.json"]


def test_no_replace_refuses_dangling_symlink(tmp_path: Path) -> None:
    target = tmp_path / "revision.json"
    try:
        target.symlink_to(tmp_path / "absent")
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(FileExistsError):
        write_text_atomic(target, "replacement", overwrite=False)
    assert target.is_symlink()
    assert not (tmp_path / "absent").exists()
