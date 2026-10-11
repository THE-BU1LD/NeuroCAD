"""Build deterministic Physics v2 arXiv and full research release archives."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RELEASE_VERSION = "NC-PHYSICS-V2-PROVENANCE-v1.0.0"
PACKAGE_ROOT = "neurocad-physics-v2-v1.0.0"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()


def _tar_gz(entries: list[tuple[str, bytes]]) -> bytes:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name, data in sorted(entries):
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mode = 0o644
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            archive.addfile(info, io.BytesIO(data))
    compressed = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as stream:
        stream.write(tar_buffer.getvalue())
    return compressed.getvalue()


def _required_paths() -> list[Path]:
    fixed = [
        Path("README.md"),
        Path("LICENSE"),
        Path("pyproject.toml"),
        Path("requirements-research.in"),
        Path("requirements-research.lock"),
        Path("neurocad_cli.py"),
        Path("core/agentic.py"),
        Path("core/artifacts.py"),
        Path("core/json_io.py"),
        Path("core/physics.py"),
        Path("core/physics_context.py"),
        Path("tests/test_agentic.py"),
        Path("tests/test_cli_verification.py"),
        Path("tests/test_feature_cli.py"),
        Path("tests/test_physics.py"),
        Path("tests/test_physics_research.py"),
        Path("paper/physics_v2/ARXIV_METADATA.md"),
        Path("paper/physics_v2/README.md"),
        Path("paper/physics_v2/generate_results.py"),
        Path("paper/physics_v2/generated_results.tex"),
        Path("paper/physics_v2/main.tex"),
        Path("release/physics_v2/README.md"),
        Path("output/pdf/neurocad-physics-v2-paper.pdf"),
        Path("output/arxiv/neurocad-physics-v2-arxiv-source.tar.gz"),
    ]
    study = [
        path.relative_to(ROOT) for path in (ROOT / "research/physics_v2").rglob("*") if path.is_file() and "__pycache__" not in path.parts
    ]
    return sorted(set(fixed + study))


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def build(source_commit: str) -> dict[str, Any]:
    if _git("status", "--porcelain"):
        raise ValueError("release build requires a clean checkout")
    if _git("rev-parse", "HEAD") != source_commit:
        raise ValueError("source commit must equal checkout HEAD")

    arxiv_path = ROOT / "output/arxiv/neurocad-physics-v2-arxiv-source.tar.gz"
    arxiv_entries = [
        ("generated_results.tex", (ROOT / "paper/physics_v2/generated_results.tex").read_bytes()),
        ("main.tex", (ROOT / "paper/physics_v2/main.tex").read_bytes()),
    ]
    _write_atomic(arxiv_path, _tar_gz(arxiv_entries))

    paths = _required_paths()
    missing = [str(path) for path in paths if not (ROOT / path).is_file()]
    if missing:
        raise FileNotFoundError(f"missing release files: {missing}")
    files = [
        {
            "path": path.as_posix(),
            "sha256": _sha256_file(ROOT / path),
            "size_bytes": (ROOT / path).stat().st_size,
        }
        for path in paths
    ]
    manifest: dict[str, Any] = {
        "schema_version": "nc-physics-v2-release-manifest-v1",
        "release_version": RELEASE_VERSION,
        "source_commit": source_commit,
        "scientific_disposition": "SUPPORTED_WITHIN_CONTROLLED_CONTRACT",
        "claim_boundary": (
            "frozen 216-case synthetic software-contract conformance matrix; "
            "not physical validation, safety certification, enterprise generalization, "
            "independent reproduction, arXiv submission, or publication"
        ),
        "protected_execution": "EXECUTED_ONCE_NO_RERUN",
        "verification": "INTERNAL_CLEAN_CHECKOUT_PASS_EXTERNAL_INDEPENDENT_NOT_YET",
        "ethics": "synthetic cases; no human or animal participants; no personal data",
        "code_license": "MIT; see LICENSE",
        "paper_distribution_license": "AUTHOR_SELECTION_REQUIRED_AT_SUBMISSION",
        "author_metadata": "AUTHOR_CONFIRMATION_REQUIRED_AT_SUBMISSION",
        "arxiv_status": "TECHNICALLY_PREPARED_NOT_SUBMITTED",
        "files": files,
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    manifest_path = ROOT / "release/physics_v2/RELEASE_MANIFEST.json"
    _write_atomic(manifest_path, manifest_bytes)

    package_entries = [(f"{PACKAGE_ROOT}/{path.as_posix()}", (ROOT / path).read_bytes()) for path in paths]
    package_entries.append((f"{PACKAGE_ROOT}/release/physics_v2/RELEASE_MANIFEST.json", manifest_bytes))
    package_path = ROOT / "output/release/neurocad-physics-v2-research-release.tar.gz"
    _write_atomic(package_path, _tar_gz(package_entries))

    receipt = {
        "schema_version": "nc-physics-v2-release-receipt-v1",
        "release_version": RELEASE_VERSION,
        "source_commit": source_commit,
        "paper_pdf": {
            "path": "output/pdf/neurocad-physics-v2-paper.pdf",
            "sha256": _sha256_file(ROOT / "output/pdf/neurocad-physics-v2-paper.pdf"),
        },
        "arxiv_source": {
            "path": arxiv_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256_file(arxiv_path),
        },
        "release_manifest": {
            "path": manifest_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256_bytes(manifest_bytes),
        },
        "release_archive": {
            "path": package_path.relative_to(ROOT).as_posix(),
            "sha256": _sha256_file(package_path),
        },
        "boundary": "local packaging receipt; not an external repository or submission receipt",
    }
    receipt_path = ROOT / "output/release/RELEASE_RECEIPT.json"
    _write_atomic(receipt_path, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source_commit), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
