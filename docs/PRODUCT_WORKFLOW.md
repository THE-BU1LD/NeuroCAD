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

### Protected interfaces and change impact

Capture only the interfaces that must remain stable, then pass the external
contract to a revision-producing command:

```bash
neurocad enclosure interface-lock controller-r2.ncad.json \
  --contract-id controller-interfaces-v1 \
  --cutout usb-port --standoff board-a --standoff board-b \
  --pcb-mounting --lid-interface --tolerance 0.05 \
  -o controller-interfaces-v1.json
neurocad enclosure interface-lock-verify controller-r2.ncad.json \
  controller-interfaces-v1.json
neurocad enclosure edit controller-r2.ncad.json \
  --instruction "rename field controller" \
  --interface-contract controller-interfaces-v1.json \
  -o controller-r3.ncad.json
```

The contract stores the exact source-project hash, revision, selected snapshots,
and a bounded absolute numeric tolerance. Cutouts are compared by stable ID,
including face, position, kind, size and purpose. Standoffs include position,
height, diameters and hardware. PCB mounting locks include origin and hole
coordinates. Lid locks include the modeled lid fields plus body XY envelope,
wall, corner radius and manufacturing profile. Missing interfaces and string or
structural changes always fail; the numeric tolerance does not relax them.

Before accepting a candidate, create and recompute its impact report:

```bash
neurocad enclosure impact-report controller-r2.ncad.json controller-r3.ncad.json \
  --interface-contract controller-interfaces-v1.json -o controller-r3-impact.json
neurocad enclosure impact-report-verify controller-r2.ncad.json \
  controller-r3.ncad.json controller-r3-impact.json \
  --interface-contract controller-interfaces-v1.json
```

Reports check exact revision ancestry, use feature-ID and coordinate-level paths,
identify dependent geometry, and list artifact, geometric, manufacturing, fit,
mounting, or process evidence invalidated by each change. The report is a
deterministic dependency statement, not a claim that unlisted evidence is
sufficient. `edit`, `apply-proposal`, `fit-revision-apply`, and calibrated
clearance application enforce an optional contract before publishing output.
When a locked interface is intentionally revised, create a reviewed successor
contract from the accepted new revision rather than modifying the old contract.

The local workbench exposes the same edit grammar through a two-step review and
confirmation flow. `POST /api/edit` accepts a canonical project string in `source`,
one `instruction` (at most 512 characters), and an optional `reason` of at most
512 characters. It returns a proposed validated project, field-level before/after
changes and the canonical base-project SHA-256. It does not mutate server state or
compile meshes. Unknown fields, forged history, no-op instructions and invalid
geometry fail without replacing the current browser project. Apply confirmation
updates the current specification and invalidates previous mesh downloads.

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

Lid plates and insertion plugs follow the enclosure's rounded outline with the
declared clearance. Screw-lid plugs include relief around the bosses beneath
the screw-bearing plate. Validation reserves plug depth when checking the floor,
standoffs and declared PCB/component envelope. Independent mesh probes check
rounded corner voids and screw-boss ring clearance; these sampled checks do not
certify complete assembly collision freedom or physical fit.

The September 9 correction changes regenerated lid geometry for rounded cases
and screw lids with a plug. Existing project JSON still opens with its history;
rebuild affected source/mesh bundles from the reviewed project. Old bundles that
do not match current canonical generation fail verification instead of being
silently relabelled as current.

Bundle publication refuses an existing destination and writes a hash manifest.
The directory is collision-refusing and tamper-evident, not physically immutable.
Verify a published source or compiled bundle independently before handoff:

```bash
neurocad enclosure verify controller-r3
```

For handoff, bind verification to the intended revision and require actual meshes:

```bash
neurocad enclosure verify controller-r3 --project controller-r3.ncad.json --require-stl
```

Without `--project`, verification establishes internal bundle consistency only;
an older, intact bundle can still pass. With `--project`, a different project,
revision, history, or specification fails. `--require-stl` rejects source-only
bundles. Project files are published without replacement, including when another
writer creates the destination after the CLI's initial collision check.

Verification fails closed on unknown manifest fields, path traversal, symbolic
links, missing or extra entries, hash or size changes, non-canonical IR or
OpenSCAD, stale preflight results, and invalid or stale mesh verification.

## 4. Engineering calculations

### Verified solid-model material

For an STL bundle built from the exact project, calculate volume from the verified
body/lid meshes rather than relying on the shell approximation:

```bash
neurocad enclosure preflight controller.ncad.json --bundle controller-r1 --density 1.25 --material-cost 20
```

The added `compiled_geometry` result records per-part and total volume in mm³,
solid-model mass in grams, material cost in the supplied price's currency, source
project hash, and the signed percentage error of the shell estimate. Density is
in g/cm³ and price is per kg. Without density, mass and cost remain unknown.
Source-only, stale-revision, different-project, or tampered bundles are rejected.
Integer and floating-point spellings of equivalent dimensions are normalized.
Existing preflight output and bundle formats are preserved.

This is tessellated solid-model volume, not slicer filament usage: infill, supports,
purge, waste, print duration, and physical measurements are not inferred. Boolean,
non-finite, negative, and overflowing economic inputs are rejected as applicable.

### Cutout fit samples

Generate a small flat coupon for an existing unrounded body cutout:

```bash
neurocad enclosure fit-sample controller.ncad.json --cutout usb-port -o usb-sample.ncad.json
neurocad compile usb-sample.ncad.json --format stl -o usb-sample.stl
```

Use the actual cutout ID from the project. Rectangular and circular body cutouts
are supported; lid/rounded cutouts are rejected. `--margin` controls surrounding
material from 2 to 50 mm. The coupon preserves generated aperture dimensions,
including circular-hole compensation, and the source wall/floor thickness.
Canonical IR metadata records the source project hash, revision, and face.
The coupon is flattened into XY: deliberately match manufacturing orientation
and process when comparing fit. A successful mesh check does not establish physical
fit, assembly access, or a promised print duration. Existing outputs are refused.

### Source-bound tolerance ladders

Generate a labeled set of fit coupons around the compiled aperture dimensions:

```bash
neurocad enclosure fit-study controller.ncad.json --cutout usb-port \
  --adjustment=-0.2 --adjustment=0 --adjustment=0.2 --adjustment=0.4 \
  --replicates=3 \
  --output-dir usb-fit-study
neurocad enclosure fit-study-verify usb-fit-study --project controller.ncad.json
```

An adjustment is the total circular diameter change or the total rectangular
width and height change. The bundle contains canonical coupon IR, deterministic
OpenSCAD source, the canonical source project, a hash-bound study description, a
replicated CSV worksheet, a strict observation template, and a manifest. A fixed
anchor plus five little-endian binary holes physically identifies each printed
variant in the top margin. Verification checks the inventory and hashes,
regenerates every coupon and SCAD file from the bundled project, checks that each
declared size equals its aperture primitive, and can require an independently
supplied exact project revision.

Complete every passport field and every predeclared trial in a copy of
`observations.template.json`, then evaluate without modifying the study:

```bash
neurocad enclosure fit-study-evaluate usb-fit-study observations.json \
  -o usb-fit-report.json
neurocad enclosure fit-study-report-verify usb-fit-study usb-fit-report.json
```

The evaluator rejects stale bindings, duplicate or missing trials, placeholder
passport fields, timestamps without a UTC offset, non-boolean outcomes, and
incomplete process identity or acceptance criteria. It conservatively requires
every predeclared replicate to pass, reports trial counts and descriptive 95%
Wilson intervals, and retains non-monotone inconsistencies. It does not turn a
coupon observation into a guarantee for the assembled enclosure, another
orientation, or another manufacturing process. Report verification reconstructs
the normalized strict observation document and recomputes the full result; an
edited recommendation, count, interval, or disposition fails.

Bind the completed record and retained external files without claiming that
hashing authenticates their contents:

```bash
neurocad enclosure fit-study-seal usb-fit-study observations.json \
  --evidence coupon-photo.jpg --evidence caliper-certificate.pdf \
  --output-dir usb-fit-evidence
neurocad enclosure fit-study-seal-verify usb-fit-study usb-fit-evidence
```

The sealed bundle retains exact attachment bytes, normalized observations, the
recomputable report, source/study bindings, sizes, and SHA-256 digests. It proves
byte integrity after sealing, not authorship, measurement truth, or physical fit.

### Evidence-bound cutout revisions

Only a sealed report with a monotone, bracketed observed transition can be used
to propose a cutout revision. Planning is separate from application:

```bash
neurocad enclosure fit-revision-plan controller.ncad.json usb-fit-study \
  usb-fit-evidence -o usb-fit-revision.json
neurocad enclosure fit-revision-plan-verify controller.ncad.json \
  usb-fit-study usb-fit-evidence usb-fit-revision.json
neurocad enclosure fit-revision-apply controller.ncad.json usb-fit-study \
  usb-fit-evidence usb-fit-revision.json -o controller-r2.ncad.json --confirm
neurocad enclosure fit-revision-verify controller.ncad.json \
  controller-r2.ncad.json usb-fit-study usb-fit-evidence usb-fit-revision.json
```

The deterministic plan records the nominal dimension before and after the edit,
the compiled aperture before and after profile compensation, the exact project,
study, report, and evidence hashes, and the process passport. The source project
is never overwritten. Application changes only the named cutout collection and
records one revision-history entry. Exact source binding makes the plan
single-use: a stale or already revised project fails before mutation. Circular
profile compensation remains separate from the nominal diameter, preventing the
observed adjustment from being silently applied twice.

Unbracketed success, no success, or non-monotone outcomes are retained but cannot
drive a revision. Hashing does not authenticate evidence, and the revised design
still requires a new held-out fit study under the intended process.

### Analytical calculations

The preflight and public math helpers keep analytical, empirical, and heuristic
evidence separate:

- tolerance contributions combine independently by default; an explicitly
  validated correlation matrix adds covariance terms. Signed mean effects use
  compensated summation and worst-case losses remain a separate conservative
  model. See [Mathematics](MATHEMATICS.md) for units, formulas and assumptions;
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
