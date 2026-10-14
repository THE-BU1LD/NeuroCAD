"""Read-only verification of listed artifacts; no execution or evidence repair."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

MAX_MANIFEST_BYTES = 16 * 1024 * 1024
MAX_ARTIFACT_BYTES = 1024 * 1024 * 1024
MAX_ARTIFACTS = 100_000


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def safe_relative_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (not name or "\\" in name or ":" in name or "\x00" in name
            or path.is_absolute() or path.as_posix() != name
            or any(part in ("", ".", "..") for part in name.split("/"))):
        raise ValueError(f"unsafe artifact path: {name!r}")
    return path


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    read_bytes = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            read_bytes += len(chunk)
            if read_bytes > MAX_ARTIFACT_BYTES:
                raise ValueError("artifact exceeds 1 GiB audit limit")
            digest.update(chunk)
    return digest.hexdigest()


def audit(manifest: Path, manifest_format: str = "research") -> dict[str, Any]:
    """Audit a stable local directory; this is not a sandbox for concurrent writers."""
    if manifest_format not in ("research", "hashes"):
        raise ValueError("manifest format must be research or hashes")
    if manifest.is_symlink() or not manifest.is_file():
        raise ValueError("manifest must be a regular file, not a symlink")
    with manifest.open("rb") as handle:
        raw = handle.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("manifest exceeds 16 MiB audit limit")
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    if not isinstance(data, dict):
        raise TypeError("manifest must be a JSON object")
    entries = data.get("artifact_sha256") if manifest_format == "research" else data
    if not isinstance(entries, dict) or not 1 <= len(entries) <= MAX_ARTIFACTS:
        raise ValueError("manifest must contain 1 to 100000 artifact digests")
    # Validate every path and digest before reading any artifact.
    for name, expected in entries.items():
        safe_relative_path(name)
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"invalid SHA-256 for {name!r}")
    root = manifest.parent.resolve()
    failures = []
    matched = 0
    for name, expected in sorted(entries.items()):
        path = root / name
        try:
            cursor = root
            for part in safe_relative_path(name).parts:
                cursor = cursor / part
                if cursor.is_symlink():
                    raise ValueError("artifact path contains a symlink")
            if not path.is_file():
                raise ValueError("missing or not a regular file")
            if path.stat().st_size > MAX_ARTIFACT_BYTES:
                raise ValueError("artifact exceeds 1 GiB audit limit")
            actual = file_digest(path)
            if actual != expected:
                failures.append({"path": name, "error": "sha256 mismatch",
                                 "expected_sha256": expected, "actual_sha256": actual})
            else:
                matched += 1
        except (OSError, ValueError) as error:
            failures.append({"path": name, "error": str(error)})
    return {
        "schema": "neurocad-retained-artifact-audit-v1",
        "status": "PASS" if not failures else "FAIL",
        "mode": "READ_ONLY_HASH_AUDIT_NO_REEXECUTION",
        "manifest_format": manifest_format,
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "listed": len(entries), "matched": matched, "failures": failures,
        "scope": "Only listed artifacts. Hash agreement does not establish authenticity, "
                 "independence, original collection, or scientific validity. Extra files are not audited.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--format", choices=("research", "hashes"), default="research",
                        help="research: artifact_sha256 map; hashes: direct path-to-digest map")
    args = parser.parse_args()
    try:
        result = audit(args.manifest, args.format)
    except (OSError, TypeError, ValueError) as error:
        print(json.dumps({"status": "INVALID_MANIFEST", "error": str(error)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
