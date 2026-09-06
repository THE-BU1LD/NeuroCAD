"""Normalize a setuptools source archive for byte-reproducible releases."""

from __future__ import annotations

import argparse
import gzip
import os
import stat
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


def normalize_sdist(archive: Path, source_date_epoch: int) -> None:
    """Rewrite one ``.tar.gz`` with stable ownership and timestamps."""

    archive = Path(archive)
    if not archive.is_file() or not archive.name.endswith(".tar.gz"):
        raise ValueError("archive must identify an existing .tar.gz file")
    if isinstance(source_date_epoch, bool) or not isinstance(source_date_epoch, int) or source_date_epoch < 0:
        raise ValueError("source_date_epoch must be a non-negative integer")
    archive_mode = stat.S_IMODE(archive.stat().st_mode)

    temporary_name: str | None = None
    try:
        with (
            tarfile.open(archive, "r:gz") as source,
            tempfile.NamedTemporaryFile(
                mode="wb", prefix=f".{archive.name}.", suffix=".tmp", dir=archive.parent, delete=False
            ) as temporary,
            gzip.GzipFile(
                filename="", mode="wb", fileobj=temporary, compresslevel=9, mtime=source_date_epoch
            ) as compressed,
            tarfile.open(fileobj=compressed, mode="w|", format=tarfile.PAX_FORMAT) as destination,
        ):
            temporary_name = temporary.name
            for member in source:
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts:
                    raise ValueError(f"unsafe path in source distribution: {member.name!r}")
                member.mtime = source_date_epoch
                member.uid = 0
                member.gid = 0
                member.uname = ""
                member.gname = ""
                member.pax_headers = {}
                payload = source.extractfile(member) if member.isfile() else None
                destination.addfile(member, payload)
        os.replace(temporary_name, archive)
        archive.chmod(archive_mode)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("source_date_epoch", type=int)
    args = parser.parse_args()
    normalize_sdist(args.archive, args.source_date_epoch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
