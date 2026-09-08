"""Release gates must remain reachable with patch-pinned Python versions."""

import re
from pathlib import Path

import pytest


@pytest.mark.parametrize("step", [
    "Type-check maintained product and research tooling",
    "Audit dependencies and supported source",
    "Fresh source-distribution install smoke test",
    "Upload distributions",
])
def test_python_release_gates_match_an_actual_matrix_entry(step: str) -> None:
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml").read_text()
    matrix = re.search(r'python-version: \[([^\]]+)\]', workflow)
    assert matrix is not None
    versions = re.findall(r'"([0-9.]+)"', matrix.group(1))
    condition = re.search(rf"- name: {re.escape(step)}\n\s+if: ([^\n]+)", workflow)
    assert condition is not None
    prefix = re.fullmatch(r"startsWith\(matrix.python-version, '([0-9.]+)'\)", condition.group(1))
    assert prefix is not None, "Use a patch-version-independent release gate"
    assert sum(version.startswith(prefix.group(1)) for version in versions) == 1
