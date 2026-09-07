"""Reject release archives that contain private, generated, or unsafe files."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

FORBIDDEN_COMPONENTS = frozenset(
    {
        ".c",
        ".git",
        ".portal-canonical",
        ".tmp-release-work",
        ".venv",
        "__pycache__",
        "legacy",
        "node_modules",
    }
)
FORBIDDEN_SEQUENCES = (("research", "runs"),)
FORBIDDEN_FILE_NAMES = frozenset(
    {
        ".env",
        "credentials.json",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "id_rsa",
        "service-account.json",
    }
)


def _validate_member_name(name: str) -> None:
    if "\\" in name:
        raise ValueError(f"ambiguous archive path separator: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe path in distribution: {name!r}")

    lowered = tuple(part.casefold() for part in path.parts)
    if any(part in FORBIDDEN_COMPONENTS for part in lowered):
        raise ValueError(f"forbidden directory in distribution: {name!r}")
    if lowered and lowered[-1] in FORBIDDEN_FILE_NAMES:
        raise ValueError(f"credential-like file in distribution: {name!r}")
    if lowered and lowered[-1].startswith(".env."):
        raise ValueError(f"environment file in distribution: {name!r}")
    for sequence in FORBIDDEN_SEQUENCES:
        if any(lowered[index : index + len(sequence)] == sequence for index in range(len(lowered) - len(sequence) + 1)):
            raise ValueError(f"forbidden path in distribution: {name!r}")


def _tar_member_names(archive: Path) -> Iterable[str]:
    with tarfile.open(archive, "r:gz") as source:
        for member in source:
            if not (member.isfile() or member.isdir()):
                raise ValueError(f"unsupported tar member type in distribution: {member.name!r}")
            yield member.name


def _zip_member_names(archive: Path) -> Iterable[str]:
    with zipfile.ZipFile(archive) as source:
        yield from source.namelist()


def verify_distribution(archive: Path) -> int:
    """Validate archive paths and return the number of inspected members."""

    archive = Path(archive)
    if not archive.is_file():
        raise ValueError(f"distribution does not exist: {archive}")
    if archive.name.endswith(".tar.gz"):
        names = _tar_member_names(archive)
    elif archive.suffix == ".whl":
        names = _zip_member_names(archive)
    else:
        raise ValueError("distribution must be a .whl or .tar.gz archive")

    count = 0
    for name in names:
        _validate_member_name(name)
        count += 1
    if count == 0:
        raise ValueError("distribution archive is empty")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+", type=Path)
    args = parser.parse_args()
    for archive in args.archives:
        count = verify_distribution(archive)
        print(f"Verified {archive}: {count} safe members")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
