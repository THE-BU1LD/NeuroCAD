# NeuroCAD

NeuroCAD is a strict prompt-to-parametric-program tool for fully dimensioned
plates, rectangular boxes/enclosures, and basic box, cylinder, and sphere
primitives. Prompts compile through a versioned, schema-validated internal
representation to deterministic OpenSCAD. Every exported length is expressed
in millimetres.

NeuroCAD is an alpha design aid. Generated parts must still be reviewed by a
qualified person before fabrication. It does not calculate load capacity,
material behaviour, regulatory compliance, or safety. Its disclosed tolerance
and coupon-calibration estimates are design aids, not manufacturing guarantees.

The primary product workflow is now a typed electronics-enclosure pipeline:
auditable semicolon-delimited intent, editable project revisions, manufacturing
preflight, deterministic body/lid IR and SCAD, request-level STL verification,
printer-coupon calibration, and explicit file handoffs to external CAD and
slicer applications. See `docs/PRODUCT_WORKFLOW.md` for the exact contract.

## Install

The public bootstrap installer will be usable after this repository is public:

```bash
curl -fsSL https://raw.githubusercontent.com/THE-BU1LD/NeuroCAD/main/install.sh | sh
```

For development:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
neurocad doctor
```

OpenSCAD is optional for SCAD and JSON output. It is required for compiled
validation and STL export.

## Supported prompts

State all overall dimensions and all requested feature dimensions explicitly:

```text
a 120 x 80 x 4 mm plate with four 4 mm holes
a plate 120 mm wide 80 mm deep and 4 mm thick
a 100 x 80 x 20 mm enclosure with 2 mm wall thickness
a 100 x 60 x 4 mm plate with two 12 x 5 mm slots
a cylinder with radius 20 mm and height 50 mm
a 40 x 30 x 20 mm box
```

Dimension sequences may use `x`, `×`, or `by`. Supported units are millimetres,
centimetres, metres, and inches; they are normalized to millimetres.

When four holes are requested, they are placed symmetrically near the four
corners. Other counts use deterministic symmetric layouts. Hole diameter and
slot dimensions are mandatory.

## Commands

Validate intent without writing a file:

```bash
neurocad validate "a 120 x 80 x 4 mm plate with four 4 mm holes"
```

Return a machine-readable design and validation manifest:

```bash
neurocad validate "a 120 x 80 x 4 mm plate with four 4 mm holes" --json
```

Generate editable OpenSCAD and a manifest:

```bash
neurocad create \
  "a 120 x 80 x 4 mm plate with four 4 mm holes" \
  -o plate.scad --manifest plate.json
```

Compile and verify a watertight STL (requires `openscad`):

```bash
neurocad export \
  "a 120 x 80 x 4 mm plate with four 4 mm holes" \
  --format stl -o plate.stl --manifest plate.json

neurocad validate \
  "a 120 x 80 x 4 mm plate with four 4 mm holes" \
  --compile
```

Export only the JSON manifest:

```bash
neurocad export \
  "a 120 x 80 x 4 mm plate with four 4 mm holes" \
  --format json -o plate.json
```

Create and compile the canonical editable IR:

```bash
neurocad ir "a 120 x 80 x 4 mm plate with four 4 mm holes" -o plate.ncad.json
neurocad compile plate.ncad.json --format scad -o plate.scad
neurocad evaluate --ir plate.ncad.json
```

Run the deterministic 48-task product regression benchmark:

```bash
neurocad benchmark
```

Reproduce the full controlled research suite (requires CPython 3.12.14 and
OpenSCAD for all 240 kernel cases):

```bash
PYTHON_BIN=python3.12 scripts/reproduce_research.sh
```

The script creates a fresh virtual environment and a new, non-resuming output
directory. It never rewrites the retained historical
`research/runs/NC-RUN-2026-09-03-FULL/` directory. A successful run generates a
new dataset, 1,000 typed IR programs, malformed-input records, ablations,
paired statistics, OpenSCAD/STL artifacts, kernel renders, plots, logs,
deterministic scientific hashes, and a separate runtime receipt. See
`REPRODUCIBILITY.md`, `QUESTION.md`,
`paper/NEUROCAD_CONTROLLED_COMPILER_PAPER.md`, and `audits/CLAIM_LEDGER.md`.

Launch the local workbench, which uses the same parser, IR, validator, and
exporter as the CLI:

```bash
neurocad demo
```

The default page is now the typed electronics-enclosure workbench. It shows the
interpreted specification, body/lid preview, canonical programs, OpenSCAD,
validation findings, and fabrication preflight together.

Create, revise, preflight, and compile a reviewable enclosure project:

```bash
neurocad enclosure interpret \
  "80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm; rectangular cutout 12 x 7 mm on front at 0 x 8 mm for USB-C" \
  --project-id controller --project-output controller-r1.ncad.json
neurocad enclosure edit controller-r1.ncad.json \
  --instruction "set wall thickness to 2.4 mm" -o controller-r2.ncad.json
neurocad enclosure preflight controller-r2.ncad.json
neurocad enclosure build controller-r2.ncad.json --output-dir controller-r2 --stl
neurocad enclosure verify controller-r2
```

`enclosure verify` independently checks the manifest schema, artifact inventory,
hashes, project metadata, regenerated canonical IR and OpenSCAD, fabrication
preflight, and current request-level mesh evidence for compiled bundles.

Inspect application support and create a verified file handoff:

```bash
neurocad integrations list
neurocad integrations export controller-r2.ncad.json \
  --output-dir controller-exchange --stl --manifest controller-apps.json
neurocad integrations verify controller-exchange
neurocad integrations handoff controller-exchange PrusaSlicer \
  -o controller-prusaslicer-handoff.json
```

The handoff command never launches an application or claims an import, slice,
or upload occurred. OpenSCAD is a verified compiler integration when installed;
Fusion, Onshape, FreeCAD, Blender, PrusaSlicer, OrcaSlicer, Bambu Studio, and
Cura currently use reviewed SCAD/STL file-exchange contracts. KiCad uses a
strict, hash-bound board-extraction receipt.

Apply a completed KiCad receipt only after binding it to the exact source board:

```bash
neurocad integrations kicad-request controller.kicad_pcb -o kicad-request.json
# A reviewed external extractor produces kicad-draft.json.
neurocad integrations kicad-bind kicad-draft.json \
  --source-board controller.kicad_pcb -o kicad-completed.json
neurocad integrations kicad-apply controller-r2.ncad.json kicad-completed.json \
  --source-board controller.kicad_pcb -o controller-r3.ncad.json
```

This adds the board envelope, height, and mounting-hole coordinates as an
audited project revision. It does not guess connector cutouts or standoffs;
those unresolved design decisions are returned for review.

Unsupported, ambiguous, or incompletely dimensioned prompts exit nonzero and
list the missing requirements. NeuroCAD does not silently approve default
geometry for fabrication.

## Current boundaries

Not implemented:

- STEP/BREP export or sketch constraint solving;
- slide lids, hinges, snap fits, threads, or true 3D edge fillets;
- native Fusion/Onshape/FreeCAD/Blender documents or native slicer projects;
- structural, thermal, fluid, electromagnetic, or material simulation;
- production aircraft, vehicle, motor, furniture, medical, or safety-critical design;
- arbitrary natural-language CAD outside the documented grammar.

Implemented enclosure features include open-top, screw, and friction-lid
designs, rectangular/circular cutouts, vent grids, PCB envelopes, M2/M2.5/M3/M4
standoffs, named manufacturing assumptions, analytical tolerance helpers, and
evidence-bounded coupon calibration. These are design aids, not simulation or
manufacturing certification.
Use `docs/PHYSICAL_VALIDATION_PROTOCOL.md` to collect the physical evidence
required before describing an enclosure as fit-checked.

## Evidence and research boundaries

The maintained engineering suite is under `tests/`; root-level historical test
scripts are retained as research artifacts and are not collected by the product
test gate. The current benchmark measures deterministic engineering coverage,
not learned intelligence or causal scientific evidence. The historical
typed-parser mechanism claim remains falsified. See `NEUROCAD_TRUTH.md`,
`NEUROCAD_RESEARCH_REPORT.md`, `audits/HISTORICAL_TRUTH.md`, and
`NEUROCAD_COMPLETION_REPORT.md`.

The repository contains historical research experiments that are not included
in the `neurocad-research` wheel and are not part of the supported product API.

## Release gates

CI compiles the shipped sources, runs the maintained suite, exercises semantic
failure and success cases, builds a wheel and source distribution, installs the
wheel into a fresh environment, performs SCAD and STL smoke tests, and scans Git
history for high-confidence secret patterns.

## License

MIT. See `LICENSE`.
