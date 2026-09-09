"""Network-free POSIX installer failure injection; real wheel smoke runs in CI."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.name == "nt" or shutil.which("sh") is None, reason="POSIX installer; Windows uses venv commands")
ROOT = Path(__file__).resolve().parents[1]
FAKE_PYTHON = '''
import os
import shutil
import sys
from pathlib import Path

if sys.argv[1:3] == ["-m", "venv"]:
    bindir = Path(sys.argv[3]) / "bin"
    bindir.mkdir()
    shutil.copy2(__file__, bindir / "python")
elif sys.argv[1:3] == ["-m", "pip"] and "install" in sys.argv:
    if os.environ.get("FAIL_INSTALL"):
        sys.exit(1)
    version = os.environ.get("FAKE_VERSION", "0.5.0a6")
    body = "#!/bin/sh\\ncase \\"$1\\" in\\n--version) echo 'NeuroCAD " + version + "';;\\ndoctor) exit "
    body += os.environ.get("FAIL_DOCTOR", "0") + ";;\\nesac\\n"
    for name in ("neurocad", "text-to-cad"):
        path = Path(__file__).parent / name
        path.write_text(body)
        path.chmod(0o755)
'''


def _environment(tmp_path: Path) -> dict[str, str]:
    fake = tmp_path / "fake-python"
    fake.write_text(f"#!{sys.executable}\n" + FAKE_PYTHON)
    fake.chmod(0o755)
    return {
        **os.environ, "PYTHON_BIN": str(fake), "NEUROCAD_PACKAGE": "local-test-wheel",
        "NEUROCAD_HOME": str(tmp_path / "install root"), "NEUROCAD_BIN_DIR": str(tmp_path / "bin dir"),
        "NEUROCAD_REF": "v0.5.0a6",
    }


def _run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["sh", str(ROOT / "install.sh")], env=env, text=True, capture_output=True, timeout=20, check=False)


def test_successful_upgrade_keeps_old_environment(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    first = _run(env)
    assert first.returncode == 0, first.stderr
    launcher = Path(env["NEUROCAD_BIN_DIR"]) / "neurocad"
    previous = launcher.resolve()
    second = _run(env)
    assert second.returncode == 0, second.stderr
    assert launcher.resolve() != previous
    assert previous.is_file()
    assert not (Path(env["NEUROCAD_HOME"]) / ".install-lock").exists()


@pytest.mark.parametrize("failure", [{"FAIL_INSTALL": "1"}, {"FAIL_DOCTOR": "1"}, {"FAKE_VERSION": "9.9.9"}])
def test_failed_upgrade_leaves_launchers_and_existing_environment_unchanged(tmp_path: Path, failure: dict) -> None:
    env = _environment(tmp_path)
    assert _run(env).returncode == 0
    launcher = Path(env["NEUROCAD_BIN_DIR"]) / "neurocad"
    previous = launcher.resolve()
    failed = _run({**env, **failure})
    assert failed.returncode != 0
    assert launcher.resolve() == previous and previous.is_file()
    assert len(list((Path(env["NEUROCAD_HOME"]) / "releases").iterdir())) == 1


def test_installer_refuses_unrelated_executable(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    launcher = Path(env["NEUROCAD_BIN_DIR"]) / "neurocad"
    launcher.parent.mkdir()
    launcher.write_text("user-owned tool")
    failed = _run(env)
    assert failed.returncode != 0
    assert "Refusing to replace" in failed.stderr
    assert launcher.read_text(encoding="utf-8") == "user-owned tool"
