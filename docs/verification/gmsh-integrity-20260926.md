# Gmsh serialization and publication repair — 2026-09-26

## Scope and provenance

Stacked development repair for NeuroCAD PR #69, based on commit
`1a212ac05a3725e4297a672e3a3cbae923e76313`. No main-branch changes, merge,
production deployment, paid compute, solver-validity claim or research result.

The extracted parent backend was verified byte-for-byte against Git blob
`4eb2be16577f11123a15ceb4aca80f5f8a381515`. The parent contract tests were
verified against blob `df9a053ddc198adb4f5214a9f01ccfa2e2710174`.

## Reproduced defects

The old backend accepted 13 fake-adapter corruptions that preserved total node
and volume-element counts and physical-group names: coordinate changes,
volume/surface connectivity changes, missing surface elements, group membership
changes, node/element identities, entity membership, non-finite or incomplete
coordinates, malformed connectivity and duplicate node identities.

A fourteenth regression created an empty destination directory after the initial
existence check. The old `os.replace` silently replaced that directory on Linux.
The original backend failed all 14 new rejection assertions. These are adapter
fault-injection results, not evidence that native Gmsh itself corrupts files.

## Implementation

- Copy node IDs and coordinates into bounded arrays, sort by ID, validate shape,
  finiteness and uniqueness, and compare with absolute tolerance 1e-12 mm and
  relative tolerance 1e-13 for ASCII floating-point round trips.
- Hash dimension, entity, element type, element IDs and ordered connectivity for
  exported 2-D/3-D elements. Preserve orientation and entity/group membership;
  ignore harmless enumeration order. 0-D/1-D elements are intentionally outside
  this contract because the adapter exports physical groups only in 2-D/3-D.
- Compare physical-group dimensions, tags, names and member entities, not just
  labels. This preserves the current grouping; it does not make the generic
  `boundary` group an exterior-boundary or solver-role annotation.
- Use native no-replace directory publication: Linux `renameat2` with
  `RENAME_NOREPLACE`, macOS `renameatx_np` with `RENAME_EXCL`, or Windows
  `os.rename`. Unsupported platforms/filesystems fail closed. Parent directories
  are trusted; atomic visibility is not power-loss durability or a sandbox.
- Preserve receipt v1 fields and add explicit verification/tolerance metadata.
- Extend the existing API double with coordinates/connectivity/membership and
  retarget its publication-failure injection. All original test names and test
  assertion ASTs are unchanged; no existing rejection assertion was removed.
- Add a read-only, exact-head workflow running the original native fixture plus
  existing and new contract tests. Existing workflows and dependency pins remain
  unchanged. The workflow is not claimed passing until it actually runs.

## Actual local execution

Environment: Linux x86-64, Python 3.13.5, pytest 9.0.2.

| Execution | Actual result |
| --- | --- |
| Original contract suite on exact original backend | 30 passed |
| New defect assertions on exact original backend | 14 failed as expected; 25 deselected |
| New integrity suite on repaired backend | 39 passed |
| Original contracts plus new suite on repaired backend | 69 passed; zero failures |
| Independent-process publication races | Five repetitions, exactly one winner each |
| Python compilation | Passed |

Each process-race test launches two independent spawned processes; the losing
writer retains its staging data and the winner's published payload is preserved.
Additional filesystem tests preserve existing empty/nonempty directories, files
and dangling symlinks and refuse unsafe fallback when the syscall is missing.

Full before/after raw logs and JUnit XML are retained in the accompanying session
source/evidence bundle. These local runs used an extracted module subset, not a
complete installed NeuroCAD checkout; the package-wide import and application
integration were not certified locally.

## Remaining release gates

Native Gmsh was unavailable locally and its installation failed because external
package/network access was unavailable. Real STEP-to-MSH meshing, the full
NeuroCAD suite, local Ruff and macOS/Windows syscall execution were NOT run.
The new workflow must establish native/full-package compatibility at its own
exact head; local engineering results are not remote CI success.

This change does not provide pre-generation native CPU/RAM/time containment,
filesystem/network isolation, exterior/interface boundary role inference,
solver convergence, physical safety, manufacturability or scientific validation.
Verification caps of 1,000,000 nodes and 3,000,000 exported elements are
post-generation Python-work bounds, not protection from native mesher allocation.
Keep this PR draft. Reconcile parent #69 with main separately before any merge.

## Reproduction in a complete checkout

```sh
python -m pip install -e '.[dev,mesh-gmsh]'
python -m pytest -q tests/test_gmsh_backend.py tests/test_gmsh_contract.py tests/test_gmsh_integrity.py
python -m ruff check core/gmsh_backend.py core/gmsh_integrity.py tests/test_gmsh_contract.py tests/test_gmsh_integrity.py
```

Linux native Gmsh additionally needs its runtime library dependency (`libglu1-mesa`
in the existing Ubuntu CI configuration).

## API and operating-system references

- Gmsh 4.15.2 manual: https://gmsh.info/doc/texinfo/
- Python rename semantics: https://docs.python.org/3/library/os.html#os.rename
- Linux renameat2: https://www.man7.org/linux/man-pages/man2/rename.2.html
- Apple constants and signatures: https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/stdio.h
