# Native CAD and mesh acceptance — 14 October 2026

## Final implementation and merge

PR110 merged as `0bef391d210b8df1c871f5f250cf011012728e64`. Its Git tree
`0a3b767105c6374bf39c07d8813ec42562bc6ef6` exactly equals final tested candidate
`518208bb3f709d4686d663309dd19b7f8f39a5c2`. The [post-merge full CI confirmation](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38577282155)
passed all ten jobs on that exact main commit. All final-candidate checks also passed:

- [Full product matrix](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38576123086):
  ten jobs passed, including 1,714 maintained tests (10 skipped, 53 subtests),
  1,695 source-distribution tests (10 skipped, 33 subtests), fresh installations,
  all three browsers, all three portable OS jobs, exact CAD and security checks.
- [Native acceptance](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38576123082):
  each platform passed 182 native/rejection tests, five analytic solid cases and
  six mesh runs. All 40 historical protected hashes passed before and after.
- [CAD/mesh interoperability](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38576123091): passed.

The final 129 manifest-listed native artifacts, three manifests and three test
XML files are retained under `research/verification/native_acceptance_final_20261014/`.
Every listed file was hash-verified after download; `final-artifact-audit.json`
binds the manifests, platform test counts and exact candidate. Earlier candidate
3 artifacts below remain unchanged. See the [current checklist](../../WORK_REGISTER_20261014.md).

Main now requires thirteen strict status checks (the prior ten plus the three
native platforms), a PR and resolved conversations; administrator enforcement,
force-push/deletion prohibitions and prior review settings remain unchanged.
This does not claim an independent human review. Issues #64/#65 are closed.
Eleven external/provenance-dependent issues remain open. Concurrent PR111 is
separate readiness work pinned to earlier source; it is not included in this
merge or this source-specific completion claim.

New artifact-audit and timing regression checks passed 15 focused cases locally.
The reusable auditor found matching present artifacts in all four retained
compiler runs, but each original `logs/run.log` is absent. Full archive integrity
is therefore FAIL; timing format v2 fixes future deterministic extraction while
all earlier result bytes remain intact. Details and raw reports are linked in
[the provenance audit](../../RESEARCH_PROVENANCE_AUDIT_20261014.md).

Attempt 4 additionally failed on Windows when checkout converted protected
files to CRLF. Attempt 5 preserves Git bytes before checkout and passes the
unchanged guard. Development used all five allowed workflow attempts, including
the two cancelled full CI runs. The separately declared final integration phase
allows exactly one non-adaptive main CI confirmation: six full-CI runs across
the two phases, with no retroactive change to the five-attempt contract.

No physical experiment, independent executor or intended-user observation was
created. The local native resource gate remained closed; hosted runners supplied
the native evidence. No scientific checkpoint or new public release is claimed.
Published immutable v0.5.0a6 remains at its original source identity.

## Earlier candidate receipt (retained history)

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
