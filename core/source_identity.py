"""Source/resource identity collected by the executing NeuroCAD interpreter.

This is an on-disk snapshot, not an attestation of loaded machine code, package
authenticity, third-party dependencies, or correspondence with a Git revision.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import platform
import re
import shutil
import subprocess  # nosec B404
from pathlib import Path
from typing import Any

IDENTITY_VERSION = "neurocad-source-identity-v1"
_HEX_REVISION = re.compile(r"[0-9a-fA-F]{40,64}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _module_source(name: str) -> Path:
    spec = importlib.util.find_spec(name)
    if spec is None or spec.origin is None:
        raise ValueError(f"could not locate NeuroCAD source module {name}")
    path = Path(spec.origin).resolve()
    if path.suffix != ".py" or not path.is_file():
        raise ValueError(f"NeuroCAD source module {name} is not a readable Python source file")
    return path


def _revision_metadata(cli_source: Path) -> tuple[str | None, str]:
    requested = os.environ.get("NEUROCAD_SOURCE_REVISION", "").strip()
    if requested:
        if _HEX_REVISION.fullmatch(requested) is None:
            raise ValueError("NEUROCAD_SOURCE_REVISION must be a full hexadecimal Git revision")
        return requested.lower(), "user_supplied_unverified"
    # Only the CLI's own checkout root is relevant. An enclosing Git repository
    # around a virtualenv does not identify the code installed in that virtualenv.
    root = cli_source.parent
    git = shutil.which("git")
    if (root / ".git").exists() and git:
        try:
            completed = subprocess.run(  # nosec B603 - fixed read-only Git argv, no shell
                [git, "-C", str(root), "rev-parse", "HEAD"],
                capture_output=True, text=True, check=False, timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            pass
        else:
            revision = completed.stdout.strip()
            if completed.returncode == 0 and _HEX_REVISION.fullmatch(revision):
                return revision.lower(), "observed_checkout"
    return None, "not_available_from_installed_package"


def implementation_provenance(cli_source: Path, version: str) -> dict[str, Any]:
    """Hash this interpreter's CLI, compiler modules and packaged resources.

    Names are logical POSIX-relative paths. Neither timestamps nor absolute
    installation paths enter the identity, so equivalent copies remain equal.
    """
    cli_source = cli_source.resolve()
    if cli_source.suffix != ".py" or not cli_source.is_file():
        raise ValueError("the executing NeuroCAD CLI must have a readable Python source file")
    core_root = Path(__file__).resolve().parent
    files = {
        "neurocad_cli.py": cli_source,
        "text_to_cad.py": _module_source("text_to_cad"),
        "text_to_openscad.py": _module_source("text_to_openscad"),
    }
    for path in sorted(core_root.rglob("*")):
        relative = path.relative_to(core_root)
        if "__pycache__" in relative.parts or not path.is_file():
            continue
        if path.suffix in {".py", ".json", ".js"} or relative.as_posix() == "static/LICENSE":
            files[f"core/{relative.as_posix()}"] = path
    hashes = {name: _sha256(path) for name, path in sorted(files.items())}
    digest = hashlib.sha256("".join(f"{name}:{value}\n" for name, value in sorted(hashes.items())).encode("utf-8")).hexdigest()
    revision, revision_status = _revision_metadata(cli_source)
    return {
        "identity_version": IDENTITY_VERSION,
        "neurocad_version": version,
        "implementation_sha256": digest,
        "implementation_files": hashes,
        "identity_scope": ["neurocad_cli.py", "text_to_cad.py", "text_to_openscad.py", "core/**/*.py", "core/**/*.json", "core/**/*.js", "core/static/LICENSE"],
        "runtime": {"implementation": platform.python_implementation(), "python_version": platform.python_version()},
        "source_revision": revision,
        "source_revision_status": revision_status,
        "source_revision_verifies_implementation": False,
        "identity_boundary": "on-disk source and packaged resources; excludes loaded bytecode and third-party dependencies",
    }
