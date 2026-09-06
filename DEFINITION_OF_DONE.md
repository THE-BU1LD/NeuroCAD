# NeuroCAD definition of done

This definition closes the maintained NeuroCAD compiler and its controlled research package. It does not redefine unsupported general CAD, BREP, simulation, or learned-model systems as hidden requirements.

| Gate | Objective acceptance criterion | Evidence command or artifact | State |
| --- | --- | --- | --- |
| Truth recovery | Supported, legacy, refuted, and blocked surfaces are separately named; negative results remain visible. | `PROJECT_TRUTH.md`, `NEUROCAD_TRUTH.md`, `audits/HISTORICAL_TRUTH.md` | Met |
| Input contract | Supported prompt families and the structured-input size/version limits are documented and fail closed. | README, parser/CLI rejection tests | Met |
| Canonical representation | Schema plus semantic validation cover primitives, transforms, hierarchy, references, constraints, cycles, finite values, and deterministic round trips. | `pytest tests/test_ir.py` | Met |
| Real end-to-end path | At least one non-hard-coded input reaches real OpenSCAD, produces STL, and passes topology and dimensional checks. | kernel integration tests and `NC-EXP-006` | Met |
| Geometry robustness | Every selected full benchmark sample passes finite-vertex, positive-volume, watertight, winding, single-body, and expected-extents checks. | `NC-RUN-2026-09-03-FULL`: 240/240 | Met |
| Evaluation | Results include per-task records, baselines, exact paired tests, failures, hashes, and conservative claim boundaries. | `NC-RUN-2026-09-03-FULL` manifest and metrics | Met |
| Demo | Demo uses production parser/IR/validator/exporter and has request limits and browser security headers. | `pytest tests/test_benchmark_demo.py` | Met |
| Integrity | Fake STEP, unimplemented markers, legacy broken kernels, stale release claims, and copied test/hash evidence cannot enter the supported distribution story; version metadata agrees. | `pytest tests/test_integrity.py tests/test_research_provenance.py` | Met locally; external exact-revision rerun blocked by missing Git metadata |
| Portability | Python 3.10–3.12 CI runs the full suite on Linux, macOS, and Windows; Linux also runs OpenSCAD integration. | `.github/workflows/ci.yml` | Implemented; external CI receipt blocked |
| Security | Static analysis and dependency audit pass against the release environment. | Generated Bandit and `pip-audit` CI results for the exact revision | Configured; integrated verification pending |
| Distribution | Wheel and sdist build from an exact clean revision; a clean environment installs the exact outputs and generated provenance binds their checksums to the revision. | release workflow `RELEASE_PROVENANCE.json` | Local candidate build/install met; clean Git and generated release provenance pending |
| S3 scientific boundary | No learned outcomes are accessed or claimed before real candidate-pool freeze, pilot selection, authorization, model/provider pinning, and budget approval. | `research/s3/PRE_OUTCOME_STATUS.json` | Correctly blocked |
| External release | Exact Git SHA, CI URLs, anonymous installer result, tag, artifact checksums, and public release URL are recorded. | public alpha evidence ledger | Blocked outside this checkout |

The maintained release is done only when every applicable gate passes on one
exact source revision. External-release and S3 gates must remain explicitly
blocked rather than filled with invented values.
