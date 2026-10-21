from __future__ import annotations

from pathlib import Path

import pytest

from research.cadtestbench_v2 import prepare_generations


def test_v2_counts_frontend_exception_as_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset_root = tmp_path / "dataset"
    samples = dataset_root / "samples"
    samples.mkdir(parents=True)
    (samples / "abstract.parquet").write_bytes(b"pinned parquet fixture")
    monkeypatch.setattr(
        prepare_generations,
        "_read_rows",
        lambda _: [{"sample_id": "external-1", "prompt": "externally authored prompt"}],
    )
    monkeypatch.setattr(
        prepare_generations.TextToCAD,
        "build",
        lambda *_: (_ for _ in ()).throw(ValueError("unrepresentable external count")),
    )

    manifest = prepare_generations.prepare_partition(
        dataset_root=dataset_root,
        partition="abstract",
        output_root=tmp_path / "out",
        expected_rows=1,
    )

    assert manifest["rows"] == 1
    assert manifest["accepted"] == 0
    assert manifest["rejected"] == 1
    assert manifest["frontend_exceptions"] == 1
    source = tmp_path / "out/abstract/generated_models/external-1/gpt_generated.py"
    assert "NEUROCAD_FRONTEND_EXCEPTION: ValueError" in source.read_text(encoding="utf-8")
