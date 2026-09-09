# Novelty audit

## Verdict

No algorithmic or model novelty is established. The contribution is a bounded
systems/reproducibility case study. Typed ASTs, schemas, unit normalization, CSG,
OpenSCAD, program validation, and retrieval controls are established ideas.

## Current overlap

The field now contains substantially broader learned systems and datasets:
CAD-Llama and CADCrafter (CVPR 2025), Pointer-CAD, CADFS, and CADSketcher (CVPR
2026), plus 2026 work on Text2CAD-Bench and high-fidelity BREP/program grounding.
CADFS alone reports roughly 450k real-world models and 15 modeling operations;
Pointer-CAD integrates BREP entity selection. NeuroCAD's synthetic seven-family
grammar and CSG/STL output do not compete with those representation or benchmark
claims.

## Contribution classification

- Mathematical: not novel.
- Algorithmic: not novel.
- Novel combination: modest engineering integration only.
- Benchmark: controlled regression suite, not a community benchmark.
- Systems: strongest aspect; fail-closed stages, raw records, and provenance gates.
- Implementation: useful bounded compiler and enclosure workflow.

Claims of general text-to-CAD, state of the art, BREP/STEP, learned reasoning, or
manufacturing readiness must be removed or prohibited. See `literature/` for the
source matrix and the manuscript references.
