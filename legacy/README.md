# NeuroCAD legacy archive

This directory preserves disconnected historical experiments and generated
outputs for negative evidence and forensic reference. Nothing under `legacy/`
is part of the supported `neurocad-research` package, maintained test suite, or
release API.

- `python/` contains abandoned kernels, research prototypes, and unsafe
  import-time test scripts formerly stored at repository root.
- `generated/` may contain locally retained, ignored SCAD, STL, OBJ, STEP-labelled,
  CAD, and ZIP outputs. These are not guaranteed checkout inputs or test fixtures.
  Historical committed originals remain available through canonical Git history.
  Their presence is not evidence of correctness or reproducibility.
- `generated/output_models/` and `generated/test_output/` preserve the two
  historical output directories; they are not current release artifacts or
  test fixtures.

Do not add this directory to `PYTHONPATH` or treat its scripts as production
entry points. Historical failures and the refuted pseudo-STEP path remain
documented in `audits/HISTORICAL_TRUTH.md`.
