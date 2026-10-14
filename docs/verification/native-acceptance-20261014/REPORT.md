# Native CAD and mesh acceptance — 14 October 2026

The implementation candidate `bf4cdca1e36ca21858403f0ebb043e7abf469602` passed the
full product matrix, native interoperability and all three new platform jobs.
The preservation follow-up restores the frozen compiler paper byte-for-byte
and adds an automatic 40-file protected-evidence check to the acceptance runner.
Final checks for that follow-up and merge identity remain to be recorded.

- Native matrix: https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38573309209
- Full matrix: https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38573309121
- Interoperability: https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38573308981
- Pull request: https://github.com/THE-BU1LD/NeuroCAD/pull/110

Each of Linux x86-64, macOS ARM64 and Windows x86-64 passed 182 native/rejection
checks, five analytic exact-CAD goldens and six repeated tagged meshing runs.
The reference programs cover sketch/extrusion, four patterned holes, a revolved
bottle-like solid, edge fillets and an open enclosure with a chamfered cutout.
STEP re-import checks valid/manifold B-Rep, one body, extents and analytic volume.
Tagged beam, plate and enclosure meshes retain physical membership and pass an
independent tetrahedral-volume sum. Repeated runs match declared invariants
within each platform; cross-platform element counts differ and no byte identity
across platforms is claimed.

The 129 source/STEP/MSH/receipt files listed by the three manifests were locally
hash-verified and are retained under
`research/verification/native_acceptance_20261014/`. Each directory also retains
its original manifest. Tool versions: build123d 0.13.0, OCP distribution
8.0.1.1.0, Gmsh 4.15.2, Python 3.13.15 and NumPy 2.5.4.

Named planar-envelope roles are source-bound and count-checked. Stale source,
invalid or index-based selectors, missing/mismatched bindings and damaged
receipts fail closed. Build receipts now record OCP; revision evaluation rejects
missing or mismatched kernel identity. Windows canonical JSON now uses LF bytes,
fixing ten observed revision failures without weakening their assertions.

Failures retained: attempt 1 had unavailable Python setup artifacts on macOS/
Windows and an incorrect OCP metadata name in the runner. Attempt 2 passed Linux
and macOS but exposed the Windows newline bug (172 pass, 10 fail). The first two
full matrices were automatically cancelled after successor pushes; they are not
claimed as completed passes. Native outputs and run metadata remain retained.

The separate research provenance audit found timing fields in the original v1
'deterministic' artifact and one missing historical `logs/run.log`. New format v2
separates these timing fields; 1,211 present historical artifacts match hashes.
The original manifest and results are unchanged; no missing log is reconstructed.
See `docs/RESEARCH_PROVENANCE_AUDIT_20261014.md`.

Physical experiments, independent execution, intended-user studies, protected
benchmark authorship/authorization, external CAD assets/licenses and publication
decisions remain open. These authored software controls advance no scientific
checkpoint. The immutable public alpha v0.5.0a6 is unchanged.
