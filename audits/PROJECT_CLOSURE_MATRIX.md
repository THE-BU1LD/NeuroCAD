# NeuroCAD closure matrix

**Updated:** 2026-09-03

| Priority | Work item | Acceptance evidence | Status |
| ---: | --- | --- | --- |
| 1 | Strengthen compiled-geometry verification | Topology, connectivity, volume, finite vertices, and expected extents covered by tests | Implemented |
| 2 | Run all 240 compiler tasks through OpenSCAD | 240/240 retained STL/PNG/validation records and final hashed manifest | Complete |
| 3 | Replace the non-test `tests/test_integrity.py` script | Real packaging, version, claim-boundary, and forbidden-marker assertions | Implemented |
| 4 | Make offline methodology tools fail closed without Git | No traceback; clear immutable-revision gate plus regression tests | Implemented |
| 5 | Preserve and classify legacy failures | Historical truth ledger plus package exclusion assertions | Implemented |
| 6 | Expand cross-platform CI | Full tests on Linux/macOS/Windows and real Linux OpenSCAD smoke | Implemented; external run pending |
| 7 | Run full maintained tests and lint | Exact-revision CI test and pinned-Ruff gates | Integrated rerun pending |
| 8 | Run security and dependency gates | Bandit clean; no known audited dependency vulnerabilities | Complete |
| 9 | Build and clean-install distributions | Generated wheel/sdist checksums and provenance plus isolated smoke | Pending for a6 |
| 10 | Reconcile reports with final evidence | Truth, evaluation, completion, reproducibility, and release ledgers contain no copied candidate claims | Implemented; release receipt pending |
