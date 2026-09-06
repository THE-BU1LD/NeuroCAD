# NeuroCAD research question

## Primary question

Can a deterministic, typed, fail-closed compiler convert inputs in a declared dimensioned-English CAD subset into semantically exact, editable CAD programs that round-trip without drift and execute as valid solids more reliably than trivial and retrieval baselines?

## Hypotheses

- **H1:** NeuroCAD's semantic-exact rate on the frozen controlled set is higher than a fixed-output baseline, a raw-number/no-unit-normalization baseline, and nearest-neighbor retrieval.
- **H2:** valid canonical programs round-trip exactly, validate all declared constraints, and export deterministically.
- **H3:** predeclared malformed-input categories are rejected with an explicit error rather than silently defaulted.
- **H4:** declared dimension constraints detect parameter corruption more often than the identical program with constraints removed.
- **H5:** a stratified sample of outputs executes through OpenSCAD and yields non-empty, watertight STL solids.

The null for H1/H4 is no paired advantage. H2/H3/H5 use an engineering acceptance criterion of 100% on the frozen controlled cases; uncertainty intervals describe the finite sample and do not imply population coverage.

## Measurable predictions and failure criteria

| Experiment | Prediction | Failure criterion |
|---|---|---|
| NC-EXP-001 | 100% semantic exactness; statistically better than each baseline by paired exact McNemar test where discordant pairs exist | Any NeuroCAD mismatch, or no advantage over the strongest baseline |
| NC-EXP-002 | 1,000/1,000 schema-valid, semantically valid, constraint-satisfied, exact round-trip, deterministic export | Any failure |
| NC-EXP-003 | 240/240 invalid cases rejected | Any silent acceptance |
| NC-EXP-004 | 100% corrupted-program detection with constraints and 0% without | Other rate |
| NC-EXP-005 | 200/200 automated parameter edits survive validation, round trip, and export | Any failed edit |
| NC-EXP-006 | 240/240 benchmark programs compile to STL passing finite-value, volume, watertightness, winding, single-body, and expected-extents checks | Missing kernel or any failed sample in the release run |
| NC-EXP-007 | Valid export through depth 128; explicit rejection at depth 129 | Crash, silent truncation, or wrong limit behavior |

## Scope

The study concerns a controlled compiler, not learned generation. It excludes sketches, images, BREP/STEP, fillets, arbitrary free-form language, constraint inference/solving, geometric similarity to human designs, manufacturability, and human usability. Train/validation/test labels characterize template and unit shifts; no training occurs for NeuroCAD.
