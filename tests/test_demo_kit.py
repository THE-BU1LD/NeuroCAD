from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _demo_tools(tmp_path: Path, *, mutate: bool = False) -> tuple[dict[str, str], Path]:
    """Mock geometry execution, while exercising the actual shell receipt path."""
    if os.name == "nt" or shutil.which("bash") is None:
        pytest.skip("POSIX executable fixtures require bash")
    runtime = tmp_path / "executing-installation"
    runtime.mkdir()
    schema = runtime / "schema.json"
    schema.write_text('{"revision": 1}\n', encoding="utf-8")
    cli = runtime / "neurocad-fixture"
    cli.write_text(
        f"#!{sys.executable}\n" + r'''
import hashlib
import json
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
args = sys.argv[1:]
if args[0] == "provenance":
    files = {"neurocad_cli.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             "core/schemas/schema.json": hashlib.sha256((root / "schema.json").read_bytes()).hexdigest()}
    digest = hashlib.sha256("".join(f"{key}:{value}\n" for key, value in sorted(files.items())).encode()).hexdigest()
    print(json.dumps({"identity_version": "neurocad-source-identity-v1", "neurocad_version": "fixture",
                      "implementation_sha256": digest, "implementation_files": files,
                      "source_revision": None, "source_revision_status": "not_available_from_installed_package"}))
elif args[0] == "--version":
    print("NeuroCAD fixture")
elif args[0] == "create" and "aircraft" in args[1]:
    print("fixture unsupported request", file=sys.stderr)
    sys.exit(2)
else:
    for flag in ("-o", "--manifest", "--project-output"):
        if flag in args:
            path = Path(args[args.index(flag) + 1])
            path.write_text("fixture artifact\n", encoding="utf-8")
    if "--output-dir" in args:
        path = Path(args[args.index("--output-dir") + 1])
        path.mkdir()
        (path / "fixture.txt").write_text("fixture bundle\n", encoding="utf-8")
    if args[0] == "export" and os.environ.get("DEMO_TEST_MUTATE") == "1":
        (root / "schema.json").write_text('{"revision": 2}\n', encoding="utf-8")
    print("fixture stdout")
    print("fixture stderr", file=sys.stderr)
''',
        encoding="utf-8",
    )
    cli.chmod(0o755)
    other = tmp_path / "unrelated-installation"
    (other / "core").mkdir(parents=True)
    (other / "core" / "__init__.py").write_text("# unrelated core\n", encoding="utf-8")
    (other / "neurocad_cli.py").write_text("# unrelated CLI\n", encoding="utf-8")
    writer = tmp_path / "receipt-python"
    writer.write_text(
        f"#!/bin/sh\ncd {shlex.quote(str(other))}\nexec {shlex.quote(sys.executable)} \"$@\"\n",
        encoding="utf-8",
    )
    writer.chmod(0o755)
    openscad = tmp_path / "openscad"
    openscad.write_text("#!/bin/sh\necho OpenSCAD-fixture\n", encoding="utf-8")
    openscad.chmod(0o755)
    env = dict(os.environ)
    env.pop("NEUROCAD_SOURCE_REVISION", None)
    env.pop("PYTHONPATH", None)
    env.update({"NEUROCAD_CLI": str(cli), "PYTHON_BIN": str(writer), "PATH": f"{tmp_path}{os.pathsep}{env['PATH']}"})
    if mutate:
        env["DEMO_TEST_MUTATE"] = "1"
    return env, cli


def test_demo_receipt_uses_executing_cli_identity_with_unrelated_receipt_python(tmp_path: Path) -> None:
    env, cli = _demo_tools(tmp_path)
    destination = tmp_path / "demo"
    expected = json.loads(subprocess.check_output([str(cli), "provenance", "--json"], env=env, text=True))
    completed = subprocess.run(
        ["bash", str(ROOT / "demo" / "build_demo_kit.sh"), str(destination)],
        env=env, capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    receipt = json.loads((destination / "DEMO_RECEIPT.json").read_text(encoding="utf-8"))
    assert receipt["implementation"] == expected
    assert receipt["physical_validation"] == "not performed"
    assert str(tmp_path) not in json.dumps(receipt["implementation"])


def test_demo_refuses_success_receipt_after_implementation_changes(tmp_path: Path) -> None:
    env, _ = _demo_tools(tmp_path, mutate=True)
    destination = tmp_path / "demo"
    completed = subprocess.run(
        ["bash", str(ROOT / "demo" / "build_demo_kit.sh"), str(destination)],
        env=env, capture_output=True, text=True, check=False,
    )
    assert completed.returncode != 0
    assert "implementation changed" in completed.stderr
    assert not (destination / "DEMO_RECEIPT.json").exists()


def test_demo_instructions_explain_the_receipt_provenance_boundary() -> None:
    readme = (ROOT / "demo" / "README.md").read_text(encoding="utf-8")
    assert "NEUROCAD_SOURCE_REVISION" in readme
    assert "does not validate a release" in readme
    assert "user_supplied_unverified" in readme
