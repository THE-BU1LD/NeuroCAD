from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

import core.source_identity as identity
import neurocad_cli


def _installation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "installation"
    (root / "core" / "schemas").mkdir(parents=True)
    (root / "core" / "static").mkdir()
    for name, content in {
        "neurocad_cli.py": "# executing cli\n",
        "text_to_cad.py": "# compiler entry\n",
        "text_to_openscad.py": "# alternate entry\n",
        "core/__init__.py": "# core\n",
        "core/source_identity.py": "# source identity fixture\n",
        "core/schemas/design.json": '{"type":"object"}\n',
        "core/static/viewer.js": "// viewer\n",
        "core/static/LICENSE": "fixture license\n",
    }.items():
        (root / name).write_text(content, encoding="utf-8")
    monkeypatch.delenv("NEUROCAD_SOURCE_REVISION", raising=False)
    monkeypatch.setattr(identity, "__file__", str(root / "core" / "source_identity.py"))
    monkeypatch.setattr(identity, "_module_source", lambda name: Path(identity.__file__).parent.parent / f"{name}.py")
    return root


def test_identity_contains_compiler_entrypoints_schemas_and_static_resources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _installation(tmp_path, monkeypatch)
    result = identity.implementation_provenance(root / "neurocad_cli.py", "test")
    files = result["implementation_files"]
    assert set(files) == {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    assert files["core/schemas/design.json"] == hashlib.sha256((root / "core/schemas/design.json").read_bytes()).hexdigest()
    assert str(tmp_path) not in json.dumps(result)
    assert all(not Path(name).is_absolute() and "\\" not in name for name in files)
    assert result["source_revision_verifies_implementation"] is False


@pytest.mark.parametrize("name", ["neurocad_cli.py", "text_to_cad.py", "text_to_openscad.py", "core/schemas/design.json", "core/static/viewer.js"])
def test_identity_changes_when_a_declared_runtime_file_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    root = _installation(tmp_path, monkeypatch)
    before = identity.implementation_provenance(root / "neurocad_cli.py", "test")
    (root / name).write_text("changed bytes\n", encoding="utf-8")
    after = identity.implementation_provenance(root / "neurocad_cli.py", "test")
    assert before["implementation_sha256"] != after["implementation_sha256"]
    assert before["implementation_files"][name] != after["implementation_files"][name]


def test_identity_is_stable_after_relocation_and_ignores_bytecode_caches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _installation(tmp_path, monkeypatch)
    before = identity.implementation_provenance(root / "neurocad_cli.py", "test")
    destination = tmp_path / "other-installation"
    shutil.copytree(root, destination)
    (destination / "core" / "__pycache__").mkdir()
    (destination / "core" / "__pycache__" / "noise.pyc").write_bytes(b"cached bytecode")
    monkeypatch.setattr(identity, "__file__", str(destination / "core" / "source_identity.py"))
    assert identity.implementation_provenance(destination / "neurocad_cli.py", "test") == before


def test_user_supplied_revision_is_explicitly_unverified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _installation(tmp_path, monkeypatch)
    monkeypatch.setenv("NEUROCAD_SOURCE_REVISION", "A" * 40)
    result = identity.implementation_provenance(root / "neurocad_cli.py", "test")
    assert result["source_revision"] == "a" * 40
    assert result["source_revision_status"] == "user_supplied_unverified"
    assert result["source_revision_verifies_implementation"] is False
    monkeypatch.setenv("NEUROCAD_SOURCE_REVISION", "main")
    with pytest.raises(ValueError, match="full hexadecimal Git revision"):
        identity.implementation_provenance(root / "neurocad_cli.py", "test")


def test_enclosing_checkout_is_not_attributed_to_nested_installed_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _installation(tmp_path, monkeypatch)
    (tmp_path / ".git").mkdir()
    result = identity.implementation_provenance(root / "neurocad_cli.py", "test")
    assert result["source_revision"] is None
    assert result["source_revision_status"] == "not_available_from_installed_package"


def test_provenance_dispatch_reports_the_executing_cli_and_no_generation(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEUROCAD_SOURCE_REVISION", raising=False)
    with pytest.raises(SystemExit) as exit_info:
        neurocad_cli.main(["provenance", "--json"])
    assert exit_info.value.code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["implementation_files"]["neurocad_cli.py"] == hashlib.sha256(Path(neurocad_cli.__file__).read_bytes()).hexdigest()
    assert "core/schemas/neurocad_ir_v1.schema.json" in result["implementation_files"]
    assert result["source_revision_verifies_implementation"] is False
