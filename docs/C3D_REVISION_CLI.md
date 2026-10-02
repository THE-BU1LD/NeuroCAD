# Verified C3D wall thickness revisions

The `feature revise` command exposes the existing frozen C3D v0.1 acceptance API.
It accepts strictly parsed Feature IR, Requirement IR, and hash-bound bindings,
requires build123d, and publishes a new verified STEP bundle only after every
geometry and provenance check passes. It preserves the accepted baseline.

The supported pilot is one XY planar sketch followed by one extrusion: an
80 × 60 × 20 mm envelope, one rectangular internal cavity, and an unaffected
radius-0.4 mm circular cutout centered at (-39, 10) mm. The baseline wall is
2 mm; the feasible revision is 3 mm. Only `wall_thickness` may change.
Comparison axis/side and numerical tolerances remain frozen by
`tests/fixtures/c3d_revision_integrity_v01.json`; the CLI has no override flags.

From a source checkout with Python 3.11–3.14:

```bash
python -m pip install -e '.[exact-build123d]'
python scripts/reproduce_c3d_revision.py /absolute/path/to/new-pilot-evidence
```

This runs the real CLI, keeps editable input programs and the frozen contract,
builds a verified baseline, publishes the feasible revision, rejects the 40 mm
request, compares baseline hashes, and independently reopens the final STEP and
rechecks requirements. It retains commands, stdout/stderr, dependency versions,
geometry receipts, a verification report, and an artifact hash inventory.
Existing output directories are refused.

For individual operations from the checkout:

```bash
neurocad feature build docs/examples/c3d_revision/baseline.ncad2.json \
  --requirements docs/examples/c3d_revision/baseline.requirements.json \
  --bindings docs/examples/c3d_revision/baseline.bindings.json \
  --output-dir accepted-baseline

neurocad feature revise \
  docs/examples/c3d_revision/baseline.ncad2.json \
  docs/examples/c3d_revision/candidate.ncad2.json \
  --baseline-bundle accepted-baseline \
  --baseline-requirements docs/examples/c3d_revision/baseline.requirements.json \
  --baseline-bindings docs/examples/c3d_revision/baseline.bindings.json \
  --candidate-requirements docs/examples/c3d_revision/candidate.requirements.json \
  --candidate-bindings docs/examples/c3d_revision/candidate.bindings.json \
  --output-dir accepted-revision
```

Success prints finite JSON containing both `build_receipt` and
`revision_integrity`. The new bundle contains STEP, build receipt, requirements,
bindings, requirement-verification evidence, and `revision-integrity.json`.
Editable Feature IR is retained separately in the reproduction package and is
bound by its canonical hash in the receipts; STEP alone does not preserve the
parametric feature history.

The 40 mm example intentionally derives a 0 × -20 mm cavity. Its raw input is
retained for the negative test; the strict Feature IR parser rejects it before
construction. Its bindings deliberately retain baseline intent, not a claim of
accepted invalid geometry. The underlying API's exact-construction rejection is
also covered by the existing kernel tests. Neither path publishes a candidate.

Tests cover real successful publication, invalid geometry, output inside the
baseline, existing output, tampered baseline, missing optional capability,
strict malformed input, and forbidden contract overrides. Unsupported geometry
fails closed. This is engineering evidence for a bounded pilot, not general CAD
equivalence, physical validation, manufacturability, or simulation.
