# NeuroCAD Release Status

Target: `v0.5.0a6` public alpha.

Current state: **private review candidate, not a published release** (checked
2026-09-09). PR #49 is open and draft at `a870c12920483f66c98628fac92b892cdadab7f3`;
its nine existing checks passed. Local HEAD is `d22172a` plus the publication
hardening changes described in the [final checklist](docs/FINAL_9_OF_10_CHECKLIST.md).
Those changes require fresh remote CI and review. See [quick start](docs/QUICKSTART.md)
for local installation. The application remains an explicitly bounded alpha.
No `v0.5.0a6` tag, published release provenance receipt, or anonymous-install receipt
exists. Private repository visibility still prevents anonymous bootstrap.

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
2. Obtain owner approval for merge and public visibility; retain the reviewed
   revision on main and confirm the intended repository is public.
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
