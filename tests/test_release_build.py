from __future__ import annotations

import io
import stat
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.normalize_sdist import normalize_sdist
from scripts.verify_distribution import verify_distribution


def _source_archive(path: Path, *, mtime: int, unsafe: bool = False) -> None:
    with tarfile.open(path, "w:gz") as archive:
        root = tarfile.TarInfo("../escape" if unsafe else "example-1.0")
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        root.mtime = mtime
        root.uid = 501
        root.gid = 20
        archive.addfile(root)
        if not unsafe:
            content = b"verified artifact\n"
            member = tarfile.TarInfo("example-1.0/README.md")
            member.size = len(content)
            member.mode = 0o644
            member.mtime = mtime + 7
            member.uid = 501
            member.gid = 20
            archive.addfile(member, io.BytesIO(content))


def test_sdist_normalization_is_reproducible_and_removes_local_identity(tmp_path: Path) -> None:
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    _source_archive(first, mtime=100)
    _source_archive(second, mtime=900)
    first.chmod(0o644)
    second.chmod(0o644)

    normalize_sdist(first, 123456789)
    normalize_sdist(second, 123456789)

    assert first.read_bytes() == second.read_bytes()
    assert stat.S_IMODE(first.stat().st_mode) == stat.S_IMODE(second.stat().st_mode) == 0o644
    with tarfile.open(first, "r:gz") as archive:
        members = archive.getmembers()
        assert all(member.mtime == 123456789 for member in members)
        assert all(member.uid == member.gid == 0 for member in members)
        assert all(member.uname == member.gname == "" for member in members)


def test_sdist_normalization_rejects_unsafe_member_paths(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.tar.gz"
    _source_archive(archive, mtime=100, unsafe=True)
    original = archive.read_bytes()

    with pytest.raises(ValueError, match="unsafe path"):
        normalize_sdist(archive, 123456789)

    assert archive.read_bytes() == original


def test_distribution_verification_accepts_safe_sdist(tmp_path: Path) -> None:
    archive = tmp_path / "example.tar.gz"
    _source_archive(archive, mtime=100)

    assert verify_distribution(archive) == 2


def test_distribution_verification_rejects_embedded_research_run(tmp_path: Path) -> None:
    archive = tmp_path / "example.whl"
    with zipfile.ZipFile(archive, "w") as wheel:
        wheel.writestr("example/research/runs/unreviewed/results.json", "{}")

    with pytest.raises(ValueError, match="forbidden path"):
        verify_distribution(archive)
