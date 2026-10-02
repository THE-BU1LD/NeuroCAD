# Rimac GBX-700 dirty-CAD capture lane

This directory is a **pre-execution capture scaffold** for GitHub issue #78.

It contains no downloaded CAD, Cubit output, repair result, or mesh result. The public
GrabCAD page is only a source reference. Do not commit a third-party model unless its
actual licence/terms permit redistribution.

## Before first outcome-producing run

1. Verify lawful access and redistribution/storage terms for the exact source file.
2. Record the original download identity and SHA-256 privately.
3. Import in an authorized compatible Cubit environment.
4. Preserve the resulting **as-imported** model under a new immutable filename.
5. Replace every placeholder in `capture.template.json`:
   - Cubit version;
   - actual input format;
   - units;
   - import settings;
   - target mesh size;
   - interface assumptions;
   - local baseline path and SHA-256.
6. Rename the completed manifest to `capture.json`.
7. Run:
   ```bash
   python scripts/validate_coreform_capture.py research/captures/rimac_gbx700/capture.json
   ```

A structural validation pass is **not** a geometry pass. It only establishes that
the capture has internally consistent provenance and evidence references.

## Frozen stage order

### geometry_before

Run and retain the declared geometry checks on the untouched as-imported baseline.
Coreform's recommendation includes `validate volume all verbose`, plus appropriate
Geometry Power Tools checks with thresholds explicitly tied to target mesh size.

### geometry_after

Only run this stage if a distinct repaired/healed derivative exists. Never replace
or mutate the baseline. Record repair operations and hash the derivative separately.

### tet_meshing

Run meshing as a separate experiment and identify whether the basis was the
`as_imported_model` or `repaired_model`. Retain failure logs as evidence.

Do not infer meshability from geometry validation and do not infer simulation
suitability from successful meshing.

## Publication boundary

Before any public release, redact machine/user paths and verify that every retained
third-party artifact may legally be redistributed. It is acceptable for the public
repository to retain only hashes, commands, logs, and derived summaries when the
underlying source geometry cannot be redistributed.
