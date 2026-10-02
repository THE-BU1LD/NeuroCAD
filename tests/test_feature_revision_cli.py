from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from neurocad_cli import build_parser

EXAMPLES = Path(__file__).resolve().parents[1] / "docs/examples/c3d_revision"


def _revision_args(accepted: Path, output: Path, candidate: str = "candidate") -> list[str]:
    return [
        "feature", "revise", str(EXAMPLES / "baseline.ncad2.json"),
        str(EXAMPLES / f"{candidate}.ncad2.json"),
        "--baseline-bundle", str(accepted),
        "--baseline-requirements", str(EXAMPLES / "baseline.requirements.json"),
        "--baseline-bindings", str(EXAMPLES / "baseline.bindings.json"),
        "--candidate-requirements", str(EXAMPLES / f"{candidate}.requirements.json"),
        "--candidate-bindings", str(EXAMPLES / f"{candidate}.bindings.json"),
        "--output-dir", str(output),
    ]


def _run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "neurocad_cli", *arguments], capture_output=True, text=True, timeout=60, check=False)


def _hashes(path: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir() if p.is_file()}


@pytest.fixture
def accepted(tmp_path: Path) -> Path:
    pytest.importorskip("build123d")
    bundle = tmp_path / "accepted"
    result = _run([
        "feature", "build", str(EXAMPLES / "baseline.ncad2.json"),
        "--requirements", str(EXAMPLES / "baseline.requirements.json"),
        "--bindings", str(EXAMPLES / "baseline.bindings.json"),
        "--output-dir", str(bundle),
    ])
    assert result.returncode == 0, result.stderr
    return bundle


def test_revision_cli_publishes_real_roundtripped_bundle(accepted: Path, tmp_path: Path) -> None:
    before = _hashes(accepted)
    output = tmp_path / "revised"
    result = _run(_revision_args(accepted, output))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    evidence = payload["revision_integrity"]["evidence"]
    assert evidence["passed"]
    assert evidence["candidate_wall_thickness_mm"] == pytest.approx(3.0, abs=1e-6)
    assert evidence["external_boundary_equivalent"] and evidence["cutouts_equivalent"]
    assert evidence["candidate_inspection"]["solid_count"] == 1
    assert {"design.step", "build-receipt.json", "requirements.json",
            "requirement-bindings.json", "requirements-verification.json", "revision-integrity.json"} <= {p.name for p in output.iterdir()}
    assert json.loads((output / "revision-integrity.json").read_text(encoding="utf-8")) == payload["revision_integrity"]
    assert _hashes(accepted) == before


def test_revision_cli_rejects_40mm_without_publication(accepted: Path, tmp_path: Path) -> None:
    before = _hashes(accepted)
    output = tmp_path / "infeasible"
    result = _run(_revision_args(accepted, output, "infeasible"))
    assert result.returncode == 2
    assert "positive" in result.stderr
    assert not output.exists()
    assert _hashes(accepted) == before


def test_revision_cli_rejects_output_inside_baseline(accepted: Path) -> None:
    before = _hashes(accepted)
    output = accepted / "nested"
    result = _run(_revision_args(accepted, output))
    assert result.returncode == 2
    assert "outside the accepted baseline" in result.stderr
    assert not output.exists()
    assert _hashes(accepted) == before


def test_revision_cli_rejects_existing_output(accepted: Path, tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "keep.txt"
    marker.write_text("preserve me", encoding="utf-8")
    result = _run(_revision_args(accepted, output))
    assert result.returncode == 2
    assert "already exists" in result.stderr
    assert marker.read_text(encoding="utf-8") == "preserve me"


def test_revision_cli_rejects_tampered_baseline(accepted: Path, tmp_path: Path) -> None:
    step = accepted / "design.step"
    step.write_bytes(step.read_bytes() + b"tampered")
    before = _hashes(accepted)
    output = tmp_path / "tampered-revision"
    result = _run(_revision_args(accepted, output))
    assert result.returncode == 2
    assert "hash" in result.stderr
    assert not output.exists()
    assert _hashes(accepted) == before


def test_revision_cli_requires_build123d_without_fallback(tmp_path: Path, monkeypatch, capsys) -> None:
    from core import exact_backend

    def unavailable(identifier: str):
        assert identifier == "build123d"
        raise exact_backend.ExactBackendUnavailable("build123d unavailable: not installed")

    monkeypatch.setattr(exact_backend, "require_exact_backend", unavailable)
    args = build_parser().parse_args(_revision_args(tmp_path / "baseline", tmp_path / "new"))
    with pytest.raises(exact_backend.ExactBackendUnavailable, match="unavailable"):
        args.func(args)
    assert capsys.readouterr().out == ""
    assert not (tmp_path / "new").exists()


@pytest.mark.parametrize("flag", ["--linear-tolerance-mm", "--axis", "--side", "--edited-requirement-ids", "--force", "--backend"])
def test_revision_cli_exposes_no_contract_override(tmp_path: Path, flag: str) -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(_revision_args(tmp_path / "baseline", tmp_path / "new") + [flag, "anything"])
    assert exc.value.code == 2


def test_revision_cli_strictly_rejects_malformed_requirement(tmp_path: Path) -> None:
    arguments = _revision_args(tmp_path / "baseline", tmp_path / "new")
    malformed = tmp_path / "bad.json"
    malformed.write_text('{"source": NaN}', encoding="utf-8")
    arguments[arguments.index("--candidate-requirements") + 1] = str(malformed)
    result = _run(arguments)
    assert result.returncode == 2
    assert not (tmp_path / "new").exists()
