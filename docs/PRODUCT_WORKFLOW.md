# NeuroCAD enclosure workflow

This document defines what the maintained enclosure product accepts, computes,
verifies, and hands to other applications. Anything not stated here should be
treated as unsupported.

## 1. Natural-language contract

The built-in interpreter is a deterministic clause grammar, not a general
language model. Clauses are separated with semicolons and every clause must
match completely. Unknown words, repeated singleton clauses, missing dimensions,
oversized feature counts, and unsupported requests produce issues and no runnable
project.

A minimal complete request is:

```text
80 x 60 x 30 mm electronics enclosure; walls 2 mm; profile fdm standard; no lid
```

Supported clauses are:

```text
<W> x <D> x <H> mm electronics enclosure
walls <T> mm
floor <T> mm
corner radius <R> mm
profile fdm draft|fdm standard|fdm precision|resin standard
no lid|open top
friction lid <T> mm thick clearance <C> mm lip <L> mm
screw lid <T> mm thick clearance <C> mm M2|M2.5|M3|M4 fasteners at corners inset <I> mm
rectangular cutout <W> x <H> mm on <face> at <U> x <V> mm [for <purpose>]
circular cutout <D> mm diameter on <face> at <U> x <V> mm [for <purpose>]
vent grid <rows> x <columns> holes <D> mm diameter pitch <P> mm on <face> at <U> x <V> mm
<count> M2|M2.5|M3|M4 standoffs <H> mm high at corners inset <I> mm
pcb <W> x <D> x <T> mm [component height <H> mm]
title <portable title>
```

Faces are `front`, `rear`, `left`, `right`, `bottom`, and `top`. Face coordinates
are centered. For front/rear, U is global X and V is global Z. For left/right,
U is global Y and V is global Z. For top/bottom, U and V are global X and Y.

Conversational or model-generated proposals may use the provider-payload API,
but they are not executable unless all meaningful source spans are mapped, the
typed specification validates, and a trusted caller explicitly confirms it.
The model never emits geometry directly.

## 2. Project and edit model

`neurocad enclosure interpret` stores the source, exact phrase-to-field spans,
typed specification, project ID, and revision. `neurocad enclosure edit` creates
a new revision and records exactly one semantic change with its reason. Parsing
replays the change chain backwards and rejects forged before/after values,
unknown fields, duplicate keys, non-finite numbers, malformed IDs, and files
larger than 1 MiB.

Supported edit sentences include exact `set`, `resize`, `rename`, `add`, `move`,
and `remove` operations. Run `neurocad enclosure edit --help` for the interface;
an unsupported sentence is rejected rather than approximated.

## 3. Geometry and validation

The typed specification supports:

- body shells with independent wall/floor thickness and optional corner radius;
- open-top, screw-fastened, and friction insertion-plug lids;
- rectangular and circular face cutouts;
- circular vent grids;
- explicit or hardware-derived standoffs for M2, M2.5, M3, and M4;
- centered rectangular PCB envelopes, mounting holes, and component height;
- named FDM/resin profiles with disclosed minimum wall, clearance, hole
  compensation, and ligament assumptions.

Validation checks finite dimensions, allowed ranges, feature containment and
edge margins, generated-node budget, ID and generated-name collisions, feature
overlaps, standoff ligaments, PCB fit and hole alignment, and lid requirements.
Slide lids and rounded side-wall cutouts are explicitly rejected until their
geometry and request-level verification are implemented.

Each body/lid compiles to canonical IR, deterministic OpenSCAD, and optionally
STL. Static validation is reported as structural validity. Geometric validity is
unknown until an STL is compiled. Kernel verification checks finite vertices,
watertightness, winding, positive volume, body count, and exact extents where
the IR bounds are exact. Enclosure STL verification additionally ray-probes
requested cavities, walls, floors, cutouts, standoffs, holes, vents, and lid
material.

Bundle publication refuses an existing destination and writes a hash manifest.
The directory is collision-refusing and tamper-evident, not physically immutable.
Verify a published source or compiled bundle independently before handoff:

```bash
neurocad enclosure verify controller-r3
```

Verification fails closed on unknown manifest fields, path traversal, symbolic
links, missing or extra entries, hash or size changes, non-canonical IR or
OpenSCAD, stale preflight results, and invalid or stale mesh verification.

## 4. Engineering calculations

The preflight and public math helpers keep analytical, empirical, and heuristic
evidence separate:

- independent tolerance contributions combine as
  `sigma_total = sqrt(sum(sigma_i^2))`; mean shifts add algebraically and
  worst-case clearance losses add conservatively;
- an end-loaded rectangular cantilever uses `I = b t^3 / 12`,
  `stress = F L (t/2) / I`, and `deflection = F L^3 / (3 E I)`;
- symmetric placements enforce a zero centroid;
- component layout uses deterministic bounded shelf packing and is described as
  a feasible proposal, not a global optimum;
- orientation scores disclose each weighted penalty rather than hiding a learned
  or simulated result;
- shell material, mass, and cost are approximate and never labeled exact.

No calculation is finite-element analysis, fatigue analysis, a material model,
or safety certification.

## 5. Printer coupon calibration

Calibration input records nominal/measured X/Y/Z dimensions, hole diameters,
clearance pass/fail results, physical run IDs, process identity, nozzle size, and
measurement resolution. At least three observations per axis, three hole
measurements, two successes, two failures, and two runs are required.

The fit uses medians, a scaled-MAD descriptive dispersion with a measurement
resolution floor, and a monotone clearance transition bracket. The dispersion
is not a confidence interval and repeated coupons are not assumed independent.
Derived claims are recomputed when a profile is read, so edited recommendations
are rejected.

```bash
neurocad calibration fit observations.json -o printer-profile.json
neurocad calibration inspect printer-profile.json
neurocad calibration plan controller-r2.ncad.json printer-profile.json
neurocad calibration apply-clearance controller-r2.ncad.json printer-profile.json \
  -o controller-r3.ncad.json
neurocad enclosure preflight controller-r3.ncad.json --calibration printer-profile.json
```

Scale factors remain explicit slicer recommendations and hole compensation is
reported for review. Neither silently distorts nominal CAD. Only an observed
friction-lid clearance increase can be applied, and it creates an audited project
revision.

## 6. Application interoperability

Run `neurocad integrations list` to inspect runtime prerequisite detection and
the exact capability state:

| Application | Current contract | What is not claimed |
| --- | --- | --- |
| OpenSCAD | native SCAD; compiled and verified STL when detected | no GUI document opened |
| KiCad | bounded rectangular `.kicad_pcb` parser or complete IPC/CLI receipt, always source-hash-bound | no arbitrary outline parser or live IPC call |
| Fusion / Onshape | verified STL file handoff | no native feature tree or API upload |
| FreeCAD | SCAD or verified STL file handoff | no FCStd document |
| Blender | verified STL visualization handoff | not authoritative parametric CAD |
| PrusaSlicer / OrcaSlicer / Bambu Studio / Cura | verified STL handoff | no slicing, profile, G-code, or print |

Application handoff generation rehashes and reparses the declared specification,
rehashes every artifact, and reverifies every STL against both kernel rules and
the exact enclosure request. JSON receipts refuse existing destinations at the
atomic publication step.

`neurocad integrations verify <bundle>` performs those checks without creating
an application handoff. Success returns a machine-readable positive report;
any schema, inventory, content, hash, canonical-source, kernel, or request-level
mesh mismatch exits nonzero.

The hardened canonical-source contract is versioned as `neurocad-exchange-v2`
and its receipts as `neurocad-application-handoff-v2`. Earlier v1 bundles are
rejected rather than silently interpreted under stronger v2 guarantees.
A `ready` handoff means the required files exist and passed NeuroCAD's contract;
it is not evidence that the target application imported them.

## 7. End-to-end example

```bash
neurocad enclosure interpret \
  "80 x 60 x 30 mm electronics enclosure; walls 2 mm; floor 2.4 mm; profile fdm standard; friction lid 2.5 mm thick clearance 0.3 mm lip 2 mm; rectangular cutout 12 x 7 mm on front at 0 x 8 mm for USB-C; 4 M3 standoffs 6 mm high at corners inset 8 mm; pcb 54 x 34 x 1.6 mm component height 12 mm; title controller case" \
  --project-id controller --output interpretation.json \
  --project-output controller-r1.ncad.json

neurocad enclosure preflight controller-r1.ncad.json
neurocad enclosure build controller-r1.ncad.json --output-dir controller-r1 --stl
neurocad enclosure verify controller-r1
neurocad integrations export controller-r1.ncad.json \
  --output-dir controller-exchange --stl --manifest controller-apps.json
neurocad integrations verify controller-exchange
neurocad integrations handoff controller-exchange OrcaSlicer \
  -o controller-orcaslicer.json
```

For a supported rectangular KiCad board, create a strict mechanical review:

```json
{
  "review_version": "neurocad-kicad-mechanical-review-v1",
  "connector_inventory_complete": true,
  "component_height_measured": true,
  "max_component_height_mm": 12.0,
  "connectors": []
}
```

Then extract source-derived geometry, reverify it against the same board bytes,
and apply it to a new NeuroCAD project revision:

```bash
neurocad integrations kicad-extract controller.kicad_pcb \
  --review mechanical-review.json -o kicad-completed.json
neurocad integrations kicad-inspect kicad-completed.json \
  --source-board controller.kicad_pcb
neurocad integrations kicad-apply controller-r1.ncad.json kicad-completed.json \
  --source-board controller.kicad_pcb -o controller-r2.ncad.json
```

The application imports the board envelope, thickness, mounting-hole positions,
and maximum component height. Hole diameters and connectors remain in the
command report for review. No standoffs or cutouts are inferred; unmatched PCB
holes remain visible warnings until explicit supports are designed.

`kicad-extract` parses only one axis-aligned rectangular Edge.Cuts outline,
board thickness, and round NPTH pads within explicitly named mounting-hole
footprints. It rejects curved/polygonal outlines, footprint-defined edge cuts,
unclassified NPTH pads, incomplete review, malformed or oversized input, and
source/receipt disagreement. For unsupported boards, `kicad-request` plus
`kicad-bind` retains the reviewed external IPC/CLI path. Live KiCad control
remains outside this package.

The parser follows KiCad's documented millimetre-based S-expression board
format for KiCad 6 and later: <https://dev-docs.kicad.org/en/file-formats/sexpr-pcb/>.

Before fabrication, inspect the generated SCAD/STL, confirm connector and PCB
measurements against the actual hardware, choose material/process settings,
print coupons, and perform a physical fit test.
Follow `docs/PHYSICAL_VALIDATION_PROTOCOL.md`; until its evidence exists, report
"kernel verified, physical validation pending."
