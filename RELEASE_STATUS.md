# NeuroCAD Release Status

Target: `v0.5.0a6` public alpha.

Current state: **public main candidate, not a tagged release** (checked 2026-09-09).
PR #49 merged as `cc8c534412701439da0d346b5445b37dc8f74122` after all twelve checks
passed on implementation head `8fed84a362d673cd302e97fa2c711115c54066d4`.
The [GitHub handoff](docs/GITHUB_HANDOFF_20260909.md) records exact CI, anonymous
installation and end-to-end acceptance. The [final checklist](docs/FINAL_9_OF_10_CHECKLIST.md)
retains earlier local verification and its limitations. Future changes still
require fresh CI; older successful checks do not cover a new commit.
Earlier GitHub jobs did not start because of an owner billing/spending restriction.
Fresh public-repository jobs now run. The first integration run found a Windows
test-harness encoding error; the correction uses explicit UTF-8 and is protected
by a maintained-source encoding regression. Required checks are not waived.
See [quick start](docs/QUICKSTART.md)
for local installation. The application remains an explicitly bounded alpha.
No `v0.5.0a6` tag, published release provenance receipt, or anonymous tagged-release
installation receipt exists. Anonymous source download, clean installation, rounded-enclosure STL
compilation and independent bundle verification passed for the merged implementation.
Immutable release bootstrap still awaits a verified tag and release.

## Implemented release surface

- Strict millimetre-based dimension parsing.
- Fully dimensioned plates, boxes, open-top rectangular enclosures, and basic primitives.
- Explicit hole count/diameter and rectangular slot count/dimensions.
- Word-boundary domain matching and rejection of unsupported prompts.
- Semantic validation with actionable nonzero failures.
- OpenSCAD, JSON manifest, and compiled/watertight-verified STL output.
- Prompt-title sanitization and bounded `$fn` input.
- Atomic SCAD writes.
- Versioned canonical IR, strict schema/semantic validation, deterministic round trips, hierarchy, transforms, Boolean composition, and constraints.
- IR compilation/evaluation, deterministic benchmark, and real local workbench.
- Workbench project save/reopen with revision history, per-part SCAD/IR downloads,
  tab-local mode drafts, stale-request protection, and retryable compiler errors.
- Bounded structured inputs, hierarchy depth limits, and fail-closed malformed-value handling.
- Dependency/static security gates and nonce-based demo browser security headers.
- Python package, CLI, installer, CI, fresh-wheel smoke gate, and release workflow.
- Typed electronics enclosures with explicit lids, cutouts, vents, PCB references, and standoffs.
- Versioned project edits, fabrication preflight, coupon calibration, and request-level mesh probes.
- Independently verifiable native enclosure bundles with strict inventory, hash, regeneration, and mesh-evidence checks.
- Independently verifiable exchange bundles and honest file handoffs for OpenSCAD, KiCad, mesh CAD tools, Blender, and common slicers.
- Source-reverified bounded KiCad parsing for rectangular outlines, board thickness, and explicitly named round mounting-hole footprints, with mandatory reviewed connector/height facts.
- Byte-reproducible wheel and normalized source-distribution builds, enforced by double-build comparisons in CI and release.

## Required before announcing the public alpha

1. Review the final changes and pass CI on the exact candidate: Python
   3.10/3.11/3.12 Linux kernel checks, portable checks, and all three browsers.
2. Retain the passing reviewed revision on main. The owner has made the intended
   repository public and requested PR management; this does not waive CI or
   independent scientific-review gates.
3. Tag that passing main commit `v0.5.0a6`. The tag workflow now requires browser
   acceptance before running release tests, fresh installations, reproducible
   builds, extracted-sdist tests and the complete controlled research execution.
4. Verify the attached artifacts against generated `SHA256SUMS` and
   `RELEASE_PROVENANCE.json`, retain the workflow URL, and confirm the GitHub
   release is marked **prerelease**. Do not copy local candidate hashes into a
   published release receipt.
5. From a clean credential-free environment, fetch the public installer and
   release, verify checksums, install, run doctor, and generate/compile/verify
   an enclosure. Announce the alpha only after this anonymous-install gate passes.

## Explicit non-goals

- General-purpose or production CAD replacement.
- STEP/BREP, arbitrary sketches, or assemblies. Analytical independent/correlated
  tolerance stacks are implemented; empirical fit guarantees are not.
- Slide lids, hinges, snap fits, threads, or automatically certified fits.
- Engineering simulation or safety certification.
- Production aircraft, vehicle, motor, furniture, medical, or safety-critical parts.
