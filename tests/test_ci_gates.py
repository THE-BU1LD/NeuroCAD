"""Release gates must remain reachable with patch-pinned Python versions."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("step", [
    "Type-check maintained product and research tooling",
    "Audit dependencies and supported source",
    "Fresh source-distribution install smoke test",
    "Upload distributions",
])
def test_python_release_gates_match_an_actual_matrix_entry(step: str) -> None:
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    matrix = re.search(r'python-version: \[([^\]]+)\]', workflow)
    assert matrix is not None
    versions = re.findall(r'"([0-9.]+)"', matrix.group(1))
    condition = re.search(rf"- name: {re.escape(step)}\n\s+if: ([^\n]+)", workflow)
    assert condition is not None
    prefix = re.fullmatch(r"startsWith\(matrix.python-version, '([0-9.]+)'\)", condition.group(1))
    assert prefix is not None, "Use a patch-version-independent release gate"
    assert sum(version.startswith(prefix.group(1)) for version in versions) == 1


@pytest.mark.parametrize("workflow", ["ci.yml", "release.yml"])
def test_required_tests_cannot_be_silently_skipped(workflow: str, tmp_path: Path) -> None:
    text = (Path(__file__).resolve().parents[1] / ".github/workflows" / workflow).read_text(encoding="utf-8")
    assert "if [ -d tests ]" not in text
    assert "python -m pytest -q tests" in text
    # Execute the actual prerequisite sequence, not a copy of its behavior.
    blocks = re.findall(
        r"test -s tests/test_workbench_ui.py\n\s+test -s tests/workbench_contract.cjs\n\s+node --version", text
    )
    assert len(blocks) == (2 if workflow == "ci.yml" else 1)
    shell = shutil.which("bash")
    if shell is None:
        pytest.skip("workflow shell is unavailable")
    command = "set -e\n" + "\n".join(line.strip() for line in blocks[0].splitlines())
    # Missing sources must fail even on a machine with Node installed.
    assert subprocess.run([shell, "-c", command], cwd=tmp_path, capture_output=True, check=False).returncode != 0
    (tmp_path / "tests").mkdir()
    for name in ("test_workbench_ui.py", "workbench_contract.cjs"):
        (tmp_path / "tests" / name).write_text("required fixture")
    assert subprocess.run(
        [shell, "-c", command], cwd=tmp_path, env={"PATH": str(tmp_path)}, capture_output=True, check=False
    ).returncode != 0
    if shutil.which("node"):
        assert subprocess.run([shell, "-c", command], cwd=tmp_path, capture_output=True, check=False).returncode == 0


def test_real_browser_lane_is_required_and_retains_failure_evidence() -> None:
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "browser: [chromium, firefox, webkit]" in workflow
    assert "playwright install --with-deps ${{ matrix.browser }}" in workflow
    assert "tests/browser/run_workbench.py --browser ${{ matrix.browser }} --require-kernel" in workflow
    lane = workflow.split("  workbench-browser:", 1)[1]
    assert "continue-on-error" not in lane
    assert "if: always()" in lane
    for revision in re.findall(r"uses: actions/[^@]+@([^ ]+)", workflow):
        assert re.fullmatch("[a-f0-9]{40}", revision), "Actions must retain reviewed immutable pins"


def test_tag_publication_requires_browsers_and_extracted_source_tests() -> None:
    root = Path(__file__).resolve().parents[1]
    release = (root / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "  release:\n    needs: workbench-browser\n" in release
    assert "browser: [chromium, firefox, webkit]" in release
    assert "--require-kernel" in release
    assert "continue-on-error" not in release
    for name in ("ci.yml", "release.yml"):
        workflow = (root / ".github/workflows" / name).read_text(encoding="utf-8")
        assert 'tar -xzf "${sdist_files[0]}" -C "$source_test_dir"' in workflow
        assert 'cd "${source_roots[0]}"' in workflow


def test_all_maintained_scripts_are_checked_and_test_failures_are_retained() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("ci.yml", "release.yml"):
        workflow = (root / ".github/workflows" / name).read_text(encoding="utf-8")
        for command in ("ruff check", "mypy", "bandit -q -r"):
            assert f"python -m {command} core research/vericodegen scripts " in workflow
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert '--junitxml="${{ runner.temp }}/neurocad-tests.xml"' in workflow
    assert "Retain test results including failures\n        if: always()" in workflow


@pytest.mark.parametrize("tag,prerelease", [("v0.5.0a6", True), ("v1.0.0rc1", True), ("v1.0.0", False)])
def test_release_command_labels_alpha_and_rc_without_marking_them_latest(tag: str, prerelease: bool, tmp_path: Path) -> None:
    import json
    import os
    import sys

    shell = shutil.which("bash")
    if shell is None:
        pytest.skip("workflow shell is unavailable")
    text = (Path(__file__).resolve().parents[1] / ".github/workflows/release.yml").read_text(encoding="utf-8")
    block = text.split("      - name: Create GitHub release\n", 1)[1].split("        run: |\n", 1)[1]
    command = "\n".join(line.removeprefix("          ") for line in block.splitlines())
    # Execute the workflow's shell with a recording gh function; no release exists
    # and no network action occurs. Version parsing uses this test environment.
    recorder = 'import json,sys; print(json.dumps(sys.argv[1:]))'
    import shlex
    prefix = f"python() {{ {shlex.quote(sys.executable)} \"$@\"; }}\ngh() {{ python -c {shlex.quote(recorder)} \"$@\"; }}\n"
    result = subprocess.run(
        [shell, "-c", prefix + command], capture_output=True, text=True, check=False,
        env={**os.environ, "GITHUB_REF_NAME": tag, "RUNNER_TEMP": str(tmp_path)},
    )
    assert result.returncode == 0, result.stderr
    arguments = json.loads(result.stdout)
    assert arguments[:3] == ["release", "create", tag]
    assert "--verify-tag" in arguments
    assert ("--prerelease" in arguments) is prerelease
    assert ("--latest=false" in arguments) is prerelease
