# NeuroCAD cross-layer flaw checklist — 17 October 2026

Cross-layer source/evidence audit; not an exhaustive proof that all defects are known.

FIXED_LOCAL means targeted source checks only, until a separately linked exact-head hosted receipt exists. VERIFIED_BASELINE applies to the prior main commit only.

Each row distinguishes an observed defect, evidence gap, supported boundary or rejected suspicion. Earlier checklist states remain dated history; this register does not overwrite them.

## A01 — Boolean or malformed dimensions accepted or crash

**High · FIXED_LOCAL** · Earlier items: F25

Cause: Dimension paths admitted Python truthy/nonnumeric values inconsistently.

Repair / next action: Reject nonnumeric, nonfinite, negative and malformed extent vectors with structured errors.

Required evidence: New counterexamples plus native/installed regression.

Source: `core/requirement_verification.py`.

## A02 — Kernel truthiness is not a validity verdict

**High · FIXED_LOCAL** · Earlier items: F10, F25

Cause: bool("false") evaluates True.

Repair / next action: Require an actual boolean; False remains a failed measurement.

Required evidence: String/integer/None controls plus exact backend integration.

Source: `core/requirement_verification.py`.

## A03 — Integer dimensions round into false equality

**High · FIXED_LOCAL** · Earlier items: F25

Cause: float conversion loses an integer unit above representable precision.

Repair / next action: Reject lossy integer dimensions/tolerances and retain exactly representable controls.

Required evidence: Three retained failing cases and passing representable control.

Source: `core/requirement_verification.py`.

## A04 — Ambiguous evidence JSON can pass

**High · FIXED_LOCAL** · Earlier items: F32

Cause: Last duplicate key wins; nonfinite constants allowed by default decoder.

Repair / next action: Bounded strict decode; hash the same bytes that are parsed.

Required evidence: Duplicate, nonfinite, hash-mismatch and size counterexamples.

Source: `scripts/audit_v3_readiness.py`.

## A05 — Readiness pointers use Python index semantics

**Medium · FIXED_LOCAL** · Earlier items: F32

Cause: Negative, signed, padded indices and invalid escapes are accepted.

Repair / next action: Require canonical JSON Pointer array indices and escapes.

Required evidence: Malformed pointer rejection plus escaped-key control.

Source: `scripts/audit_v3_readiness.py`.

## A06 — Nested boolean evidence equals numeric evidence

**High · FIXED_LOCAL** · Earlier items: F32

Cause: Python container equality treats True as 1.

Repair / next action: Recursively compare types as well as values.

Required evidence: Nested list/object counterexamples.

Source: `scripts/audit_v3_readiness.py`.

## A07 — Malformed readiness containers crash or misidentify schema

**Medium · FIXED_LOCAL** · Earlier items: F01, F32

Cause: No entry schema validation; True and 1.0 equal integer version 1.

Repair / next action: Validate object/array/string containers and exact integer version; return FAIL.

Required evidence: Malformed API/CLI inputs and existing readiness cases.

Source: `scripts/audit_v3_readiness.py`.

## A08 — Invalid Feature IR allegedly reaches acceptance

**None · REJECTED_FINDING** · Earlier items: F25, F36

Cause: Initial test failed before verification while constructing the hash.

Repair / next action: No production change: serialization already validates; retain negative controls and failed audit attempt.

Required evidence: Four existing rejection controls; do not count as repaired bugs.

Source: `core/feature_ir.py`.

## A09 — Verification covers represented intent only

**High · OPEN_ENGINEERING** · Earlier items: F10, F11, F15

Cause: Source-span accounting cannot prove that extracted predicates match complete human intent.

Repair / next action: Keep interpretation review separate from checker satisfaction; adjudicate omission cases.

Required evidence: Independent clause labels and omitted/spurious-requirement interventions.

Source: `core/conversational_parser.py`.

## A10 — Language generalization unmeasured

**High · BLOCKED_EXTERNAL** · Earlier items: F05, F06, F07, F08, F09

Cause: 32 observed authored cases share two contexts.

Repair / next action: Preserve 20/20 valid and 12/12 rejection development results; acquire new families.

Required evidence: Independent authorship, family split, ambiguity/status rubric and protected results.

Source: `docs/verification/hosted-bore-20261016/REPORT.md`.

## A11 — Entity lineage beyond supported edits is incomplete

**High · OPEN_ENGINEERING** · Earlier items: F13

Cause: Topology changes can remove or ambiguously resolve named entities.

Repair / next action: Extend only a declared selector/cardinality envelope with adversarial native tests.

Required evidence: Deleted, split, merged and ambiguous face/edge reference cases.

Source: `core/exact_build123d.py`.

## A12 — Scalar preservation and correction have bounded coverage

**High · VERIFIED_BASELINE** · Earlier items: F06, F07, F12

Cause: Earlier parser limitations repaired on main but not universally solved.

Repair / next action: Retain scalar/history/negation tests; expand from observed user failures.

Required evidence: Base hosted language suite; independent new edit sequences still needed.

Source: `core/conversational_parser.py`.

## A13 — Aggregate properties do not establish local features

**High · OPEN_ENGINEERING** · Earlier items: F10, F24

Cause: Equal volume/extents can hide moved, filled or mis-sized features.

Repair / next action: Keep aggregate and final-bore claims separate; add independent local predicates by domain.

Required evidence: Final-solid counterexamples with equal aggregates and different geometry.

Source: `core/requirement_verification.py`.

## A14 — Final bore verification is limited to isolated Cartesian bores

**High · VERIFIED_BASELINE** · Earlier items: F10, F13, F25

Cause: Probe requires one manifold solid, bounded entry plane and sleeve/cap clearance.

Repair / next action: Retain the exact scope; do not label it arbitrary hole recognition.

Required evidence: Existing cross-platform native tests; new geometry requires a successor contract.

Source: `core/final_geometry.py`.

## A15 — Interacting features and arbitrary wall thickness unsupported

**High · OPEN_ENGINEERING** · Earlier items: F13, F24, F25

Cause: Current planar and isolated-bore contracts omit general cavities and intersections.

Repair / next action: Define supported interactions first; compare reimported solids against independently measured references.

Required evidence: Native intersection, narrow ligament, open cavity and tangency cases.

Source: `core/exact_build123d.py`.

## A16 — Evidence invalidation beyond existing contexts needs coverage

**High · OPEN_ENGINEERING** · Earlier items: F14, F24

Cause: New dependencies or caches could leave stale verdicts.

Repair / next action: Use full recomputation reference and explicit source/material/load/unit/checker identity.

Required evidence: Mutation matrix and incremental-versus-full equivalence; no cache speed claim.

Source: `core/physics_context.py`, `core/physics_v3_context.py`, `core/project.py`.

## A17 — Mesh topology is not exact geometric or physical proof

**High · SCOPE_LIMIT** · Earlier items: F23, F25

Cause: Welding and floating predicates operate on sampled triangles.

Repair / next action: Declare mesh scale/tolerance envelopes and cross-check supported predicates.

Required evidence: Independent mesh/solid references, degeneracy and convergence cases.

Source: `core/topology.py`, `core/mesh_geometry.py`.

## A18 — Optimization is local and finite precision

**High · SCOPE_LIMIT** · Earlier items: F25

Cause: Local solvers can depend on initialization/scaling.

Repair / next action: Document convergence/residual contracts; retain infeasibility versus failed-search distinction.

Required evidence: Independent numerical references, conditioning and multi-start diagnostics.

Source: `core/scientific_kernel.py`.

## A19 — Analytical physics omits general spatial fields

**High · SCOPE_LIMIT** · Earlier items: F23, F24

Cause: Closed-form/network assumptions exclude general contact, plasticity, fatigue and turbulence.

Repair / next action: Keep analytical screening explicit; add solver adapters only for an admitted need.

Required evidence: Solver verification, mesh convergence and physical validation for each new claim.

Source: `docs/PHYSICS.md`.

## A20 — Uncertainty calculations depend on supplied distributions

**High · SCOPE_LIMIT** · Earlier items: F23, F25

Cause: Assumed covariance and ideal inputs are not empirically calibrated reliability.

Repair / next action: Separate input uncertainty, numerical error and measurement uncertainty.

Required evidence: Independently calibrated inputs and held-out measured coverage.

Source: `core/physics_uncertainty.py`, `core/scientific_kernel.py`.

## A21 — General sketch, assembly and freeform CAD are absent

**High · OPEN_ENGINEERING** · Earlier items: F24, F36

Cause: Current Feature IR and backend contracts cover a finite subset.

Repair / next action: Treat as separately scoped product expansions, not prerequisites for bounded enclosure correctness.

Required evidence: Native constraint/assembly/reference suites before enabling each surface.

Source: `core/feature_ir.py`, `docs/C3D_REVISION_CLI.md`.

## A22 — Native external-app interoperability not demonstrated broadly

**High · BLOCKED_EXTERNAL** · Earlier items: F24, F28

Cause: Most integrations are file handoffs rather than application-native execution.

Repair / next action: Obtain exact tools/assets and retained import/edit/export outcomes.

Required evidence: Licensed CAD fixtures, confirmed invariants and independent application receipts.

Source: `core/integrations/`, `docs/verification/merged-bore-20261016/OWNER_ACTIONS.md`.

## A23 — Local app exists but browser tests are not user evidence

**Medium · VERIFIED_BASELINE** · Earlier items: F24, F30

Cause: Loopback workbench, daemon and project revisions cover engineering behavior.

Repair / next action: Retain tested local behavior and explicit schematic-versus-verified preview distinction.

Required evidence: Base browser/CLI receipts plus intended-user task outcomes.

Source: `core/demo_server.py`, `core/daemon.py`, `core/workbench.py`.

## A24 — Internet-hosted multiuser app is outside current deployment contract

**High · SCOPE_LIMIT** · Earlier items: F24

Cause: Demo has no complete authentication/tenant isolation/storage service.

Repair / next action: Keep loopback default; design and threat-model a separate hosted product if needed.

Required evidence: Authentication, authorization, isolation, rate-limit and deployment tests.

Source: `core/demo_server.py`, `README.md`.

## A25 — Performance advantage unmeasured

**Medium · OPEN_ENGINEERING** · Earlier items: F26

Cause: No complete representative latency/memory/cost profile.

Repair / next action: Profile actual workflows before optimizing or training.

Required evidence: Pinned workloads, full failed-attempt cost, cancellation and concurrency measurements.

Source: `docs/NEUROCAD_RECOVERY_CHECKLIST_20261015.md`.

## A26 — Local native/full/release execution inadmissible

**Critical · BLOCKED_RESOURCE** · Earlier items: F27

Cause: 217.8 and 274.5 MiB available; pageouts rise; minimum is 512 MiB.

Repair / next action: Use authorized hosted checks or recheck stable local admission.

Required evidence: Exact candidate native/full/type/package receipts; no old-SHA substitution.

Source: `audit/comprehensive_20261017/CONTRACT.json`.

## A27 — Published alpha predates verified main and this candidate

**High · OPEN_ENGINEERING** · Earlier items: F34

Cause: Installer still selects immutable v0.5.0a6.

Repair / next action: Publish a separately versioned prerelease only after exact-source checks.

Required evidence: New version/tag, wheel/sdist provenance and credential-free install acceptance.

Source: `pyproject.toml`, `RELEASE_STATUS.md`.

## A28 — Status routing mixes old checkout, main and release

**High · OPEN_ENGINEERING** · Earlier items: F01, F34

Cause: Historical headers retain superseded source identities.

Repair / next action: Append a current routing record and preserve every dated predecessor.

Required evidence: Before/after state hashes and explicit base/candidate/release links.

Source: `CURRENT_STATUS.md`, `RESEARCH_STATE.json`.

## A29 — Distinct contribution is not established

**Critical · RESEARCH_BLOCKED** · Earlier items: F03, F33

Cause: CIT-CAD, CADTests, ReliCAD and CADEngBench overlap broad promises.

Repair / next action: Keep Checkpoint 1 blocked until a materially distinct falsifiable question is defended.

Required evidence: Exact prior-art comparison and independent domain review.

Source: `research/successors/recovery_research_v2_20261015/REVIEW.md`.

## A30 — Independent task and scoring authority absent

**Critical · BLOCKED_EXTERNAL** · Earlier items: F08, F09, F15, F28

Cause: Project-authored labels are not independent ground truth.

Repair / next action: Recruit separate task authors/adjudicators with provenance and disagreement records.

Required evidence: Unseen revision families, approved oracle and rights.

Source: `research/physics_v3/external_validation_v1/PROTOCOL.md`.

## A31 — Matched strong comparisons not executed

**Critical · RESEARCH_BLOCKED** · Earlier items: F04, F16, F22

Cause: Task support, information and budgets must be comparable.

Repair / next action: Freeze compatible adapters, equal budgets and classical/simple controls first.

Required evidence: Pinned baseline implementation, support coverage and complete outcomes.

Source: `research/successors/recovery_research_v2_20261015/FORMAL_CONTRACT.md`.

## A32 — Fixed-bank and interactive claims can be conflated

**Critical · RESEARCH_BLOCKED** · Earlier items: F16, F18

Cause: Repair and clarification change candidates, information and costs.

Repair / next action: Use separate estimands; keep fixed-bank mechanism controls distinct.

Required evidence: Prospective matched-bank study and separately budgeted end-to-end protocol.

Source: `research/successors/recovery_research_v2_20261015/FORMAL_CONTRACT.md`.

## A33 — Reject-all policies can look safe

**High · RESEARCH_BLOCKED** · Earlier items: F17

Cause: False acceptance alone omits useful completion.

Repair / next action: Report correct-and-accepted, unsafe acceptance, coverage and clarification cost together.

Required evidence: Predeclared practical benefit and risk criteria; undefined conditional risk at zero acceptance.

Source: `research/successors/recovery_research_v2_20261015/FORMAL_CONTRACT.md`.

## A34 — Statistical precision, clustering and multiplicity unresolved

**Critical · RESEARCH_BLOCKED** · Earlier items: F19, F20, F21

Cause: Dependent paraphrases and many endpoints inflate apparent evidence.

Repair / next action: Choose family-level split/analysis, primary contrast and precision target before protection.

Required evidence: Power/precision rationale, paired cluster uncertainty and multiplicity policy.

Source: `research/successors/revision_research_v1/CHECKLIST.md`.

## A35 — Failure accounting needs immutable complete denominators

**High · VERIFIED_BASELINE** · Earlier items: F16, F24, F32

Cause: Earlier adapter and persistence paths could drop scheduled tasks.

Repair / next action: Retain merged manifest-first ledger and fault-injection controls.

Required evidence: Base regression receipts; new research requires separate ledger freeze.

Source: `core/language_comparison.py`, `research/vericodegen/`.

## A36 — Physical fit and model accuracy unmeasured

**High · BLOCKED_EXTERNAL** · Earlier items: F23

Cause: No calibrated fabricated-part/apparatus dataset supplied.

Repair / next action: Choose scope/operator, freeze predictions/tolerances, measure every declared trial.

Required evidence: Raw measurements, calibration, repeats, uncertainty and discrepancy review.

Source: `research/physics_v3/external_validation_v1/PROTOCOL.md`.

## A37 — Independent reproduction absent

**High · BLOCKED_EXTERNAL** · Earlier items: F29

Cause: Implementer CI cannot be its own independent executor.

Repair / next action: Give pinned package and derivations to an external executor.

Required evidence: Independent commands, environment, logs, all failures and discrepancy report.

Source: `research/physics_v3/external_validation_v1/PROTOCOL.md`.

## A38 — Usability and accessibility not measured

**High · BLOCKED_EXTERNAL** · Earlier items: F30

Cause: No eligible user sessions or target-device observations supplied.

Repair / next action: Execute existing formative protocol with consent and fixed assistance rule.

Required evidence: At least five eligible users under existing protocol; task time/errors/outputs/withdrawals.

Source: `research/physics_v3/external_validation_v1/PROTOCOL.md`.

## A39 — Industrial/customer usefulness unproven

**High · BLOCKED_EXTERNAL** · Earlier items: F30

Cause: No independent team acceptance records supplied.

Repair / next action: Obtain consented real tasks, critiques and repeated pilot workflows.

Required evidence: External engineering-team and organization pilot records.

Source: `docs/verification/merged-bore-20261016/OWNER_ACTIONS.md`.

## A40 — Four historical original logs remain missing

**High · BLOCKED_EXTERNAL** · Earlier items: F31

Cause: Archive provenance incomplete for four old runs.

Repair / next action: Recover authentic bytes from original custodians or retain limitation.

Required evidence: Original expected SHA-256 matches; never synthesize replacement logs.

Source: `docs/verification/merged-bore-20261016/missing-log-recovery.json`.

## A41 — PhD/publication quality cannot be inferred from tests

**Critical · RESEARCH_BLOCKED** · Earlier items: F33

Cause: No successor scientific run or independently defended contribution.

Repair / next action: Keep successor NOT_EVALUATED and predecessor terminal MIXED.

Required evidence: Claim-to-raw-evidence chain, independent review and justified terminal answer.

Source: `research/successors/recovery_research_v2_20261015/CLOSURE.json`.

## A42 — Repeated iteration until success rewrites scientific meaning

**High · POLICY_RETAINED** · Earlier items: F02, F35, F36

Cause: Unbounded perfection has no stopping rule.

Repair / next action: Bound engineering work; retain old results and separately version new scientific claims.

Required evidence: Preservation inventory, attempts and explicit remaining gates.

Source: `audit/comprehensive_20261017/CONTRACT.json`.

## A43 — Missing local readiness receipt

**High · RECOVERED_LOCAL** · Earlier items F01, F31, F32.

The original checkout lacked `docs/verification/readiness-20261014/implementation-v2.json`. Recovered bytes from verified main match the hash already present in its checklist. This is authentic recovery, not a recreated result. The first audit failure remains retained. The four original run logs remain missing. See `receipt-recovery.json`.

## A44 — Broken historical Python source

**Low · HISTORICAL_RETAINED** · F35, F36.

`legacy/python/cad_master_kernel_legacy_broken.py` fails syntax at its empty class body (lines 4286–4287). The whole-repository inventory retains the failure. `MANIFEST.in` prunes `legacy`; this is not a newly introduced maintained-product defect. Its bytes remain unchanged.
