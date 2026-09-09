from __future__ import annotations

import io
import stat
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.normalize_sdist import normalize_sdist
from scripts.verify_distribution import verify_distribution


def test_sdist_retains_restored_pre_outcome_control_fixture() -> None:
    root = Path(__file__).resolve().parents[1]
    fixture = "research/s3/benchmark_candidate_pool_v0.csv"
    assert (root / fixture).is_file()
    assert f"include {fixture}" in (root / "MANIFEST.in").read_text()


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
    original_mode = stat.S_IMODE(first.stat().st_mode)

    normalize_sdist(first, 123456789)
    normalize_sdist(second, 123456789)

    assert first.read_bytes() == second.read_bytes()
    assert stat.S_IMODE(first.stat().st_mode) == stat.S_IMODE(second.stat().st_mode) == original_mode
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


def test_distribution_verification_rejects_wheel_symlinks(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.whl"
    member = zipfile.ZipInfo("core/linked.py")
    member.create_system = 3
    member.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as wheel:
        wheel.writestr(member, "../../outside.py")
    with pytest.raises(ValueError, match="unsupported zip member"):
        verify_distribution(archive)


@pytest.mark.parametrize("name", ["C:/outside.py", "core/module.py:stream", "../outside.py"])
def test_distribution_verification_rejects_nonportable_paths(tmp_path: Path, name: str) -> None:
    archive = tmp_path / "unsafe.whl"
    with zipfile.ZipFile(archive, "w") as wheel:
        wheel.writestr(name, "untrusted")
    with pytest.raises(ValueError, match="unsafe path"):
        verify_distribution(archive)


@pytest.mark.parametrize("name", ["core/module.py", "core/./module.py", "CORE/module.py"])
def test_distribution_verification_rejects_overwriting_members(tmp_path: Path, name: str) -> None:
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "w:gz") as source:
        for path in ("core/module.py", name):
            member = tarfile.TarInfo(path)
            member.size = 1
            source.addfile(member, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="duplicate or case-colliding"):
        verify_distribution(archive)
