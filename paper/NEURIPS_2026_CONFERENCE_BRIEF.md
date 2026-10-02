# NeuroCAD: Separating Geometry Validity, Revision Integrity, and Meshability in Physical-World AI

**NeurIPS 2026 conference technical brief**  
**Ryan Gomez — NeuroCAD / The Bu1LD**

## One-line idea

For AI-assisted CAD, “the model produced something that looks right” is not a sufficient success criterion. NeuroCAD treats geometry validity, preservation of intended invariants, and downstream meshability as separate, independently evidenced stages.

## Why this matters

Physical-world AI systems increasingly generate, revise, or reason over geometry. In engineering workflows, a visually plausible artifact can still fail in several distinct ways:

- the resulting geometry is invalid;
- a requested edit silently changes unrelated geometry;
- a file is valid but cannot be meshed under the declared downstream policy;
- a mesh exists but fails a user-selected quality criterion;
- an output is reproducible only in prose, not from retained artifacts.

NeuroCAD is being developed as a constrained, fail-closed CAD-generation and revision system with explicit evidence receipts. The current research direction is therefore less about claiming broad text-to-CAD intelligence and more about making engineering claims auditable.

## Evaluation decomposition

We separate four outcomes:

| Stage | Question | What counts as evidence? |
|---|---|---|
| Visual plausibility | Does the artifact look superficially reasonable? | Human/visual review only |
| Geometry validity | Is the resulting solid valid under declared geometric checks? | Reopened geometry/kernel checks |
| Revision integrity | Did the requested edit preserve geometry and requirements declared invariant? | Frozen invariants + before/after receipts |
| Meshability | Does the artifact pass a separately declared meshing workflow/policy? | Mesher execution + provenance + output receipt |

The key rule is that success at one stage does not imply success at the next.

## Current verified engineering evidence

### 1. Frozen revision-integrity evaluation

A constructed 17-case C3D-style evaluation is now merged and source-bound.

The suite contains:
- five feasible wall-thickness revisions;
- twelve expected rejections covering geometry drift, impossible cavity geometry, altered frozen requirements, and stale bindings.

For every accepted revision, the generated STEP artifact is independently reopened and checked again. For every expected rejection, the evaluator requires:
- the declared error class;
- no candidate publication;
- an unchanged accepted baseline.

The retained run reported **17/17 expected outcomes**, and the separate native Gmsh meshing stage also passed for the declared positive case. The same PR reported a broad local suite of **1,087 passing tests** with two known Unix-socket tests intentionally deselected, plus green lint, type checking, security checks, platform CI, browser acceptance, exact-CAD tests, source-distribution tests, and the standalone CAD-to-mesh evaluation at the final verified revision.

**Boundary:** this is a constructed verifier-regression suite within one frozen component family. It is not held-out design-family evaluation and not evidence of learned-model generalization.

### 2. Separate mesh-quality publication policy

NeuroCAD's supervised STEP-to-Gmsh pipeline now accepts an optional minimum SICN element-quality floor.

If a caller supplies a floor:
- the floor must be finite and in `(0, 1]`;
- below-floor or unavailable quality fails explicitly;
- the STEP input is preserved;
- no mesh bundle is published;
- successful executions record the requested floor and observed score in the evidence receipt.

The merged implementation was validated with **157 focused supervisor/CLI/integrity tests** and **5 real build123d-to-Gmsh integration tests**. A separate pilot STEP passed at a floor of **0.001** and was rejected at **0.1** without publication.

**Boundary:** this is an element-quality acceptance rule. It does not establish solver convergence, physical correctness, manufacturability, or safety.

## Evidence architecture

```text
request / source geometry
        |
        v
immutable input identity
(hash, units, versions, settings)
        |
        v
generation or revision
        |
        v
geometry artifact
        |
        +--------------------+
        |                    |
        v                    v
geometry checks       revision-invariant checks
        |                    |
        +---------+----------+
                  |
                  v
         downstream meshing
                  |
                  v
         optional quality policy
                  |
                  v
         evidence receipt bundle
```

Each stage records commands, versions, configuration, artifact identity, and failure state. Derived repair or revision artifacts are kept separate from the baseline.

## What is not claimed

NeuroCAD does not currently claim:

- general natural-language-to-CAD intelligence;
- state-of-the-art text-to-CAD performance;
- arbitrary CAD correctness;
- that geometry validity implies meshability;
- that meshability implies simulation correctness;
- manufacturability, fit, load capacity, or safety;
- that current internal regression suites establish external validity.

The historical claim that a typed parser caused improved learned-model behavior remains explicitly falsified and is excluded from this research direction.

## External-validation work now underway

The next step is to move from internal constructed evidence toward externally grounded engineering cases.

### Dirty-CAD geometry-to-meshing case

A public dirty-CAD benchmark has been frozen around a real assembly example recommended through Coreform correspondence. The protocol preserves the untouched as-imported model, records exact import metadata, runs explicit geometry checks, stores repairs only as derived artifacts, and performs tet meshing as a separate outcome.

No result is reported until those external execution artifacts exist.

### Parametric edit-reliability case

A separate external-feedback track with ShapeDiver focuses on a simple question: after changing one allowed parameter in a parametric model, what invariants should remain fixed, and what constitutes a silent failure even if the model still renders?

The intended output is one public, reproducible edit task with:
- one changed parameter;
- an allowed range;
- 3–5 invariants;
- explicit failure conditions;
- checks on resulting geometry, not only stored parameter values.

## Research question for discussion

The current research question is:

> How should physical-world AI systems evaluate generated or revised engineering geometry without collapsing visual plausibility, geometric validity, revision integrity, and downstream meshability into a single success label?

The broader hypothesis is that stronger engineering evaluation comes from treating these as independent, provenance-bound checks rather than one aggregate notion of “valid output.”

## What I want feedback on at NeurIPS

1. Is the four-stage decomposition scientifically useful, or is an important engineering stage missing?
2. Which public CAD benchmark families would best test external validity without introducing proprietary data?
3. What is the right abstraction for invariants in learned or agentic geometry systems: named parameters, geometric relations, topology, or all three?
4. How should a benchmark distinguish “failure to satisfy the requested edit” from “valid edit that is poor for downstream simulation”?
5. Which parts of this protocol generalize beyond CAD to other physical-world AI outputs such as meshes, scenes, robot plans, or simulation assets?

## Current artifact trail

- merged C3D constructed evaluation: PR #80;
- merged mesh-quality policy: PR #81;
- dirty-CAD benchmark: issue #78;
- conference-brief / 2027 evidence lane: issue #82 and draft PR #83;
- source-bound controlled compiler evidence: `NC-REPRO-508EC40`;
- repository evidence and claim ledgers: `EVIDENCE_LEDGER.md`, `FINAL_RESEARCH_AUDIT.md`, and `audits/CLAIM_LEDGER.md`.

## Bottom line

The project is deliberately moving away from “does AI generate something that looks like CAD?” toward a stricter question:

**Can every engineering claim about an AI-produced artifact be traced to a specific invariant, check, command, and retained artifact — while preserving failures rather than repairing them away?**
