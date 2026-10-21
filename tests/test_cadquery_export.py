from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from core.cadquery_export import CADQUERY_EXPORT_VERSION, program_to_cadquery_python
from core.ir import CADProgram, Node, Primitive, Transform
from research.cadtestbench_v1 import prepare_generations


def _program() -> CADProgram:
    return CADProgram(
        title="external benchmark development fixture",
        nodes=(
            Node(
                "body",
                primitive=Primitive("box", {"size": [40.0, 30.0, 8.0]}),
            ),
            Node(
                "hole",
                primitive=Primitive("cylinder", {"radius": 3.0, "height": 12.0}),
                transform=Transform(translate=(5.0, 0.0, 0.0)),
            ),
            Node(
                "result",
                composition="difference",
                children=("body", "hole"),
            ),
        ),
        roots=("result",),
    )


def test_cadquery_source_is_deterministic_parseable_and_uses_real_csg() -> None:
    first = program_to_cadquery_python(_program())
    second = program_to_cadquery_python(_program())

    assert first == second
    assert first.startswith(f"# {CADQUERY_EXPORT_VERSION}\n")
    assert ".box(40.0, 30.0, 8.0, centered=(True, True, True))" in first
    assert ".circle(3.0).extrude(6.0, both=True)" in first
    assert ".translate((5.0, 0.0, 0.0))" in first
    assert ".cut(node_0001)" in first
    assert "final_result = create_cad()" in first
    assert "cq.exporters.export" not in first
    ast.parse(first)


@pytest.mark.parametrize(
    ("kind", "parameters", "fragment"),
    [
        ("rounded_box", {"size": [10.0, 8.0, 6.0], "radius": 1.0}, ".edges().fillet(1.0)"),
        ("sphere", {"radius": 2.0}, '.sphere(2.0)'),
        ("cone", {"r1": 3.0, "r2": 1.0, "height": 5.0}, "cq.Solid.makeCone(3.0, 1.0, 5.0"),
        ("torus", {"major_radius": 5.0, "minor_radius": 1.0}, "cq.Solid.makeTorus(5.0, 1.0)"),
    ],
)
def test_cadquery_source_covers_every_canonical_primitive(
    kind: str,
    parameters: dict[str, object],
    fragment: str,
) -> None:
    program = CADProgram(
        title=kind,
        nodes=(Node("body", primitive=Primitive(kind, parameters)),),
        roots=("body",),
    )
    source = program_to_cadquery_python(program)
    assert fragment in source
    ast.parse(source)


def test_cadquery_source_refuses_non_rigid_scale() -> None:
    program = CADProgram(
        title="scaled box",
        nodes=(
            Node(
                "body",
                primitive=Primitive("box", {"size": [10.0, 10.0, 10.0]}),
                transform=Transform(scale=(2.0, 1.0, 1.0)),
            ),
        ),
        roots=("body",),
    )
    with pytest.raises(ValueError, match="refuses non-rigid transforms"):
        program_to_cadquery_python(program)


def test_cadquery_source_refuses_invalid_program() -> None:
    program = CADProgram(
        title="invalid",
        nodes=(Node("body", primitive=Primitive("sphere", {"radius": -1.0})),),
        roots=("body",),
    )
    with pytest.raises(ValueError, match="cannot export invalid canonical IR"):
        program_to_cadquery_python(program)


def test_external_benchmark_preparation_retains_acceptance_and_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset_root = tmp_path / "dataset"
    samples = dataset_root / "samples"
    samples.mkdir(parents=True)
    parquet = samples / "detailed.parquet"
    parquet.write_bytes(b"project-authored parquet placeholder")
    monkeypatch.setattr(
        prepare_generations,
        "_read_rows",
        lambda _: [
            {
                "sample_id": "accepted-1",
                "prompt": "Create a 10 x 20 x 3 mm plate.",
            },
            {
                "sample_id": "rejected-1",
                "prompt": "Make an ornate articulated clockwork assembly without dimensions.",
            },
        ],
    )

    output_root = tmp_path / "generations"
    manifest = prepare_generations.prepare_partition(
        dataset_root=dataset_root,
        partition="detailed",
        output_root=output_root,
        expected_rows=2,
    )

    assert manifest["rows"] == 2
    assert manifest["accepted"] == 1
    assert manifest["rejected"] == 1
    assert manifest["outcomes_observed"] is False
    accepted = output_root / "detailed/generated_models/accepted-1/gpt_generated.py"
    rejected = output_root / "detailed/generated_models/rejected-1/gpt_generated.py"
    assert "final_result = create_cad()" in accepted.read_text(encoding="utf-8")
    assert "NEUROCAD_REJECTED" in rejected.read_text(encoding="utf-8")
    persisted = json.loads((output_root / "detailed/generation_manifest.json").read_text())
    assert persisted["records"] == manifest["records"]
