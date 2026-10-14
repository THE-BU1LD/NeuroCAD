# Exact CAD and tagged mesh acceptance

`python scripts/verify_native_acceptance.py NEW_DIRECTORY` builds five authored
reference programs, exports and re-imports STEP, and compares topology, extents
and volume with analytic expectations. The beam, four-hole patterned plate and
open enclosure also run twice through the supervised Gmsh worker. Each retained
MSH is audited with a coordinate-determinant tetrahedral volume sum.

The cases are a dimensioned rectangular sketch/extrusion, actual two-axis linear
hole patterns, a revolved stepped bottle-like solid, a box with vertical edge
fillets, and an open enclosure with a chamfered front-wall port. The contract is
`research/development/native_acceptance_20261014/contract.json`. Linux, macOS and
Windows execution receipts are required before calling the matrix complete.
Build receipts now also record the OCP distribution version. Revision evaluation
rejects a missing or mismatched kernel version; older baseline bundles must be
rebuilt and retained separately before continuing a revision.

For named planar boundary roles, supply `--boundary-roles roles.json` to
`neurocad-mesh step`. The file has this structure; replace the source digest with
the SHA-256 of the exact input STEP bytes:

```json
{
  "source_step_sha256": "<64 lowercase hexadecimal characters>",
  "roles": {
    "fixed_end": {"axis": "x", "side": "min", "expected_surfaces": 1},
    "loaded_end": {"axis": "x", "side": "max", "expected_surfaces": 1}
  }
}
```

The selector finds planar faces on the specified extreme of the imported
geometry, within 1e-6 mm. It checks the declared face count. No match, an
unexpected count, stale source hash or raw index rejects the bundle. Role names
do not themselves apply forces, supports, materials or solver conditions.
Curved/interior faces and arbitrary semantic inference are outside this first
vocabulary. Kernel tags appear only in the result receipt as observed bindings.

`semantic-groups.json` binds the request, selected faces, source and mesh hashes,
tolerance and deterministic settings. Existing serialization verification checks
all physical-group memberships; the supervisor checks the role receipt and
binds its hash into `execution-receipt.json`. The default path retains the
original three-file bundle. A tagged bundle adds the semantic group receipt.

The mesher explicitly selects one thread, first-order elements, random seed 1,
2D algorithm 6 and 3D algorithm 1. These settings use the
[Gmsh 4.15.2 API](https://gmsh.info/doc/texinfo/). Repeats compare mesh invariants
within one pinned environment; STEP/MSH bytes need not match across platforms.
The native worker timeout and existing file/element bounds remain in force;
they are not a hard RAM limit or a whole-command deadline.

This is internal engineering acceptance. It establishes no solver convergence,
physical accuracy, manufacturability, independent reproduction or user outcome.
Earlier frozen protocols and failure receipts remain authoritative for their
original source versions. The public alpha tag is unchanged.
