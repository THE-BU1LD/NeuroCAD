# Failures and negative evidence

- The historical typed-parser causal claim is falsified; Stage 1 used scripted
  fixtures and made no model calls.
- A historical STEP exporter emitted marker text. It is hard-disabled and archived;
  NeuroCAD has no STEP/BREP backend.
- The retained FULL run cannot authenticate its producing source and reused 181
  kernel artifacts.
- A sandboxed fresh run produced valid meshes but PNG rendering failed because
  OpenSCAD could not create `NSOpenGLContext`. Native execution passed; preflight
  now catches this environment failure before expensive work.
- The first challenge evaluator crashed on an ambiguous must-reject prompt rather
  than recording rejection. Exception classification was fixed and regression
  tested without changing the frozen dataset.
- Independent benchmark, external replication, physical fit, authorized model
  outcomes, and public exact-release evidence do not exist.

See `../audits/HISTORICAL_TRUTH.md` for the preserved historical ledger.
