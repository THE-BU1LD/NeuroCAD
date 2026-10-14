# NeuroCAD Release Status

## Current version routing — 2026-10-13

See [CURRENT_STATUS.md](CURRENT_STATUS.md) for the current version index.
The original compiler study remains terminal mixed. Physics v2 has a separate
controlled 216-case result and local tagged research package; Physics v3 has
engineering receipts only. Neither upgrades the predecessor or establishes
independent or physical validation. The historical assessment below retains its
dated scope and must not be read as an inventory of all later implementations.

Target: `v0.5.0a6` public alpha. Execution date: 2026-10-14.

**Status: release candidate undergoing full hosted verification.**
[PR #103](https://github.com/THE-BU1LD/NeuroCAD/pull/103) carries the candidate.
A release is ready only when its exact source commit passes the required matrix,
the tag workflow publishes checksum-bound artifacts as a prerelease, and the
anonymous installation job passes. Check the
[release page](https://github.com/THE-BU1LD/NeuroCAD/releases/tag/v0.5.0a6) and
[release workflow](https://github.com/THE-BU1LD/NeuroCAD/actions/workflows/release.yml)
for publication receipts; this source document is not a publication receipt.

Enclosure-only CI passed on `6151d93` (run `38426643691`). The first full matrix
(run `38494422164`) found a test lint defect and an unsupported Windows import of
the POSIX research harness; all three browsers and build123d passed. These failures
are retained under `docs/verification/alpha-20261014/`. Replacement CI is required.
Repository-only frozen study tests need Unix resource accounting and Git/study
sources; they do not ship in the sdist. Product physics tests remain portable.

See [quick start](docs/QUICKSTART.md) for source installation and the public
release procedure. Historical September verification is retained in
[the handoff](docs/GITHUB_HANDOFF_20260909.md), scoped to its original commit.

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
5. The post-publication anonymous job fetches the public installer, verifies
   tag/source identity and published artifact checksums, installs the wheel, runs
   doctor and edited compiled-enclosure acceptance, then tests the default
   tagged-source installer path. Both use fresh environments without download
   credentials. Announce only after this job passes. Persistent OS service setup
   and physical fit are outside this installation receipt.

## Explicit non-goals

- General-purpose or production CAD replacement.
- STEP/BREP, arbitrary sketches, or assemblies. Analytical independent/correlated
  tolerance stacks are implemented; empirical fit guarantees are not.
- Slide lids, hinges, snap fits, threads, or automatically certified fits.
- Engineering simulation or safety certification.
- Production aircraft, vehicle, motor, furniture, medical, or safety-critical parts.
