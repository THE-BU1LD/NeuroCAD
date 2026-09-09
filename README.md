# NeuroCAD

NeuroCAD is a strict prompt-to-parametric-program tool for fully dimensioned
plates, rectangular boxes/enclosures, and basic box, cylinder, and sphere
primitives. Prompts compile through a versioned, schema-validated internal
representation to deterministic OpenSCAD. Every exported length is expressed
in millimetres.

Research status: the maintained compiler is engineering-verified, while the
conference evidence is **partial**. The retained full benchmark is synthetic and
historically source-unbound; it must not be read as external validation. Start
with `RESEARCH_TRUTH.md`, `audit/REPOSITORY_MAP.md`, and
`audit/CONFERENCE_READINESS_CHECKLIST.md` for the current evidence boundary.

NeuroCAD is an alpha design aid. Generated parts must still be reviewed by a
qualified person before fabrication. It does not calculate load capacity,
material behaviour, regulatory compliance, or safety. Its disclosed tolerance
and coupon-calibration estimates are design aids, not manufacturing guarantees.

The primary product workflow is now a typed electronics-enclosure pipeline:
auditable semicolon-delimited intent, editable project revisions, manufacturing
preflight, deterministic body/lid IR and SCAD, request-level STL verification,
printer-coupon calibration, and explicit file handoffs to external CAD and
slicer applications. See `docs/PRODUCT_WORKFLOW.md` for the exact contract.

## Install and first prompt

From this source checkout, the currently verified installation path is:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
neurocad doctor
neurocad create "a 120 x 80 x 4 mm plate with four 4 mm holes" \
  -o plate.scad --manifest plate.json
```

For a persistent macOS/Linux command from this checkout:

```bash
NEUROCAD_PACKAGE="$PWD" sh ./install.sh
```

The installer stages and checks a fresh environment before publishing launchers;
failed installation or health checks leave existing launchers unchanged. Previous
environments are retained for rollback. It refuses unrelated existing executables.
Windows, private GitHub access, OpenSCAD setup, and first-use recipes are in
[Quick start](docs/QUICKSTART.md).

The repo is currently private and `v0.5.0a6` is not published. The public
anonymous-install gate is **open**: a public curl command is not yet usable.

For development, install the pinned test tools:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
neurocad doctor
```

`install.sh` defaults to the immutable `v0.5.0a6` tag. Release verification can
exercise it without GitHub by setting `NEUROCAD_PACKAGE` to an exact local wheel;
this override is not a substitute for the pending anonymous-install gate.

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

Analyze an existing STL's topology, or compute a correlated tolerance stack:

```bash
neurocad topology plate.stl --require-closed-manifold -o topology.json
neurocad tolerance docs/examples/tolerance.json -o tolerance-report.json
```

Topology reports F2 Betti numbers, Euler characteristic, boundary loops,
orientability and genus where applicable. Kernel verification also rejects
singular vertex links. These are connectivity checks, not self-intersection,
surface-equivalence, or physical-fit proofs. See [Mathematics](docs/MATHEMATICS.md)
for equations, assumptions, numerical/resource limits, and reference tests.

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
neurocad benchmark \
  --dataset neurocad-benchmark.jsonl \
  --output neurocad-benchmark-results.json
```

Run the immutable audit-authored development challenge (this is not independent
confirmatory evidence):

```bash
python -m core.challenge \
  research/benchmarks/neurocad_prompt_challenge_v1.jsonl \
  /tmp/neurocad-prompt-challenge-results.json
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

To produce a deterministic structural-generation report (not kernel verification
or physical certification), use `neurocad verify "a 120 x 80 x 4 mm plate with
four 4 mm holes" --json-output verification.json --scad-output design.scad`.
Output paths must be distinct and new unless `--force` is supplied. Unlike the
older public-alpha examples, all dimensions must be explicit; unsupported inputs
produce an invalid report and no SCAD artifact.

Launch the local workbench, which uses the same parser, IR, validator, and
exporter as the CLI:

```bash
neurocad demo
```

The default page is now the typed electronics-enclosure workbench. It shows the
interpreted specification, body/lid preview, canonical programs, OpenSCAD,
validation findings, and fabrication preflight together. The server binds to
loopback and validates browser Host headers by default. Binding it to another
interface requires `--allow-remote` and exposes an unauthenticated service; put
an authenticated reverse proxy in front of it rather than exposing it directly.
The demo caps active request workers at eight and applies a 10-second socket-idle
timeout; excess connections are closed without creating more workers. Requests
must have one Content-Length and cannot use Transfer-Encoding. These limits do
not make the demo an authenticated or internet-hardened hosting service. Editing
input invalidates both displayed output and responses still in flight.

The fast preview is schematic, not kernel verification. Use **Compile verified
mesh** to run the installed OpenSCAD kernel, check mesh topology and enclosure
features, inspect the actual body/lid triangles, and download the verified STL
bytes. This does not verify physical fit. Compilation is serialized and limited
to 30 seconds per part; previews are limited to 20,000 faces. Downloads expire
after ten minutes and may be evicted earlier from the bounded in-memory cache;
recompile if a download expires. No persistent cloud storage is provided.

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
Cura currently use reviewed SCAD/STL file-exchange contracts. KiCad supports a
strict, hash-bound bounded parser for rectangular boards, plus IPC/CLI receipts
for boards outside that subset.

For a rectangular board, provide reviewed connector/height facts in
`mechanical-review.json`, then extract and apply a receipt bound to the exact
source bytes:

```bash
neurocad integrations kicad-extract controller.kicad_pcb \
  --review mechanical-review.json -o kicad-completed.json
neurocad integrations kicad-inspect kicad-completed.json \
  --source-board controller.kicad_pcb
neurocad integrations kicad-apply controller-r2.ncad.json kicad-completed.json \
  --source-board controller.kicad_pcb -o controller-r3.ncad.json
```

The review JSON uses `neurocad-kicad-mechanical-review-v1`, must explicitly mark
the connector inventory and height measurement complete, and supplies
`max_component_height_mm` plus a `connectors` array. The bounded parser accepts
one axis-aligned rectangular Edge.Cuts outline and round NPTH pads only inside
footprints explicitly named as mounting holes. Other geometry fails closed and
uses the existing reviewed IPC/CLI draft-and-bind route.

This adds the board envelope, height, and mounting-hole coordinates as an
audited project revision. It does not guess connector cutouts or standoffs;
those unresolved design decisions are returned for review.

Unsupported, ambiguous, or incompletely dimensioned prompts exit nonzero and
list the missing requirements. NeuroCAD does not silently approve default
geometry for fabrication.

Artifact-producing commands refuse existing output paths by default. Pass
`--force` only when replacement is intentional and the existing file is no
longer needed.

## Troubleshooting

- `OpenSCAD is required`: install OpenSCAD and confirm `openscad --version` is
  available on `PATH`; SCAD and JSON generation work without it.
- `unsupported domain` or `all overall dimensions must be stated`: rewrite the
  prompt using one of the exact supported forms above and specify every
  dimension and feature size.
- `already exists`: choose a new output path, or use `--force` after reviewing
  the file that will be replaced.
- `permission denied`: write into a user-owned directory and verify its parent
  is writable; do not run NeuroCAD as root to work around ownership problems.
- Enclosure interpretation reports unmatched clauses: use semicolons and the
  clause grammar in `docs/PRODUCT_WORKFLOW.md`.

Portal environment, OAuth redirect, and migration-ledger troubleshooting lives
with the portal deployment runbook rather than this package.

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
