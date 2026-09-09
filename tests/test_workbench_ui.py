"""Run the shipped script, not a duplicate implementation, against async races."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from core.workbench import HTML


@pytest.mark.skipif(shutil.which("node") is None, reason="Node required for shipped browser-script tests")
def test_workbench_project_and_request_lifecycle() -> None:
    script = re.search(r'<script nonce="__NONCE__">(.*?)</script>', HTML, re.DOTALL)
    assert script is not None
    harness = Path(__file__).with_name("workbench_contract.cjs").read_text(encoding="utf-8")
    result = subprocess.run(
        ["node", "-e", harness],
        input=json.dumps(script.group(1)),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
