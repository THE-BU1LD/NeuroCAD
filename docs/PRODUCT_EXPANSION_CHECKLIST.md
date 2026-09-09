# NeuroCAD product expansion checklist

Planning revision: 2026-09-07. This is a backlog, not a capability or completion claim.
Unchecked items require implementation or fresh acceptance evidence. Existing
functionality must be extended where possible rather than duplicated.

The current supported boundary remains [CAPABILITY_BOUNDARY.md](CAPABILITY_BOUNDARY.md).
The existing enclosure contracts, profiles, math helpers, edits, and bundle
verification are described in [PRODUCT_WORKFLOW.md](PRODUCT_WORKFLOW.md).
Release completion remains governed by [../DEFINITION_OF_DONE.md](../DEFINITION_OF_DONE.md).
These proposals do not silently expand the requirements for the current alpha.

## Existing foundations to reuse

Source review during execution found substantial implementations already present:

| Foundation | Existing component | Expansion boundary |
| --- | --- | --- |
| Typed enclosure contracts and validation | `core/enclosure.py`, `core/natural_language.py` | Extend supported requirements; do not add a competing specification |
| Revisioned edits | `core/project.py`, `core/edit_language.py` | Build interface locks and impact explanations on existing revision history |
| Calibration observations and bounded recommendations | `core/calibration.py` | Actual physical observations and held-out validation remain necessary |
| Process assumptions and analytical calculations | `core/manufacturing.py`, `core/engineering_math.py` | Extend declared models; do not relabel estimates as simulation |
| Independent artifact verification | `core/artifacts.py`, `core/enclosure_verification.py` | Reuse manifests, regeneration, and request-level geometric probes |
| Bounded board input and external handoff | `core/integrations/` | Expand explicit formats and external acceptance evidence |

The checkboxes below describe acceptance of expanded behavior, not absence of
all related code. The execution record is `../PROJECT_FINISH_CHECKLIST.md`.

## Acceptance rules for every feature

- [ ] Define the user problem, supported inputs, exclusions, and measurable outcome.
- [ ] Locate existing implementation and record the smallest extension required.
- [ ] Define typed inputs, units, limits, versioning, and deterministic behavior.
- [ ] State assumptions and classify checks as analytical, geometric, empirical, or heuristic.
- [ ] Implement a complete user path with useful diagnostics and failure recovery.
- [ ] Exercise representative success, boundary, contradictory, and malformed cases.
- [ ] Verify results independently of the generator where practical.
- [ ] Bind acceptance artifacts to source revision, inputs, dependency versions, and hashes.
- [ ] Update help, examples, capability boundaries, and migration notes as applicable.
- [ ] Demonstrate the feature from an installed package outside the source checkout.

## P0 — Finish and publish the existing supported alpha

- [ ] Reconcile canonical repository history without losing working code or evidence.
- [ ] Record one clean candidate revision and exact wheel/sdist checksums.
- [ ] Obtain CI evidence for that revision on the supported platform matrix.
- [ ] Verify license, dependency notices, distribution contents, and history secret scan.
- [ ] Publish an immutable tag and release artifacts after publication authorization.
- [ ] Test the documented installer anonymously on a clean machine.
- [ ] Confirm supported prompt examples and deliberate rejection examples from that install.
- [ ] Complete the physical validation protocol before claiming physical fit.
- [ ] Publish an evidence ledger with failures and external blockers still visible.
- [ ] Keep portal deployment readiness separate from CAD package release readiness.

## P1 — Requirements and mathematical foundations

Dependencies: existing typed specification, parser, preflight, and revision history.

- [ ] Design contract: present resolved dimensions, sources, assumptions, and unknowns; reject unresolved required fields.
- [ ] Unit extensions: normalize supported mixed units; verify equivalent inputs produce equivalent dimensions.
- [ ] Interval dimensions: retain measurement bounds; test feasible, impossible, and indeterminate cases.
- [ ] Constraint explanations: identify violated rules and the contributing parameter values.
- [ ] Conflict diagnosis: return a conflicting subset of requirements; do not call it minimal without checking minimality.
- [ ] Smallest feasible repair: minimize a disclosed weighted change objective while respecting locked parameters; independently recheck the proposal.
- [ ] Parameter operating ranges: report validated bounds and any disconnected feasible intervals.
- [ ] Protected interfaces: lock selected mounting patterns and connector locations; reject edits that violate them.
- [ ] Change-impact report: identify altered dimensions, dependent features, and invalidated evidence.
- [ ] Compatibility tests: check an old lid against a new body using explicit interface dimensions and tolerance bounds.
- [ ] Constraint report: emit passed, failed, and unknown results with check versions and assumptions.
- [ ] Report authenticity: verify hashes; introduce signatures only with explicit issuer identity and key management.
- [ ] Evidence expiry: invalidate only affected checks when geometry, process, material, or checker version changes.
- [ ] Design regression tests: rerun user requirements after edits; demonstrate detection of a deliberately broken interface.
- [ ] Robust tolerance calculations: distinguish worst-case bounds from statistical estimates; disclose independence and distribution assumptions.
- [ ] Sensitivity analysis: compare perturbations against known analytical cases and disclose step sizes or derivatives.

## P1 — Fast physical-fit workflow

Dependencies: supported enclosure features, deterministic exports, physical protocol.

- [ ] Fit-only preview: extract a connector opening or mounting interface while retaining production dimensions.
- [ ] Tolerance ladder: generate labeled clearance variants; verify labels correspond to measured geometry.
- [ ] Calibration coupon: include known reference dimensions and a measurement worksheet.
- [ ] Printer passport: record machine, nozzle, material, orientation, settings, measurements, date, and uncertainty.
- [ ] Compensation model: estimate supported dimensional bias from measurements; validate on held-out coupons.
- [ ] Nominal/compensated separation: preserve intended dimensions and make compensation reversible without double application.
- [ ] Cross-machine transfer: identify evidence that no longer applies when the process profile changes.
- [ ] Measurement assistant: show where to measure each required dimension and how uncertainty affects fit.
- [ ] Scale-check sheet: export a 1:1 template with calibration marks and instructions to disable print scaling.
- [ ] Acceptance worksheet: list critical dimensions, limits, instruments, observed values, and pass/fail/unknown results.
- [ ] Full workflow demo: request → fit sample → measurement → revised enclosure → independent verification.

## P2 — Hardware and assembly

Dependencies: stable feature identities, interface constraints, validated component data.

- [ ] Hardware-on-hand mode: select from an explicit user inventory and explain incompatible choices.
- [ ] Hardware source records: attach dimensional references and revisions; require review for uncertain entries.
- [ ] Component revision alerts: identify affected designs when board or connector dimensions change.
- [ ] Interface library: reuse versioned mounting patterns with compatibility tests.
- [ ] Cable/plug envelopes: include plug bodies, insertion travel, and specified cable bend limits.
- [ ] Tool access: validate a declared tool envelope and approach path for supported fasteners.
- [ ] Service access: check a declared removal path for batteries, boards, and filters.
- [ ] Assembly sequence: validate supported insertion paths; distinguish a checked sequence from exhaustive feasibility.
- [ ] Incorrect-assembly prevention: propose keyed geometry and test the prohibited orientation.
- [ ] Captive hardware: generate supported nut pockets and retention features with process-specific fit checks.
- [ ] Motion envelopes: check sampled or bounded hinge/slider travel and state coverage limits.
- [ ] Hardware simplification: propose fewer fastener types while preserving interface and load assumptions.
- [ ] Bracket templates: define mounting, envelope, and supported analytical checks before adding prompt syntax.
- [ ] Jig/fixture templates: define locating surfaces and workpiece clearances; verify the intended positioning behavior.

## P2 — Fabrication and optimization

Dependencies: process profiles, measured calibration, geometric validation.

- [ ] Oversized-part splitting: preserve reconstruction dimensions and validate generated joint interfaces.
- [ ] Support-reduction proposals: compare candidate orientations or geometries using a disclosed metric.
- [ ] Slicer integration: pin supported slicer versions; parse real output and handle failures/timeouts safely.
- [ ] Print-time/material comparisons: show slicer settings and measured estimates; avoid unsupported fixed-time promises.
- [ ] Scrap-stock constraints: accept stock bounds and keepouts; verify placement within available material.
- [ ] Process conversion: support one explicit conversion pair first; validate changed geometry and allowances.
- [ ] Manufacturability profiles: attach sources and applicability ranges to each rule; separate defaults from measured limits.
- [ ] Multi-objective variants: report feasible tradeoffs in mass, time, and clearance without claiming global optimality.
- [ ] Independent feasibility checks: reject optimizer outputs that violate the original contract.
- [ ] Analytical mechanics: restrict calculations to documented geometries, loads, and material assumptions; verify against reference cases.
- [ ] Calibration experiment planner: select informative coupons under a declared model and compare against a simple baseline.
- [ ] Failure attribution: report evidence for model error, process bias, or measurement error; retain ambiguous outcomes.

## P2 — Product experience and reproducibility

- [ ] Evidence overlay: link highlighted features to specific checks; avoid unsupported numerical confidence scores.
- [ ] Counterexample view: display the failing region, measured value, and required bound.
- [ ] Independent CAD critic: use separate geometric/checking logic and demonstrate detection of injected defects.
- [ ] Repair workflow: turn measured failures into reviewable parameter edits with before/after validation.
- [ ] Reproducibility capsule: extend existing bundles only where required; verify from a clean environment.
- [ ] Local operation: document all network use and demonstrate the supported offline workflow.
- [ ] User trials: observe users completing a fixed task and record completion, interventions, and failures.
- [ ] Accessibility: support keyboard navigation and readable textual equivalents for visual diagnostics.
- [ ] Design-family validation: exercise supported parameter boundaries and representative combinations.

## P3 — Portal and shared physical evidence

Dependencies: resolve existing portal merge, verify authentication and database isolation,
and deploy the correct schema before exposing new member workflows.

- [ ] Finish current portal integration and rerun tests on the merged revision.
- [ ] Certify migrations and row-level security against a fresh database.
- [ ] Verify the deployed revision, migration ledger, and two-member isolation with controlled identities.
- [ ] Implement design uploads with ownership, size/type limits, and safe artifact handling.
- [ ] Attach build reports to exact design, machine, and process revisions.
- [ ] Track generated, checked, printed, measured, and field-tested evidence as separate attributes.
- [ ] Require measurement records before displaying measured-fit claims.
- [ ] Preserve failed builds and allow corrections without silently replacing history.
- [ ] Support export/deletion policies for member designs and measurement data.
- [ ] Define moderation, abuse reporting, and provenance for community contributions.
- [ ] Obtain contributor permission before reusing private designs or measurements for research.

## Research track — Separate from alpha promises

- [ ] STEP/B-rep backend: choose supported operations and verify actual solid geometry and external import.
- [ ] Arbitrary component extraction: evaluate known dimensions, uncertainty, and failure cases on a held-out dataset.
- [ ] General assembly planning: specify a bounded problem and compare with declared baselines.
- [ ] Learned prompt interpretation: freeze evaluation inputs and reject proposals that fail the typed contract.
- [ ] Simulation integration: verify solver setup, boundary conditions, reference problems, and artifact provenance.
- [ ] Formal proofs: specify exactly which properties and geometry representations are covered.
- [ ] Optimization research: freeze objectives, budgets, and baselines before evaluating outcomes.
- [ ] Publish negative results and distinguish mathematical guarantees from sampled checks.

## First integrated milestone

Build P1 around one supported enclosure family before broadening geometry support.

- [ ] A user resolves a contract and locks its mounting interface.
- [ ] NeuroCAD generates a dimensionally equivalent fit sample.
- [ ] The user records real measurements with process metadata.
- [ ] Compensation produces a new, inspectable revision of the complete enclosure.
- [ ] Validation detects a deliberately introduced fit or wall violation.
- [ ] A second clean installation reproduces and verifies the delivered bundle.
- [ ] A physical build is measured against declared acceptance dimensions.
- [ ] Report completion time, user interventions, failed attempts, and fit results without omitting failures.

Expansion decision: proceed to another part family only after this workflow has
repeatable acceptance evidence and observed user demand. Feature count is not
an acceptance metric.
