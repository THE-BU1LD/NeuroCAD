# C3D constructed verification evaluation

This release freezes 17 constructed regression cases for the existing C3D planar
wall revision pilot: five feasible wall edits and twelve geometric, requirement,
or binding failures. It extends verifier coverage within the same component
family. It is not a held-out benchmark of AI generation or new design families.

## Run and retain evidence

Use Python 3.11 through 3.14 and a new output directory:

```bash
python -m pip install -e '.[exact-build123d,mesh-gmsh]'
python scripts/evaluate_c3d_revision.py /absolute/path/to/new-evidence --mesh
```

Gmsh requires its native system libraries; Linux typically needs libGLU and
libXft. Omit `--mesh` only when intentionally evaluating CAD alone. The report
then states `not_run`; geometry acceptance does not imply successful meshing.

The manifest is `docs/examples/c3d_revision/evaluation-v1.json`. It specifies
expected decisions before execution. The runner retains its exact bytes,
baseline inputs, generated candidate programs, requirements and bindings,
commands, return codes, stdout/stderr, per-case results, exported STEP bundles,
reopened geometry checks, and an artifact SHA-256 inventory.

Five positive cases use 1.5, 2.5, 3, 4 and 8 mm walls. Twelve negative cases cover
a thin wall overlapping the cutout, zero and negative cavities, moved/resized/
removed cutouts, width/height/depth changes, a false wall requirement, a relaxed
frozen width tolerance, and a stale Feature IR binding hash. Impossible cavity
dimensions remain raw negative-test intent and fail strict parsing.

An expected rejection passes only with the normal CLI error exit, a declared
error category, no published candidate and an unchanged accepted baseline.
Unrelated capability errors, crashes and timeouts are not successful rejections.
The runner exits nonzero if any decision differs from the manifest. Partial
artifacts are retained if execution is interrupted; an incomplete run has no
successful overall report.

Every accepted STEP is independently reopened and checked for a valid manifold
single solid and its exact requirements. When requested, the 3 mm candidate is
meshed through the supervised native worker; the separate mesh receipt records
settings, STEP/mesh hashes, connectivity and physical-group round-trip checks.
This does not certify solver convergence, manufacturing, load capacity, safety,
general CAD equivalence, Cubit integration or learned-model generalization.

The original frozen acceptance fixture, core verifier and tolerances are
unchanged. To extend beyond this release, freeze external design families and
independent ground truth before changing model or verifier behavior.
