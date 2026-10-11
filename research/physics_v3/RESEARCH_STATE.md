# NeuroCAD Physics v3 research state

**State:** `ENGINEERING_IMPLEMENTED_SCIENTIFIC_VALIDATION_NOT_STARTED`  
**Date:** 2026-10-11

Physics v3 is a bounded engineering successor to the tagged Physics v2
provenance study. It adds six analytical or small-network models, a
temperature-aware provenance contract, reusable load combinations, three
generic uncertainty methods, and honest component-level result annotations.
The 2026-10-11 engineering extension also adds canonical composite generation
for hollow shafts, I-beams, L-brackets, and perforated plates, with exact
idealized section/mass properties and bounded structural screening.

The implementation does not modify or reinterpret the frozen v2 protocol,
216-case result, release archive, paper, or `physics-v2-v1.0.0` tag. v2's
external reproduction and arXiv submission remain separate open actions.

The v3 evidence currently supports only code behavior and closed-form
conformance. No protected v3 study, experimental validation, independent
reproduction, paper, or arXiv submission has occurred. FEA and CFD remain
unimplemented because there is no identified external solver, mesh/convergence
receipt, boundary-condition manifest, or validated result-file pipeline.

Engineering verification completed with 1,225 passing tests and 9 expected
skips, a full in-scope Ruff pass, and MyPy passing across 75 source files. Four
canonical complex-shape examples also compile as single, finite, watertight,
winding-consistent volumes with no detected non-adjacent triangle
intersections; exact hashes and measurements are recorded in
`COMPLEX_SHAPE_VERIFICATION.json`. These are software and tessellated-kernel
receipts, not physical, FEA, safety, or independent scientific evidence.

See [FEATURE_MATRIX.md](FEATURE_MATRIX.md) for the capability-by-capability
status and [../../docs/PHYSICS.md](../../docs/PHYSICS.md) for the request
contracts and runnable examples.
