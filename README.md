# NeuroCAD

NeuroCAD combines a persistent conversational concept planner with a strict
prompt-to-parametric-program compiler. Natural-language project revisions may be
planned by a local built-in planner, Ollama, or an OpenAI-compatible model. Every
accepted plan still compiles through a versioned, schema-validated internal
representation to deterministic OpenSCAD. Every exported length is expressed in
millimetres.

Research status: the maintained compiler is engineering-verified, while the
conference evidence is **partial**. The current full benchmark is source-bound,
non-resumed, and reproducible locally, but remains synthetic and must not be read
as independent external validation. Start
with `RESEARCH_TRUTH.md`, `audit/REPOSITORY_MAP.md`, and
`audit/CONFERENCE_READINESS_CHECKLIST.md` for the current evidence boundary.

NeuroCAD is an alpha design aid. Agent projects are concept drafts, and generated parts must still be reviewed by a
qualified person before fabrication. It does not calculate load capacity,
material behaviour, regulatory compliance, or safety. Its disclosed tolerance
and coupon-calibration estimates are design aids, not manufacturing guarantees.

The primary product interface is now terminal-first. A prompt submitted as
`neurocad "..."` becomes a durable local job and produces one atomic,
provenance-bearing artifact directory. A user-scoped daemon serializes the
configured work, survives terminal closure, and records job state. The typed
electronics-enclosure pipeline remains available for editable project revisions,
manufacturing preflight, calibration, and explicit external handoffs. See
`docs/PRODUCT_WORKFLOW.md` for that narrower contract.

## Install and first prompt

From this source checkout, the currently verified installation path is:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
neurocad doctor
neurocad "a 120 x 80 x 4 mm plate with four 4 mm holes"
```

The first prompt creates a strict user configuration and starts the local daemon
automatically. Run `neurocad setup` when you also want to install the persistent
launchd or user-systemd service explicitly.

For a persistent macOS/Linux command from this checkout:

```bash
NEUROCAD_PACKAGE="$PWD" sh ./install.sh
```

The installer stages and checks a fresh environment before publishing launchers,
then creates the user configuration and installs/starts a launchd or user-systemd
service. Set `NEUROCAD_SKIP_SETUP=1` only when service setup must be performed
later with `neurocad setup`. Failed package installation or health checks leave
existing launchers unchanged. Previous environments are retained for rollback.
It refuses unrelated existing executables.
Windows, private GitHub access, OpenSCAD setup, and first-use recipes are in
[Quick start](docs/QUICKSTART.md).

The repository is public as of 2026-09-09; `v0.5.0a6` is still an unreleased
candidate. Use the [quick start](docs/QUICKSTART.md) to obtain audited `main`
without credentials. Public source access is not a passing release receipt:
the immutable-tag installer and release-artifact gates remain open.

For the current implementation and its measured limitations, see the
[publication checklist](docs/FINAL_9_OF_10_CHECKLIST.md). Research controls and
historical evidence are intentionally not rewritten as part of product upgrades.
The [GitHub handoff](docs/GITHUB_HANDOFF_20260909.md) records the merged changes,
cross-platform checks, anonymous installation and remaining review gates.

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

For conversational drafting with assumptions, revision memory, component
checkpoints, and a live browser viewer:

```bash
neurocad studio ~/NeuroCADProjects/bottle --view
# then: make a water bottle
# then: make it 750 mL, add a carrying loop, and widen the base
```

See [Agent studio](docs/AGENT_STUDIO.md) for local/hosted provider setup and the
current general-CAD boundary. Without a configured model, the credential-free
planner covers editable primitive concepts, water bottles, and a decorative
Mark III-inspired cosplay/display shell.

The deterministic verified generation path requires all overall dimensions and
requested feature dimensions:

State all overall dimensions and all requested feature dimensions explicitly:

```text
a 120 x 80 x 4 mm plate with four 4 mm holes
a plate 120 mm wide 80 mm deep and 4 mm thick
a 100 x 80 x 20 mm enclosure with 2 mm wall thickness
a 100 x 60 x 4 mm plate with two 12 x 5 mm slots
a cylinder with radius 20 mm and height 50 mm
a 40 x 30 x 20 mm box
Please make me a sturdy mounting plate that is 120 millimeters wide, 80 millimeters deep,
and 4 millimeters thick, with four holes that are 4 millimeters in diameter.
```

Dimension sequences may use `x`, `×`, or `by`. Supported units are millimetres,
centimetres, metres, and inches; they are normalized to millimetres. Conversational
request prefixes, punctuation, common object synonyms, named dimensions, and common
feature phrasing are normalized into the same deterministic grammar. The normalized
contract is retained in the canonical IR metadata. Qualitative terms such as `sturdy`
are reported as non-geometric warnings; they never silently invent dimensions or
certify strength.

When four holes are requested, they are placed symmetrically near the four
corners. Other counts use deterministic symmetric layouts. Hole diameter and
slot dimensions are mandatory.

## Commands

The normal interface is the prompt itself:

```bash
neurocad "a 120 x 80 x 4 mm plate with four 4 mm holes"
```

The command waits for completion and prints the new artifact directory. That
directory contains `request.json`, `validation.json`, `manifest.json`, canonical
IR, OpenSCAD, and the verified STL and rendered preview when their local
OpenSCAD capability probes pass. Publication is atomic: an existing destination is refused and a failed
job publishes no partial directory. Useful daemon controls are:

When native OpenSCAD image rendering is unavailable, the preview is a
deterministic isometric wireframe rendered from the already verified STL; the
manifest records `verified-stl-wireframe` as its renderer.

```bash
neurocad daemon status
neurocad jobs list
neurocad jobs show NCJ-...
neurocad jobs wait NCJ-...
neurocad jobs retry NCJ-...
neurocad daemon logs
neurocad daemon restart
```

Human-readable status, compact job tables, colored state transitions, durable
retry, and structured daemon event logs are the defaults. Add `--json` to daemon,
jobs, setup, doctor, and generation commands when scripting. `--format auto` is
the generation default: it produces IR and SCAD everywhere and adds verified STL
and preview artifacts only when the respective local OpenSCAD capability probes
pass. Use `--no-wait` to enqueue and
return a job ID, or `--local -o /absolute/new/directory` to bypass the daemon while
retaining the same validation and manifest path. `neurocad config show` prints
the exact persistent configuration; `neurocad config set` validates updates and
requires a daemon restart. Running `neurocad` with no arguments in a terminal
opens the persistent agent studio. Its commands include `:view`, `:project`,
`:assumptions`, `:history`, `:status`, `:jobs`, `:help`, and `:quit`.

Analyze an existing STL, propagate a tolerance model, or evaluate a bounded
analytical physics constraint:

```bash
neurocad nlp "Design an enclosure 10 x 7 x 3 cm with walls 2 mm and an FDM standard profile and an open top"
neurocad topology plate.stl --require-closed-manifold -o topology.json
neurocad tolerance docs/examples/tolerance.json -o tolerance-report.json
neurocad math tolerance docs/examples/tolerance-quadratic.json
neurocad math beam --force 10 --length 50 --width 10 --thickness 4 --modulus 2200
neurocad physics docs/examples/physics-buckling.json -o buckling-report.json
```

`neurocad nlp` prints recognized source spans, precise unresolved locations,
recovery suggestions, disclosed deterministic assumptions, and the normalized
millimetre specification. The `math` namespace provides terminal-oriented views;
the established specialist commands retain their machine-readable defaults.
Tolerance inputs can target an explicit fit probability and require a declared
worst-case guard, with correlated variance attribution retained in the receipt.

Topology reports F2 Betti numbers, Euler characteristic, boundary loops,
orientability and genus where applicable. Kernel verification also rejects
singular vertex links and detected non-adjacent triangle self-intersections.
The geometric predicates are bounded floating-point evidence, not an exact BREP,
surface-equivalence, or physical-fit proof. See [Mathematics](docs/MATHEMATICS.md)
and [Physics](docs/PHYSICS.md) for equations, assumptions, numerical/resource
limits, and reference tests. The [Scientific kernel](docs/SCIENTIFIC_KERNEL.md)
documents dimensional quantities, automatic differentiation, local nonlinear
constraints/optimization, intervals, Monte Carlo, and numerical diagnostics.

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
  --dataset research/benchmarks/neurocad_benchmark_v1.jsonl \
  --output neurocad-benchmark-results.json
```

This loads and validates the frozen JSONL without rewriting it. Dataset
generation is a separate, explicit operation:

```bash
python -m core.data prepare /tmp/neurocad-benchmark.jsonl --seed 20260902
python -m core.data validate research/benchmarks/neurocad_benchmark_v1.jsonl
neurocad benchmark --generate --dataset /tmp/neurocad-benchmark.jsonl \
  --output /tmp/neurocad-benchmark-results.json
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

For a bounded pipeline check using the reviewed smoke configuration:

```bash
neurocad research --config configs/research_smoke.json \
  --run-id NC-SMOKE-LOCAL --output /tmp/neurocad-research-smoke --require-kernel
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
