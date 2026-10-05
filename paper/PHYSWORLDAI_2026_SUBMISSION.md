# NeuroCAD for Physical-World AI: Evidence-Preserving Geometry Validation Across Revision and Meshing Workflows

**Reference workshop:** NeurIPS 2026 Workshop on Physical World AI: Geometry, Characteristics, and Multimodal Sensing  
**2026 CFP status:** Closed; official contribution deadline was August 29, 2026  
**Current output:** 4-page conference technical brief + evidence-complete 2027/preprint manuscript pipeline  
**Status:** Claims frozen conservatively pending execution of the external geometry cases  
**Primary repository issue:** #82

## Abstract

Physical-world AI systems that generate or revise engineering geometry are often evaluated at the level of visual plausibility or task completion, even though downstream engineering workflows impose stricter requirements. A model can produce geometry that looks plausible while violating a revision invariant, containing invalid topology, or failing downstream meshing. We present an evidence-preserving evaluation workflow built around NeuroCAD that separates four questions that are frequently conflated: whether a design appears plausible, whether its geometry passes explicit validity checks, whether an intended revision preserves frozen invariants, and whether the resulting geometry is accepted by a downstream meshing workflow. The system records source identity, tool versions, commands, thresholds, hashes, intermediate artifacts, and failure states, and retains untouched baselines before any repair or defeaturing. Existing repository evidence includes a fail-closed controlled CAD compiler, source-bound reproducibility runs, revision-integrity fixtures, and Gmsh serialization/integrity checks. We extend this evidence model to external dirty-CAD and revision workflows without treating geometry validation as proof of meshability or engineering suitability. The resulting protocol is intended as a practical evaluation pattern for physical-world AI systems whose outputs must survive deterministic engineering checks rather than only perceptual review.

## 1. Research question

How can a physical-world AI or CAD-generation system evaluate engineering geometry without collapsing visual plausibility, geometric validity, revision integrity, and downstream meshability into a single success label?

This paper evaluates a provenance-preserving workflow rather than claiming a new CAD-generation algorithm.

## 2. Frozen claims

The submission is limited to the following claims unless stronger evidence is added before submission.

### Claim 1 — Evidence separation
A single engineering artifact can receive different outcomes under visual plausibility, geometry validity, revision-integrity, and meshability checks; therefore these outcomes should be recorded separately.

**Required evidence:** at least one benchmark case for which the four columns are populated from retained artifacts.

### Claim 2 — Baseline preservation
Keeping the as-imported or pre-revision artifact immutable, while storing repairs/revisions as derived artifacts, makes before/after evaluation auditable and prevents repaired geometry from silently replacing the baseline.

**Required evidence:** provenance receipts containing immutable baseline identity and separately hashed derived outputs.

### Claim 3 — Revision integrity can be tested independently of global validity
For a bounded revision task with frozen invariants, NeuroCAD can verify whether named geometry that should remain unchanged actually remains unchanged, independently of whether the final artifact later passes meshing or engineering review.

**Required evidence:** C3D-style revision-integrity fixture(s) with predeclared invariants and retained pass/fail receipts.

### Claim 4 — Geometry validity does not imply meshability
Passing a geometry-validation stage is not sufficient evidence that a downstream tet-meshing workflow succeeds.

**Required evidence:** dirty-CAD benchmark records containing both validation output and a separately recorded mesh attempt. A failed mesh is a valid result.

## 3. Explicit non-claims

This submission does **not** claim:

- general natural-language-to-CAD intelligence;
- state-of-the-art text-to-CAD performance;
- that geometry validation proves meshability;
- that successful meshing proves simulation correctness;
- manufacturability, physical fit, structural safety, regulatory compliance, or production readiness;
- exact BREP reconstruction from arbitrary inputs;
- that public engineering case studies constitute third-party endorsement;
- that internal synthetic compiler benchmarks establish external CAD validity.

## 4. System and evidence architecture

The evaluation flow is:

```text
source / prompt / revision request
        |
        v
immutable input identity
(hash, source, units, tool versions)
        |
        +----------------------+
        |                      |
        v                      v
generation / revision      as-imported external CAD
        |                      |
        v                      v
canonical artifact         baseline validation
        |                      |
        +----------+-----------+
                   |
                   v
          explicit check families
     ┌─────────────┼──────────────┬──────────────┐
     v             v              v              v
visual         geometry       revision       downstream
plausibility   validity       integrity      meshability
     |             |              |              |
     └─────────────┴──────────────┴──────────────┘
                   |
                   v
             evidence receipt
      (commands, versions, thresholds,
       hashes, outputs, failures)
```

Every repair/healing/defeaturing operation produces a derived artifact. The original baseline is retained.

## 5. Existing evidence foundation

### 5.1 Controlled compiler evidence

The source-bound run `NC-REPRO-508EC40` records a clean source identity and a fully regenerated internal controlled suite. It includes deterministic semantic checks, malformed-input rejection, revision/constraint checks, and kernel execution artifacts.

This evidence supports the implementation and provenance machinery only. It is synthetic, project-authored evidence and is not used as external validity.

### 5.2 Revision-integrity evidence

The revision-integrity lane treats a CAD edit as a transformation with explicit invariants. The key evaluation question is not merely whether an output file exists, but whether geometry that was declared immutable remains unchanged while the requested feature changes.

For this workshop paper, the revision-integrity component should be represented with the strongest frozen external or quasi-external fixture available at submission time.

### 5.3 Gmsh serialization and integrity evidence

The Gmsh integrity work verifies serialized node identities/coordinates, ordered 2-D/3-D topology, element/entity membership, physical-group membership, and safe artifact publication behavior under injected corruption classes.

These tests establish integrity properties of the adapter and evidence path. They do not claim that native Gmsh itself generates the injected corruptions.

### 5.4 Dirty-CAD benchmark

Issue #78 freezes a dirty-CAD workflow around the public Rimac GBX 700 case suggested through Coreform correspondence. The benchmark requires preservation of the as-imported geometry, exact import metadata, raw `validate volume all verbose` output, Geometry Power Tools thresholds relative to target mesh size, explicit classification of gaps/overlaps/misalignments/clearances, separate healing copies, and a separately recorded tet-mesh attempt.

The benchmark is not complete until the retained external execution artifacts exist.

## 6. Evaluation protocol

For each case, record the following before inspecting the final result.

### 6.1 Identity

- source/retrieval identity;
- SHA-256 or equivalent immutable content identity;
- source file format;
- units;
- import settings;
- exact software versions;
- exact repository commit for NeuroCAD-side tooling.

### 6.2 Baseline

- preserve the untouched imported/generated artifact;
- run the declared baseline checks;
- retain raw stdout/stderr and machine-readable outputs;
- hash the artifacts.

### 6.3 Repair or revision

If a repair or revision is attempted:

- create a new derived artifact;
- record the exact command or edit request;
- retain the transformation log;
- evaluate the same checks again;
- never overwrite the baseline.

### 6.4 Geometry validation

Record the exact geometry checks and thresholds. Thresholds that depend on intended mesh size must be stated relative to that target rather than reported as unexplained constants.

### 6.5 Revision integrity

For revision tasks, freeze 3–5 invariants before outcome-producing execution. Examples include:

- external envelope;
- selected hole positions;
- named datum geometry;
- a cutout/opening;
- a critical assembly reference.

A revision is not considered integrity-preserving merely because the file remains loadable.

### 6.6 Downstream meshability

Run meshing as a separate stage. Store:

- mesher/version;
- mesh-size/configuration parameters;
- exact command;
- exit status;
- diagnostics;
- output artifact identity;
- success/failure.

A failed mesh remains a reportable and useful outcome.

## 7. Primary results table

The final technical brief and full manuscript should contain a compact table of this form:

| Case | Visual plausibility | Geometry validity | Revision invariants | Meshability | Notes |
|---|---|---|---|---|---|
| Controlled generated fixture | TBD | artifact-backed | artifact-backed | artifact-backed | Internal engineering evidence only |
| C3D revision fixture | TBD | TBD | artifact-backed | N/A or TBD | Frozen revision invariants |
| Rimac dirty-CAD baseline | TBD | TBD | N/A | TBD | Untouched imported baseline |
| Rimac repaired derivative | TBD | TBD | N/A | TBD | Must remain a derived copy |
| Additional external fixture | TBD | TBD | TBD | TBD | Include only if provenance is complete |

Do not replace `TBD` with inferred values. Populate only from retained execution artifacts.

## 8. Failure analysis

The paper should foreground, not hide, the following failure classes:

1. visually plausible but geometrically invalid;
2. geometrically valid but not meshable;
3. requested revision succeeds while an invariant silently drifts;
4. repair improves one validation stage while changing geometry outside the requested scope;
5. adapter/export corruption caught by serialization-integrity checks;
6. unsupported or ambiguous generation requests that fail closed.

## 9. Reproducibility requirements

The final artifact package must include:

- exact Git commit;
- environment/tool versions;
- benchmark source identities;
- commands/configurations;
- raw validation logs;
- per-case receipts;
- hashes for baseline and derived artifacts;
- results table generated from those receipts;
- figure source;
- manuscript source and exact submitted PDF.

No quantitative statement should survive into the camera-ready manuscript unless it can be traced to a retained artifact.

## 10. Limitations

The workflow does not establish full engineering correctness. Geometry validity, invariant preservation, and meshing are only separate necessary checks for particular downstream workflows. They do not certify physical behavior, materials, tolerances, assembly fit, safety, or manufacturability. The external benchmark set is also intentionally small and case-based; this paper therefore presents an evaluation protocol and systems case study rather than a population-level estimate of CAD reliability.

The controlled language/compiler experiments remain useful implementation evidence but are not evidence of broad natural-language generalization. The historical claim that a typed parser caused learned-model improvement remains falsified and is outside this submission.

## 11. Completion gates

- [ ] Execute and retain the dirty-CAD baseline.
- [ ] Execute and retain at least one derived repair path.
- [ ] Record the separate tet-mesh outcome.
- [ ] Freeze and execute at least one revision-integrity external fixture.
- [ ] Populate the four-way results table from artifacts only.
- [ ] Generate the evidence-flow figure.
- [ ] Run a claim-to-artifact audit.
- [ ] Write related work using verified primary sources.
- [ ] Produce a concise 4-page NeurIPS-conversation brief in NeurIPS style.
- [ ] Produce and visually inspect the conference-brief PDF.
- [ ] Produce a full preprint/2027-submission manuscript after evidence gates pass.
- [ ] Record the exact public/preprint or future submitted revision when applicable.

## References to repository evidence

- `EVIDENCE_LEDGER.md`
- `FINAL_RESEARCH_AUDIT.md`
- `audits/CLAIM_LEDGER.md`
- `research/runs/NC-REPRO-508EC40/`
- GitHub issue #78 — dirty-CAD benchmark
- GitHub issue #82 — NeurIPS 2026 Physical World AI submission tracker
- Gmsh integrity PR/workflow evidence in the repository
