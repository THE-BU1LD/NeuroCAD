# NeuroCAD / Coreform diagnostic capture protocol

**Version 1.0 · 1 October 2026 · protocol and software validation only**

## Purpose and evidence boundary

Turn the Coreform feedback into a reproducible record that separates an imported model, geometry validation, any repair, and a subsequent tetrahedral-meshing attempt. This package does not contain a real Cubit run, a downloaded assembly, a measured meshing result, or a NeuroCAD–Cubit integration.

Source: Kimberly White's October 1 reply in the existing “NeuroCAD x Coreform: one geometry-to-meshing failure case” correspondence. The diagnostic recommendations below summarize that reply. The proposed public case is the Rimac GBX-700 assembly suggested in the preceding Coreform message. Its reported overclosures and housing watertightness issues are Coreform's account, not independently reproduced findings here.

Public case reference: https://grabcad.com/library/rimac-automobili-gbx-700-1

Canonical NeuroCAD reference from the existing outreach: https://github.com/THE-BU1LD/NeuroCAD

A publicly accessible model is not automatically licensed for redistribution. Verify the actual file's terms and the right to use the required software before a real experiment. Do not purchase a licence, request proprietary data or provision paid compute under this protocol. The currently described NeuroCAD output route uses OpenSCAD; no Cubit or IGA integration is asserted.

## 1. Preserve the import before changing it

Store the as-imported model under an immutable baseline filename. Record its SHA-256, source reference, file format, import settings, units, Cubit version and target mesh size. Capture what import actually did rather than reconstructing defaults from memory later. Note whether automatic healing or other transformations occurred during import; “as imported” is not necessarily byte-identical to the original downloaded source file.

Preserve the original downloaded file separately when permitted, with its own checksum. The first experiment should not overwrite it, the as-imported baseline or previous logs. Case capture is local and private by default; redact machine/user paths before any public release.

## 2. Record geometry validation independently

Coreform recommended running:

```
validate volume all verbose
```

Run that command only in an authorized compatible Cubit environment after confirming the loaded model and units. Save the actual complete output, command/procedure and model identity. This package records the recommendation but does not execute the command or certify its compatibility with a locally installed version.

Use Geometry Power Tools as appropriate to inspect small curves, small surfaces and bad angles. Record the numerical thresholds, their units, and how they relate to the intended mesh size. Do not use a different threshold on a later case merely to turn a failure into a pass without documenting a separately scoped development change.

For an assembly, record gaps, overlaps and misalignments. Distinguish intended clearances and contact interfaces from defects. A gap is not automatically an error; the intended physical and meshing relationships matter.

## 3. Keep repairs separate from the baseline

If invalid ACIS geometry is flagged, investigate healing on a copy of the affected volumes and repeat the checks. Save the repaired model under a distinct filename and checksum. Record each operation, its purpose and any changed dimensions, topology or interfaces. Keep defeaturing separate from baseline evaluation.

Only imprint or merge interfaces where shared mesh nodes are intended. Do not silently remove design clearances, alter acceptance geometry or transform an infeasible constraint into a different easier model. Existing NeuroCAD boundary/cutout and feasibility invariants remain in force; this protocol does not relax them.

A repaired model that passes a geometry check does not retrospectively make the original model valid. Record both states.

## 4. Record meshing as its own experiment

Use a separate tet-meshing stage. Record the actual model basis (as-imported or repaired), meshing procedure, settings, target size, relevant version, output/error log and runtime when measured. Retain failures and incomplete runs.

Do not infer meshability from a geometry-validation pass. Do not infer analysis suitability from the existence of a mesh. Analysis suitability requires its own problem-specific criteria and evidence, which are outside this first capture protocol.

## 5. Manifest contract

`validate_capture.py` checks capture structure and file identities. It does not run Cubit or interpret whether a reported result is scientifically correct.

Required top-level fields:

| Field | Meaning |
|---|---|
| `schema_version` | Integer 1. |
| `case_id` | A stable local case identifier, not a participant identifier. |
| `purpose` | `DEVELOPMENT_CAPTURE` or `SYNTHETIC_SOFTWARE_TEST`. |
| `cubit_version`, `input_format`, `units` | Actual recorded environment and geometry-unit information. |
| `source_reference`, `rights_status` | Provenance and documented rights status; the validator does not certify a licence. |
| `import_settings` | Object containing explicit known import settings. |
| `target_mesh_size` | Positive finite number in the recorded units. |
| `interface_assumptions` | Intended clearances, contacts and shared-node boundaries. |
| `repair_description` | What was done, or an explicit statement that no repair was performed. |
| `mesh_settings` | Actual settings or an explicit not-run statement. |
| `as_imported_model` | Relative file path plus SHA-256 of the preserved baseline. |
| `repaired_model` | Separate relative file/hash record, or null when none exists. |
| `stages` | Three independent records: `geometry_before`, `geometry_after`, `tet_meshing`. |

Each stage has one of `NOT_RUN`, `REPORTED_PASS`, `REPORTED_FAIL`, or `INCONCLUSIVE`. All non-NOT_RUN stages require an actual local evidence file/hash, the command/procedure and an interpretation. Geometry-after also requires a separate repaired model; tet-meshing must identify which model it used. Verdicts remain operator-reported even when evidence is correctly hashed.

A NOT_RUN stage must not contain claimed output evidence. A successful manifest check can therefore describe an entirely unrun real experiment. That is an integrity pass, not a geometry pass.

## 6. Local commands and sample

```
python -m unittest discover -s tests -v
python validate_capture.py example_capture/capture.json
```

The delivered `example_capture` contains explicitly labeled synthetic text, not CAD. Its valid manifest has all three stages NOT_RUN. It exists to demonstrate the file contract and command behavior without fabricating an experiment.

The validator is read-only, uses Python's standard library, does not access the network and does not launch software. It rejects paths escaping the capture directory, symlinks, changed hashes and evidence larger than 256 MiB per file. These checks are a bounded convenience, not a complete security audit. Large real-case handling needs a separately reviewed storage path; do not increase limits to move unauthorized data.

## Acceptance and next action

A handoff is useful when a reviewer can recover the exact baseline, distinguish it from the repair, identify the model used for meshing, and locate the real outputs. The next real experiment still needs an authorized Cubit environment, lawful access to the model, agreed interface assumptions, and a person able to inspect geometry and mesh results.

Route a narrowly reproducible technical question to Coreform's forum, as they requested: https://forum.coreform.com/

Keep any possible promotion separate from benchmark evidence. No partnership, technical approval, promotion commitment or successful integration is implied by the feedback.
