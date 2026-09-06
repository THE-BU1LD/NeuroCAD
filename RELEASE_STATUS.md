# NeuroCAD Release Status

Target: `v0.5.0a6` public alpha.

Current state: **pending**. Source metadata declares a6. Local a6 wheel/sdist
candidates have been built and installed successfully from this working tree,
but they are deliberately outside the historical `dist/` snapshot. A new local
Git baseline was initialized during the 2026-09-06 audit; it does not recover
the missing historical repository. There is still no external CI result, tag,
generated release provenance receipt, or public-install receipt.

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
- Bounded structured inputs, hierarchy depth limits, and fail-closed malformed-value handling.
- Dependency/static security gates and nonce-based demo browser security headers.
- Python package, CLI, installer, CI, fresh-wheel smoke gate, and release workflow.
- Typed electronics enclosures with explicit lids, cutouts, vents, PCB references, and standoffs.
- Versioned project edits, fabrication preflight, coupon calibration, and request-level mesh probes.
- Independently verifiable native enclosure bundles with strict inventory, hash, regeneration, and mesh-evidence checks.
- Independently verifiable exchange bundles and honest file handoffs for OpenSCAD, KiCad, mesh CAD tools, Blender, and common slicers.

## Required before announcing the public alpha

1. Make the repository public and confirm the anonymous source and installer URLs.
2. Run the exact release commit through CI on Python 3.10, 3.11, and 3.12.
3. Run the installer from a clean credential-free environment.
4. Confirm the compiled OpenSCAD/STL smoke test on Linux.
5. Confirm that CI generated `SHA256SUMS` and `RELEASE_PROVENANCE.json` from the
   exact newly built artifacts; do not manually copy candidate hashes into docs.
6. Tag the passing commit `v0.5.0a6`, verify attached distributions, and retain
   the generated provenance receipt and CI URL.

## Explicit non-goals

- General-purpose or production CAD replacement.
- STEP/BREP, arbitrary sketches, assemblies, or tolerance stacks.
- Slide lids, hinges, snap fits, threads, or automatically certified fits.
- Engineering simulation or safety certification.
- Production aircraft, vehicle, motor, furniture, medical, or safety-critical parts.
