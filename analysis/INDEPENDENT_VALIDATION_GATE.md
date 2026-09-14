# NeuroCAD independent validation gate

**Status:** PRE-OUTCOME PROTOCOL ONLY — EXECUTION NOT AUTHORIZED  
**Frozen source anchor:** `main@a910f949694787da012fe10818cf5367b51ac0f4`  
**Scope:** deterministic NeuroCAD compiler only. This protocol does not revive the falsified typed-parser mechanism claim and does not authorize VeriCodeGen Stage 2/3 work.

## Purpose

The current controlled evidence verifies a narrow compiler on its declared grammar, but generated in-grammar tasks and post-implementation adversarial cases are not an independent blind challenge. The next scientifically useful step is therefore not another feature sweep. It is one source-bound, independently authored challenge under a prospectively frozen comparator, verifier, failure rule, and outcome-access contract.

No confirmatory outcome may be opened, generated, summarized, or used for retuning until every blocking item below has a retained receipt.

## 1. Freeze the treatment surface

Before challenge labels or outcomes are accessible, retain:

- exact Git commit and a clean-tree receipt;
- hashes of the supported compiler source surface (`core/` plus maintained CLI/evaluation modules);
- the accepted prompt/IR contract and supported grammar version;
- Python version and locked dependency identities;
- OpenSCAD executable identity/version where STL compilation is part of the endpoint;
- all runtime flags, timeout/retry rules, output-retention rules, and deterministic seeds, if any;
- an empty, newly created output directory receipt proving no resumed samples are present.

Any treatment-changing source edit after this freeze invalidates the confirmatory run and requires a new protocol version before outcome access.

## 2. Independent challenge contract

The confirmatory challenge must be authored outside the implementation path by a person or group that did not inspect case-level system outcomes while authoring it. Before execution, retain:

- immutable case IDs and dataset/archive SHA-256;
- provenance, license/use permission, and author identity/role;
- task-family counts and an outcome-blind coverage summary;
- frozen expected semantic properties or adjudication targets;
- a separate adjudication key/receipt that is inaccessible to the implementation operator until the treatment and comparator are frozen;
- a written rule for ambiguous, invalid, or out-of-scope cases;
- a statement that cases will not be edited, removed, or rescued after observing system-specific failures.

Challenge construction must not reuse generated examples produced by NeuroCAD's parser/compiler code as confirmatory evidence.

## 3. Comparator fairness gate

The current deterministic development baselines in `BASELINES.md` remain useful controls, but a confirmatory comparative claim requires one prospectively frozen grammar-independent comparator or an explicitly narrower non-comparative claim.

If a comparator is used, freeze before outcomes:

- exact implementation/model/version and source identity;
- the same task information available to both systems;
- the same retry count, timeout, resource envelope, and failure accounting;
- the same semantic verifier and retained-output rules wherever technically possible;
- no hand repair, hidden hints, or system-specific rescue path;
- a documented mapping for outputs that cannot be represented in the canonical verifier.

If those conditions cannot be made fair, the confirmatory claim is restricted to NeuroCAD's exact-source-bound compiler behavior and must not claim superiority.

## 4. Primary endpoint and failure accounting

The confirmatory endpoint must be specified in a versioned manifest before execution. It must distinguish at minimum:

1. accepted/rejected input according to the frozen scope contract;
2. canonical IR/schema validity;
3. semantic/constraint validity;
4. deterministic OpenSCAD generation where applicable;
5. STL compilation/topology verification where the task requires a mesh;
6. exact failure category for every unsuccessful case.

The manifest must name one primary endpoint and its aggregation rule before outcome access. Secondary metrics are descriptive and may not replace an unfavorable primary endpoint after results are observed. Timeouts, exceptions, invalid outputs, verifier failures, and missing outputs count according to the frozen failure rule; they may not be silently dropped.

## 5. Component interventions

Mechanism-oriented follow-up is separate from the confirmatory comparison. If component evidence is reported, freeze isolated interventions for:

- unit normalization;
- named versus positional dimension handling;
- feature parsing;
- fail-closed semantic validation;
- constraint checking.

Each intervention changes one declared component while preserving the rest of the pipeline. These analyses may localize behavior but **cannot** revive the already-falsified historical claim that introducing a typed parser itself caused improved model behavior.

## 6. Leakage and independence review

Before execution, an outcome-blind reviewer must sign off that:

- challenge cases were not used to implement or tune the treatment;
- adjudication targets are not present in prompts, filenames, metadata, logs, or fixtures available to the treatment;
- comparator and NeuroCAD receive matched information;
- no case-level outcome has been inspected during final treatment selection;
- all exclusions are predeclared and mechanically checkable;
- any development-only cases are clearly separated from confirmatory cases.

A failed leakage review blocks execution; it is not a documentation warning.

## 7. Outcome-access state machine

The run remains locked until the following state transitions are evidenced:

`DRAFT_PROTOCOL -> SOURCE_FROZEN -> CHALLENGE_FROZEN -> COMPARATOR_FROZEN_OR_CLAIM_NARROWED -> LEAKAGE_REVIEW_PASS -> EXECUTION_AUTHORIZED -> RUN_COMPLETE -> ADJUDICATION_UNLOCKED -> REPORT_LOCKED`

Rules:

- `EXECUTION_AUTHORIZED` requires retained receipts for every previous state.
- Challenge/adjudication outcomes remain inaccessible before `RUN_COMPLETE`.
- No treatment/comparator changes are allowed between `EXECUTION_AUTHORIZED` and `REPORT_LOCKED`.
- An implementation/runtime defect discovered after authorization is recorded as a failed attempt. Any rerun requires an explicit incident note stating whether the protocol remains valid; treatment-changing fixes require a new protocol version.
- Negative or null results are retained and reported under the same rule as positive results.

## 8. Required retained evidence package

The final independent-validation package must contain:

- protocol version and exact source SHA;
- source/environment/OpenSCAD receipts;
- challenge manifest, archive hash, license/provenance, and authoring-independence statement;
- comparator manifest or claim-narrowing declaration;
- leakage-review receipt;
- execution-authorization receipt;
- raw per-case outputs for both systems, where applicable;
- raw verifier/adjudication records and failure taxonomy;
- deterministic aggregation script and its source hash;
- primary/secondary metrics with all exclusions and failures visible;
- a machine-readable run manifest linking every reported number to source, challenge, and output artifacts.

## 9. Stop conditions

Do **not** run the confirmatory challenge if any of these remain unresolved:

- exact accepted source surface is not frozen;
- challenge provenance/license/hash is missing;
- adjudication is not independent or outcome-blind;
- comparator fairness is unresolved while a comparative claim is planned;
- leakage review is incomplete;
- failure/exclusion rules are not frozen;
- outputs can be resumed or overwritten without an immutable attempt record;
- execution authorization or held-out outcome access is ambiguous.

## Claim boundary after completion

Even a successful independent challenge would support only the frozen compiler/task contract. It would not establish general natural-language-to-CAD intelligence, BREP/STEP reconstruction, engineering safety, manufacturability, or learned geometric reasoning. Human usability remains governed separately by `analysis/HUMAN_EVALUATION_PROTOCOL.md`.
