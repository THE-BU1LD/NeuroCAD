# NC-PHYS-V3-CONFORMANCE-3

Authored 2026-10-14. This is a project-authored software conformance study,
not a blinded confirmatory experiment or independent reproduction. Existing
source and unit tests were inspected during design. No new case outcomes are
observed before freeze.json is written. Frozen inputs must never be retuned
after execution; corrections require a separately named successor protocol.

## Scope and operating envelope

The six newly introduced v3 models are evaluated separately. Inherited v2
models retain their existing contracts and frozen evidence; the full repository
regression suite is a separate compatibility check, not new v2 science.

* Cantilever: prismatic, small-displacement linear Euler-Bernoulli bending;
  signed tip and uniform loads. Reference deflection comes from integrating
  the bending moment against the unit-tip-load moment; maximum stress uses
  the extrema of the moment polynomial over the entire beam.
* Combined stress: symmetric point stress tensor; exact diagonal, pure shear,
  and rotated two-axis tensors. No spatial stress recovery or fracture model.
* Thermal network: constant symmetric conductances with fixed temperatures;
  three-node series resistance references and energy conservation. Disconnected
  free nodes must be refused. No radiation or temperature-dependent conductance.
* Forced vibration: linear SDOF steady harmonic force/base excitation;
  complex mechanical impedance gives reference amplitudes. Undamped exact
  resonance must be refused. No multimode or transient claim.
* Pipe network: steady incompressible circular pipes; laminar Poiseuille
  resistance and explicitly supplied constant-factor parallel branches.
  Transitional automatic friction and invalid dimensions must be refused.
  No looped networks, pumps, turbulence validation, or compressibility claim.
* Electrothermal wire: uniform current-driven conductor, linear resistivity
  and constant thermal resistance; reference equilibrium solves the scalar
  heat balance. Feedback at or above unity must be refused.

Every scalar case stores inputs, expected output paths, reference derivation,
and tolerances before execution. Numerical comparison is
abs(actual-reference) <= atol + rtol*abs(reference), rtol=1e-9 and atol=1e-9
in the output field's declared units unless explicitly specified in the case.
Non-finite results always fail. Rejections require ValueError or TypeError
and the frozen diagnostic substring in source mode; installed CLI additionally
requires exit code 2. No crash, missing dependency, or arbitrary nonzero status
counts as correct rejection. All cases are attempted and failures retained.
All endpoints require 100%; no aggregate score may hide a failing family.
The matrix has 32 scalar cases (beam 6, stress 5, thermal 5, vibration 5,
pipe 5, wire 6). Scope is deterministic conformance, with no statistical
population inference. Budget: one local scalar execution, one installed
execution per admitted environment, at most 30 minutes per hosted job. Stop
at the complete retained matrix, regardless of failures. Infrastructure-only
retries require a new output directory and retained earlier receipt; no source
or expected-answer edits are permitted under this frozen version.

## Installed acceptance

Run a fresh wheel installation in an isolated environment outside the checkout,
with PYTHONPATH removed and user site disabled. Record installed module paths,
distribution version, source hashes, wheel hash and dependencies. Refuse an
editable/check-out import or source mismatch. Run the same frozen scalar cases
through the public CLI. Then exercise all four composite families, independently
calculated volumes, bundle file hashes, collision refusal, invalid geometry,
unsupported plate loads, temperature interpolation, algebraic load combination,
geometry/material/load contradictions, material extrapolation, mixed coordinate
systems, all three uncertainty methods, nonspatial overlays, and saved-result
freshness after geometric versus non-geometric edits. Retain every command,
stdout, stderr and output. Compiled mesh checks are separate from scalar checks.

Composite geometry scope is exact idealized hollow shafts, I-beams, extruded
L-sections and perforated plates. Composite structural screens receive existing
regression coverage; this first frozen suite does not independently validate
every section property, structural output or arbitrary geometry.

## Freeze, preservation and execution

freeze.json binds the protocol, cases, fixtures, runner and production Python
sources, plus a complete path/hash inventory of research/physics_v2,
release/physics_v2 and paper. Verify exact inventories before and after runs.
New files and deletions in protected paths are changes. Freeze is a content
identity, not a signature or independent timestamp. Source Git identity and
dirty state are recorded separately. Reproduction may rerun unchanged content
in a new output directory, never overwrite an earlier receipt. Changed source,
references or tolerances require a new version; retain negative results.

Local scalar-only execution uses direct loading of the stdlib-only analytical
module and must be labeled SOURCE_SCALAR, never installed acceptance. Heavy
imports, installs/builds and mesh runs require two stable samples of at least
512 MiB free-plus-speculative memory, no rising pageouts/swapouts, 2 GiB disk
headroom and no competing study process. Hosted CI uses isolated runners with
the same memory/disk floor. Admission failure is BLOCKED, not a failed model.

## External gates

Physical experiments: NOT_STARTED. Independent reproduction: NOT_STARTED.
Intended-user task study: NOT_STARTED. No software pass changes these states.
No FEA/CFD, safety certification, manufacturing readiness, population accuracy,
novelty, reliability-tail or global interval-bound claim is evaluated here.

## Successor identity and retained failure

This successor corrects the opposing-load maximum-stress defect retained in v1.
All v1 inputs, freeze and failed receipts remain unchanged and replayable at
commit 7c53a0c287071135b962b19b6d5bfe651a84c67f. Prior outcomes are known.
Replaying the original cases establishes regression conformance, not fresh
confirmation. Added sign reversal, interior/boundary extremum and yield cases
use exact beam-equilibrium references. No numerical threshold is relaxed.
Maximum absolute moment considers both endpoints and the interior stationary
point z=-F/w when 0<z<L. The stationary moment is -F^2/(2w).

## Integration revision

This source-bound regression successor integrates reviewed product fixes from
PRs 88-102 with corrected Physics v3. Earlier freezes and outcomes remain
unchanged; their known cases are reused without fresh confirmatory claims.
The linear diagnostics contract explicitly rejects unrepresentable nonzero
products and backward-error ratios, retaining strict original-integer admission.
The prior zero-valued underflow outputs are retained in predecessor history,
not accepted as success in this integration. Hosted compatibility tests include
the unchanged inherited 40,000-draw seeded engineering regression; this is a
new integration budget, not reopening a closed numerical development session.
Maximum four hosted verification attempts per workflow; retain failed attempts.
No learned/provider calls, physical trials or protected outcomes are authorized.
