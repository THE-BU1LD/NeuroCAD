from __future__ import annotations

import re
from pathlib import Path

import neurocad_cli

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_release_version_has_one_source_value_across_metadata_and_cli() -> None:
    match = re.search(r'^version = "([^"]+)"$', _read("pyproject.toml"), flags=re.MULTILINE)
    assert match is not None
    assert match.group(1) == neurocad_cli.__version__


def test_supported_distribution_excludes_legacy_root_modules() -> None:
    metadata = _read("pyproject.toml")
    assert 'py-modules = ["neurocad_cli", "text_to_cad", "text_to_openscad"]' in metadata
    assert 'include = ["core*"]' in metadata
    assert 'numpy>=1.26,<3' in metadata
    assert "cad_intelligence_core_allinone" not in metadata
    assert "cad_master_kernel_legacy_broken" not in metadata


def test_ci_and_release_enforce_complete_quality_and_artifact_gates() -> None:
    ci = _read(".github/workflows/ci.yml")
    release = _read(".github/workflows/release.yml")
    guarded_helpers = (
        "surfaces.py",
        "vector_fields_engine.py",
        "pipeline_stage.py",
        "exceptions.py",
        "thinking_engine.py",
    )
    for helper in guarded_helpers:
        assert helper in ci
        assert helper in release
    for gate in ("pytest", "ruff check", "mypy", "pip_audit", "bandit", "compileall"):
        assert gate in ci
        assert gate in release
    assert "Fresh source-distribution install smoke test" in ci
    assert 'test "v$package_version" = "$GITHUB_REF_NAME"' in release
    assert 'git merge-base --is-ancestor "$GITHUB_SHA" origin/main' in release
    assert "sha256sum -c SHA256SUMS" in release
    assert "RELEASE_PROVENANCE.json" in release
    assert "research_manifest_sha256" in release
    assert "installed_version" in release
    assert 'python -m build --no-isolation --outdir "$release_dist"' in release
    for workflow in (ci, release):
        assert "neurocad enclosure interpret" in workflow
        assert "neurocad integrations export" in workflow
        assert "neurocad integrations verify" in workflow
        assert "neurocad integrations kicad-extract --help" in workflow


def test_workflows_and_quality_tools_are_version_pinned() -> None:
    workflows = "\n".join(path.read_text(encoding="utf-8") for path in sorted((ROOT / ".github/workflows").glob("*.yml")))
    action_references = re.findall(r"uses:\s*(actions/[^@\s]+)@([^\s#]+)", workflows)
    assert action_references
    assert all(re.fullmatch(r"[0-9a-f]{40}", revision) for _, revision in action_references)
    assert "-latest" not in workflows
    for runtime in ('"3.10.21"', '"3.11.16"', '"3.12.14"'):
        assert runtime in workflows
    assert 'pip==26.2.1' in workflows

    metadata = _read("pyproject.toml")
    for requirement in (
        'setuptools==83.0.0',
        'build==1.6.0',
        'mypy==1.18.2',
        'pytest==9.1.1',
        'ruff==0.16.5',
        'bandit==1.9.4',
        'pip-audit==2.10.1',
    ):
        assert requirement in metadata
    assert "setuptools==83.0.0" in _read("requirements-research.lock")
    assert "setuptools==83.0.0" in _read("requirements-research.in")
    assert "--hash=sha256:" in _read("requirements-research.lock")
    assert "--require-hashes" in _read("scripts/reproduce_research.sh")
    assert "--require-hashes" in workflows


def test_reproduction_is_fresh_non_resuming_and_provenance_checked() -> None:
    script = _read("scripts/reproduce_research.sh")
    assert "EXPECTED_PYTHON_VERSION=3.12.14" in script
    assert "mktemp -d" in script
    assert "Research output must not already exist" in script
    assert "Refusing to overwrite the canonical frozen research run" in script
    assert "force_recompile=True" in script
    assert 'config["force_recompile"] is True' in script
    assert 'kernel["resumed_verified_samples"] == 0' in script
    assert 'manifest["provenance"]["source"]["sha256"]' in script
    assert "NEUROCAD_REPRO_ENV" not in script


def test_source_distribution_manifest_contains_referenced_protocols_and_release_docs() -> None:
    manifest = _read("MANIFEST.in")
    assert "recursive-include core *.py" in manifest
    assert "include research/VERICODEGEN_2026_PROTOCOL.md" in manifest
    assert "recursive-include docs *.md" in manifest
    assert "prune legacy" in manifest
    assert "include requirements-research.in" in manifest


def test_legacy_fake_step_export_is_hard_disabled() -> None:
    legacy_source = _read("legacy/python/cad_intelligence_core_allinone.py")
    fake_step_marker = "Mesh " + "place" + "holder STEP"
    assert fake_step_marker not in legacy_source
    assert "STEP export is unsupported" in legacy_source


def test_disconnected_root_experiments_are_isolated_in_the_legacy_archive() -> None:
    supported_root_modules = {
        "exceptions.py",
        "neurocad_cli.py",
        "pipeline_stage.py",
        "surfaces.py",
        "text_to_cad.py",
        "text_to_openscad.py",
        "thinking_engine.py",
        "vector_fields_engine.py",
    }
    assert {path.name for path in ROOT.glob("*.py")} == supported_root_modules
    assert (ROOT / "legacy/python/cad_master_kernel_legacy_broken.py").is_file()
    assert (ROOT / "legacy/generated/round3_output.step").is_file()
    assert "legacy" not in _read("pyproject.toml")


def test_supported_source_contains_no_fake_step_or_implementation_markers() -> None:
    supported_paths = [ROOT / "neurocad_cli.py", ROOT / "text_to_cad.py", ROOT / "text_to_openscad.py"]
    supported_paths.extend(sorted((ROOT / "core").rglob("*.py")))
    forbidden = (
        "Mesh " + "place" + "holder STEP",
        "Not" + "ImplementedError",
        "TO" + "DO",
        "FIX" + "ME",
    )
    violations = {
        str(path.relative_to(ROOT)): marker
        for path in supported_paths
        for marker in forbidden
        if marker in path.read_text(encoding="utf-8")
    }
    assert violations == {}


def test_historical_negative_results_remain_explicit() -> None:
    truth = _read("NEUROCAD_TRUTH.md")
    historical = _read("audits/HISTORICAL_TRUTH.md")
    assert "not STEP export" in truth
    assert "REFUTED" in historical
    assert "falsified" in truth.lower()


def test_research_claim_boundary_rejects_a_learned_model_claim() -> None:
    report = _read("MODEL_CARD.md")
    maintained_model_note = _read("model/README.md")
    assert "no trained model" in report.lower()
    assert "no learned model" in maintained_model_note.lower()


def test_truth_documents_do_not_regress_to_stale_release_claims() -> None:
    project_truth = _read("PROJECT_TRUTH.md")
    completion = _read("NEUROCAD_COMPLETION_REPORT.md")
    evidence = _read("docs/PUBLIC_ALPHA_EVIDENCE_LEDGER.md")
    truth = _read("NEUROCAD_TRUTH.md")

    combined = f"{project_truth}\n{completion}\n{evidence}\n{truth}"
    assert ("pending" + " final verification") not in combined
    assert "152 " + "passed" not in combined
    assert "163/163 " + "passed" not in combined
    assert "167/167 " + "passed" not in combined
    assert "762da4a99fab5f5e690e3d23d6766e0535511b2157827d9da84ce02f8fbd0e12" not in combined
    assert "c9178a60fbee421575116f34feebccf75a3756dc6a5cd10a7c1c5953cad577f5" not in combined
    assert "legacy file writes text " + "labelled" not in combined
    assert "hard-disabled" in combined
    assert "RELEASE_PROVENANCE.json" in evidence
    assert "Current status: **PENDING**" in evidence
