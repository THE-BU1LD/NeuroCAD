# NeuroCAD expansion architecture — 2026 Q4

Status: implementation plan on `expansion/brep-feature-ir-20260925`.

This document is deliberately additive. The existing deterministic OpenSCAD/CSG
pipeline, frozen research evidence, enclosure workflow, daemon/job model, and
verification receipts remain valid. New capabilities must not be described as
working until their own acceptance gates pass.

## 1. Product target

Move NeuroCAD from a bounded prompt-to-CSG system toward a stateful engineering
compiler:

```text
natural-language requirement
  -> requirement/intent graph
  -> explicit assumptions + unresolved requirements
  -> feature-history IR
  -> deterministic exact-CAD backend
  -> B-Rep + editable source/history
  -> geometric + dimensional + intent verification
  -> revision/rebuild loop
  -> STEP/STL/SCAD/JSON artifacts with provenance
```

The planner may be probabilistic. Accepted geometry may not be.

### Non-goals

- Do not replace the verified OpenSCAD path before the new path is proven.
- Do not silently infer dimensions needed for fabrication.
- Do not call mesh exchange an editable native CAD document.
- Do not call heuristic manufacturability or analytical physics a safety proof.
- Do not rewrite historical negative research results.
- Do not add a learned model whose checkpoint/evaluation does not actually exist.

## 2. The architectural split

NeuroCAD should expose four explicit layers instead of asking one representation
to carry every concern.

### Layer A — Requirement IR

Represents what the user asked for, independent of a specific CAD kernel.

Minimum fields:

- requirement id and source span;
- quantity, units and tolerance;
- semantic target/role;
- relation to other requirements;
- must/should/preference strength;
- provenance: explicit / user-confirmed / deterministic policy / unresolved;
- verification method;
- status: satisfied / violated / unresolved / unsupported.

Every material phrase in a fabrication-bound prompt must be mapped to one of
these records or surfaced as unresolved.

### Layer B — Feature-history IR

Represents the editable construction history.

Initial feature vocabulary:

- datum plane / axis / point;
- 2-D sketch;
- line, circle, arc and rectangle sketch entities;
- dimensional/geometric sketch constraints;
- box/cylinder primitives as migration helpers;
- extrude/add and extrude/cut;
- revolve/add and revolve/cut;
- boolean union/cut/intersect;
- fillet;
- chamfer;
- linear pattern;
- circular pattern;
- mirror;
- named body / component.

Later vocabulary can include loft, sweep, shell, draft and assembly joints only
after the narrow set is stable.

Feature IR must be versioned and deterministic. Feature references are by stable
NeuroCAD ids, never by a raw kernel face/edge index.

### Layer C — Kernel adapter

Introduce a backend interface rather than embedding a second compiler throughout
the product:

```python
class ExactCADBackend(Protocol):
    def build(program: FeatureProgram) -> BuildReceipt: ...
    def export_step(program: FeatureProgram, path: Path) -> ExportReceipt: ...
    def export_stl(program: FeatureProgram, path: Path) -> ExportReceipt: ...
    def inspect(program: FeatureProgram) -> GeometryReceipt: ...
```

First candidate: CadQuery/OCP because it provides a Python parametric construction
layer over OpenCascade and supports exact CAD exchange including STEP. It should
be an optional capability until cross-platform installation, deterministic
builds and license/package review pass.

Keep OpenSCAD as the proven CSG backend for the existing v1 IR.

### Layer D — Verifier

The verifier consumes Requirement IR + Feature IR + kernel evidence and produces
claim-level results. A successful kernel build alone is not success.

Required checks for the first exact-CAD slice:

- kernel build succeeds;
- exactly expected body/component count;
- B-Rep validity check passes;
- overall extents match requirements;
- named holes/cutouts/features exist;
- dimensional constraints match within declared tolerance;
- expected topology / feature count checks where meaningful;
- stable selectors resolve uniquely;
- STEP export succeeds;
- STEP re-import reproduces body count and bounded geometric invariants;
- all must-level requirements are satisfied or the build fails.

## 3. Stable references: solve topological naming early

Fillet/chamfer and revision workflows fail if NeuroCAD stores “edge 7” or
“face 3”. Kernel ordering is not a semantic identity.

Introduce semantic selectors with provenance, for example:

```json
{
  "entity": "edge",
  "generated_by": "extrude_body",
  "role": "outer_vertical_edge",
  "predicates": [
    {"kind": "parallel_to", "axis": [0, 0, 1]},
    {"kind": "near_bbox_corner", "corner": "x+y+"}
  ],
  "resolution": "unique_required"
}
```

A selector must resolve to exactly one entity unless its contract explicitly
permits a set. Zero or multiple matches fail closed with an explanation.

Initial selector predicates should be deterministic and explainable:

- generated-by feature;
- semantic role;
- surface/curve type;
- normal or axis relation;
- min/max coordinate;
- bounding-box region;
- radius/length range;
- adjacency to another named entity.

Record the selected entity's geometric signature in the receipt so revisions can
detect drift rather than silently targeting a new face.

## 4. Revision semantics

A revision is not “regenerate from the latest prompt”. It is a typed transaction
against durable design state.

```text
project revision N
  + user edit
  -> proposed requirement delta
  -> proposed feature delta
  -> precondition checks
  -> rebuild
  -> verification
  -> semantic diff + geometry diff
  -> revision N+1 or no state change
```

Required invariants:

- invalid edits never mutate the accepted project;
- old revisions remain replayable;
- source prompt and change rationale are retained;
- changed requirements are explicitly listed;
- unchanged must-level requirements are regression checked;
- selector ambiguity is an edit failure, not a guessed target;
- every accepted revision receives a new content hash and build receipt.

## 5. Optimization layer: calculus connected to CAD

NeuroCAD already has bounded engineering math. Expansion should connect that math
to named CAD parameters without pretending to solve arbitrary engineering.

Represent an optimization problem as:

```text
design variables x
objective f(x)
equality constraints h(x)=0
inequality constraints g(x)<=0
parameter bounds
topology fixed during continuous solve
```

First supported objectives should be narrow and auditable:

- minimize material proxy / mass estimate;
- minimize bounding volume;
- target an exact internal volume;
- tune a rectangular beam dimension under a declared Euler-Bernoulli stress or
  deflection constraint;
- maximize a declared clearance margin;
- choose enclosure dimensions that fit a bounded component layout.

Each objective/constraint must cite its analytical or empirical basis in the
optimization receipt.

Add derivative paths in this order:

1. closed-form derivative where available;
2. existing automatic differentiation/scientific-kernel path;
3. bounded finite differences with step-size diagnostics.

Optimization is allowed to change only explicit design variables. It may not
invent a topology change or waive a hard requirement.

### Robust optimization

Add tolerance-aware constraints:

- expected value;
- worst-case interval guard;
- target fit/yield probability when a declared statistical model exists.

This creates a useful differentiator: NeuroCAD can return a candidate plus the
assumptions, sensitivity and uncertainty receipt that led to it.

## 6. Field-driven and multiscale geometry

Add an experimental geometry family after exact feature CAD is stable.

Use a separate field specification rather than forcing implicit geometry into the
B-Rep feature tree:

```text
macro envelope
+ field domain
+ cell / implicit family
+ cell scale
+ volume-fraction or thickness field
+ optional orientation field
+ clipping/boundary policy
-> generated field geometry
-> mesh/surface validation
```

Initial families:

- gyroid;
- Schwarz-P;
- diamond TPMS;
- simple strut lattices;
- graded infill / porosity fields.

Potential applications:

- lightweight structures;
- heat-transfer structures;
- flow/mixing structures;
- acoustic/mechanical metamaterial experiments;
- microfluidic concept geometry.

Do not market a geometry as “nano” merely because the user asks. The artifact
must record geometric scale, kernel tolerance, target process, minimum feature
size and unsupported fabrication claims. Micrometre/nanometre-scale design
requires a separate numerical-tolerance and fabrication-validation gate.

## 7. Assemblies and component-aware design

Do not start with a general assembly solver. Start with a bounded component graph:

- components with immutable local coordinate systems;
- mates: coincident plane, concentric axis, fixed offset;
- interference / clearance checks;
- imported reference envelopes;
- explicit fastener/hardware metadata;
- exploded-view transform as presentation-only state.

High-value first use case: electronics packaging.

```text
KiCad board receipt
+ connector envelopes
+ component height envelope
+ fastener requirements
-> enclosure feature program
-> cutouts/standoffs/lid
-> interference and clearance report
```

This extends the existing bounded KiCad handoff instead of creating a parallel
workflow.

## 8. Benchmark v2

The current frozen benchmark remains immutable. Add a new benchmark family with
separate tracks.

### Track A — language understanding

Human-written prompts, including ambiguity and unsupported requests.

Metrics:

- requirement extraction precision/recall;
- numerical/unit accuracy;
- unresolved-requirement precision;
- clarification necessity accuracy;
- source-span/provenance correctness.

### Track B — compiler/kernel correctness

Use golden Feature IR without a language model.

Metrics:

- build success;
- exact dimension error;
- B-Rep validity;
- expected body/feature count;
- selector resolution;
- STEP round-trip invariants;
- deterministic rebuild hash where applicable.

### Track C — revisions

Multi-turn human-written edits.

Metrics:

- requested change success;
- preservation of unchanged requirements;
- history replay;
- selector stability;
- regression rate;
- failed-edit state preservation.

### Track D — compositional CAD

Difficulty bands:

- L1 primitives + dimensions;
- L2 sketches + extrude/cut;
- L3 multiple features + patterns + fillet/chamfer;
- L4 bounded multi-component/revision tasks.

External public benchmarks may be used as comparisons, but report domain and
metric mismatches instead of converting unlike scores into one headline number.

## 9. CLI/product surface

Proposed additive commands:

```bash
neurocad feature validate design.ncad2.json
neurocad feature build design.ncad2.json --backend exact
neurocad feature inspect design.ncad2.json --json
neurocad feature export design.ncad2.json --format step -o design.step
neurocad feature rebuild project.ncadproj.json
neurocad optimize project.ncadproj.json optimization.json -o candidates/
neurocad requirements show project.ncadproj.json
neurocad requirements coverage project.ncadproj.json
```

Existing commands remain unchanged until migration is explicitly accepted.

Artifact bundle additions:

- `requirements.json`;
- `feature-program.ncad2.json`;
- `build-receipt.json`;
- `verification.json`;
- `design.step` when exact backend is available;
- optional `design.stl` preview/fabrication mesh;
- `semantic-diff.json` for revisions.

## 10. Acceptance gates

### Gate G0 — representation

- schema rejects malformed/ambiguous feature references;
- all ids bounded and unique;
- dependencies form an acyclic ordered graph;
- no raw face/edge indices in persisted source;
- round-trip JSON serialization is deterministic.

### Gate G1 — exact backend spike

Five fixed golden programs:

1. constrained rectangular sketch -> extrude;
2. plate -> four patterned holes;
3. revolved bottle-like body;
4. box -> edge fillet;
5. enclosure-like body -> chamfered cutout.

For each: build, inspect and STEP export/re-import. Retain kernel version and
receipts.

### Gate G2 — stable revision

For each G1 program, change one dimension and rebuild. Verify the requested change
and all declared invariants. Include adversarial cases where a selector becomes
ambiguous; those must fail.

### Gate G3 — NL-to-feature subset

Human-written prompts compile into only the already-proven G1/G2 vocabulary.
Language failure and kernel failure are reported separately.

### Gate G4 — optimization

At least three analytical cases with known solutions plus geometry rebuilds.
Verify objective improvement, hard-constraint satisfaction and deterministic
receipts.

### Gate G5 — benchmark/public alpha

Freeze benchmark v2 before the final run. Publish exact code/data hashes and
failure cases. No benchmark regeneration during evaluation.

## 11. Work order

P0 foundation:

1. Requirement IR contract and coverage ledger.
2. Feature IR v0 schema + validation.
3. Stable semantic selector contract.
4. Exact-backend protocol and capability probe.
5. Five-program golden corpus.
6. Independent geometry/build receipt.

P1 useful exact CAD:

7. Sketch + constraints.
8. Extrude/revolve.
9. Fillet/chamfer.
10. Linear/circular pattern.
11. STEP export/re-import verification.
12. Typed revision transactions.

P2 engineering intelligence:

13. Optimization problem IR.
14. CAD-parameter binding and sensitivities.
15. robust/tolerance-aware optimization.
16. bounded component/assembly graph.
17. component interference/clearance.
18. KiCad-to-enclosure component-aware flow.

P3 research expansion:

19. Benchmark v2 human-written prompts.
20. Multi-turn edit benchmark.
21. Field/lattice geometry IR.
22. TPMS + graded fields.
23. inverse editing / target-measurement solve.
24. learned planner or repair policy only after deterministic baselines exist.

## 12. Definition of a meaningful next release

Do not call the expansion complete because a STEP file can be emitted.

A meaningful exact-CAD release must demonstrate, from a clean install:

```text
human request
-> explicit interpreted requirements
-> editable feature history
-> exact-kernel build
-> verified STEP
-> semantic edit
-> deterministic rebuild
-> verification that the requested change happened
   and unchanged hard requirements still hold
```

That is the point where NeuroCAD becomes materially more than prompt-to-mesh or
prompt-to-script generation.
