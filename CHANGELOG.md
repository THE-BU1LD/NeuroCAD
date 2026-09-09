# Changelog

## 0.5.0a6 - unreleased candidate

This candidate remains pending until the exact source revision passes the
integrated CI, distribution, clean-install, and release-provenance gates in
`RELEASE_STATUS.md`.

- Matched lid and insertion-plug corner radii to rounded enclosures, cleared screw
  boss rings beneath lid plates, and reserved insertion depth in floor, standoff
  and PCB-envelope validation. Added independent negative mesh-clearance probes.
- Corrected rounded-box limits (zero radius, tiny radius, disk and capsule) and
  bounded standoff attachment overlap within thin explicit floors.
- Preserved validated project/source downloads when compilation fails.
- Recorded bounded-export rejections as negative research evaluation results
  instead of aborting the full stress campaign or changing its generated fixtures.
- Preserved canonical S3 pre-outcome controls during remote-branch reconciliation
  and included their candidate-pool fixture in the tested source distribution.
- Updated public-source onboarding, expanded CI/release checks to every maintained
  script, and retained per-Python test results even when a job fails.
- Required three-browser kernel acceptance before tag publication; alpha/RC
  releases are explicitly marked prerelease and cannot become the latest stable
  release. Added execution of tests from the built source archive.
- Included retained helper sources in the sdist, separated the two checkout-only
  archive checks, and rejected symlink, duplicate, case-colliding and unsafe
  cross-platform archive entries.

- Hardened canonical IR parsing against duplicate keys, excessive nesting, non-finite or out-of-range values, non-string metadata keys, and inexact constraint payloads.
- Closed prompt fail-open cases involving implicit zero-value defaults, arbitrary three-number text, ambiguous dimension sequences, substring-based unsupported-feature matching, and unbounded or overlapping plate features.
- Invalid prompt analysis no longer produces a canonical program or OpenSCAD payload; export APIs reject it explicitly.
- Added strict artifact path, timeout, and mesh-tolerance validation and rejected ambiguous flat Boolean exports.
- Added static type checking across maintained product, research protocol, and retained helper modules; the configured gate must pass before release.
- Strengthened CI/release configuration with complete helper coverage, source-distribution smoke installation, tag/version agreement, and generated release checksums.
- Expanded the maintained regression suite with adversarial parser, IR, geometry, API, artifact, and workflow-integrity coverage.
- Added a typed electronics-enclosure workflow with screw/friction lids, face cutouts, vents, PCB envelopes, hardware-aware standoffs, semantic revisions, manufacturing preflight, and request-level STL probes.
- Added strict semicolon-delimited enclosure language plus a schema-gated provider-payload adapter; unsupported or ambiguous clauses fail closed.
- Added evidence-bounded printer coupon calibration with robust scale, hole, and clearance recommendations and explicit application plans.
- Added honest OpenSCAD, KiCad, Fusion, Onshape, FreeCAD, Blender, and slicer file-exchange contracts without claiming native imports or documents.
- Added independent exchange-bundle revalidation and hash-bound KiCad PCB-envelope application as auditable project revisions.
- Added independent native enclosure-bundle verification for manifest shape, complete file inventory, hashes, regenerated IR/OpenSCAD/preflight, and current compiled-mesh evidence.
- Embedded generated standoffs into enclosure floors by a small internal overlap to avoid fragile face-contact unions and pathological OpenSCAD Boolean time.
- Replaced the generic demo landing state with a strict enclosure workbench that exposes the interpreted specification, body/lid IR and SCAD, validation, and manufacturing preflight without inventing unsupported geometry.
- Refused non-loopback demo binding without explicit opt-in, rejected unrecognized loopback Host headers to reduce DNS-rebinding exposure, and required release tags to point into `origin/main`.
- Added source-bound KiCad receipts plus a bounded native-file parser for rectangular Edge.Cuts, thickness, and explicitly named round mounting-hole footprints. Source-derived fields are re-extracted before use; connector inventory and maximum height remain mandatory reviewed facts.
- Flattened enclosure standoff Booleans into one positive union and one bore subtraction, reducing the maintained real-kernel regression from roughly 99 seconds to under 50 seconds on this audit machine while preserving mesh checks.
- Moved 113 disconnected historical Python experiments and 44 generated root artifacts into an excluded, read-only-by-convention `legacy/` archive instead of shipping or presenting them as product surface.
- Added a frozen physical-validation protocol for independent print runs, dimensional coupons, hardware fit, lid cycling, retained failures, photos, and hash-bound receipts; no physical result is claimed before that protocol is executed.
- Replaced the version-only research environment snapshot with a reviewed direct-input file and a universal distribution-hash lock; reproduction and release install it in pip hash-checking mode.
- Made wheel and normalized source-distribution artifacts byte-reproducible from the release commit timestamp and enforced double-build comparison gates.

## 0.5.0a5 - 2026-09-04

- Hardened retained curve, surface, vector-field, and abstract pipeline contracts with explicit finite-value, shape, count, and zero-vector validation.
- Added legacy-contract regression tests for retained geometry helpers so malformed values fail closed instead of producing undefined math behavior.
- Reconciled release, truth, evidence, and research documentation to the new local alpha candidate.
- Added integrity coverage against stale release claims and stale test-count claims in maintained completion documents.

## 0.5.0a4 - 2026-09-03

- Strengthened STL acceptance with finite-vertex, positive-volume, winding, single-body connectivity, and expected-dimension checks.
- Expanded executable evaluation from 12 samples toward the complete 240-task compiler benchmark, with identity-checked, hash-recorded interrupted-run resumability.
- Added a real integrity suite that prevents fake STEP and incomplete legacy code from entering the supported distribution and keeps negative research claims visible.
- Brought the VeriCodeGen methodology subsystem under Ruff and Bandit gates and made its no-Git failure path explicit and non-traceback-producing.
- Expanded CI to full Python 3.12 tests on Linux, macOS, and Windows while retaining Python 3.10–3.12 Linux/OpenSCAD coverage.
- Added project truth, objective definition-of-done, evaluation, closure, and S3 pre-outcome receipts.
- Replaced the legacy fake STEP writer with an explicit unsupported-format error so direct legacy use cannot create a misleading `.step` file.

## 0.5.0a3 — 2026-09-02

- Added a frozen, one-command controlled research suite with seven new `NC-EXP-*` experiment IDs.
- Added 240-task compiler evaluation with retrieval, raw-number, and fixed baselines plus exact paired tests.
- Added 1,000-program IR stress, 240 malformed cases, constraint and editability experiments, hierarchy stress, and 12 OpenSCAD/STL kernel executions with actual PNG renders.
- Fixed singular `inch` parsing for named measurements and added regression coverage.
- Added the historical truth ledger, research question, representation/grammar, dataset and literature audits, statistical plan, error taxonomy, claim ledger, reviewer attack, full manuscript, and reproduction script.
- Preserved the falsified historical typed-parser claim and kept all current experiment IDs separate.

## 0.5.0a2 — 2026-09-02

- Made canonical IR validation fail closed for non-finite values, malformed direct-Python inputs, invalid constraint tolerances/vectors, and non-JSON metadata.
- Added an explicit 128-level hierarchy limit, iterative cycle traversal, and positive-volume intersection checks.
- Bounded canonical IR file/stdin reads to 1 MiB before decoding and added clean CLI I/O/timeout errors.
- Hardened the local demo with prompt/request limits, JSON media-type enforcement, CSP nonces, anti-framing/privacy headers, cached benchmark results, and safe threaded shutdown.
- Added dependency and static security gates; no known dependency vulnerabilities or medium/high static findings were observed.
- Expanded the maintained suite to 149 tests, including deterministic malformed-IR fuzzing, and removed the unused `core/constraints_py` assertion stub.

## 0.5.0a1

- Changed the internal and OpenSCAD length convention to millimetres.
- Added strict semantic rejection for unsupported and incomplete prompts.
- Added exact plate/enclosure dimensions, open-top wall thickness, hole count and
  diameter, rectangular slot count and dimensions, and deterministic placement.
- Added word-boundary classification and common adjective measurement phrasing.
- Added JSON design/validation manifests.
- Added OpenSCAD compilation, STL export, timeout handling, and watertight mesh
  verification.
- Added prompt-comment sanitization, bounded feature counts, bounded `$fn`, and
  atomic SCAD writes.
- Added product-focused CLI, parser, geometry, manifest, and mesh tests.
- Removed unsupported production-domain claims from release documentation.

This release intentionally rejects prompts accepted by 0.4.0a1 when their
dimensions or feature requirements are ambiguous.
