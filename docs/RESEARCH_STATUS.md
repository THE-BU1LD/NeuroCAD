# NeuroCAD Research Status

This reviewer-facing status separates scientific evidence from software/release evidence. Passing CI, compiling CAD, or succeeding on scripted smoke fixtures is not by itself support for a research hypothesis.

| Maintained claim / question | Current verdict | What is established | Next decisive gate |
| --- | --- | --- | --- |
| The historical typed-parser mechanism itself caused the reported NeuroCAD advantage | **FALSIFIED / validation-dominant** | Later matched-validation evidence removes the causal interpretation; release work does not revive it. | No rescue test. Preserve the falsifier and evaluate VeriCodeGen as a separate successor mechanism. |
| The maintained code can execute the supported Stage-2 evaluation path fail-closed | **SUPPORTED as engineering evidence only** | Evaluation plumbing exists and rejects invalid evidence paths. | Keep it fixed while outcome-bearing Stage-2 remains unauthorized until issues #21/#22 close. |
| Scripted Stage-1 fixtures demonstrate real model/CAD performance | **CONTRADICTED as a scientific interpretation** | They demonstrate plumbing and verification behavior only. | Run only the frozen held-out external pilot after authorization. |
| A structured VeriCodeGen arm outperforms a direct arm under treatment-matched validation | **UNTESTED** | No admissible Stage-2 comparison outcome exists yet. | Freeze the 120-task benchmark, prompts, baselines, provider/model identities and budgets, then authorize the bounded pilot. |
| Current verifier acceptance is sufficient for semantic CAD correctness | **WEAK / UNPROVEN** | Compilation and hard constraints catch some invalid outputs but may permit semantically wrong geometry. | Incorporate externally identified verifier gaps before outcome access. |
| NeuroCAD/VeriCodeGen outputs are manufacturing/fabrication valid | **UNTESTED** | Parsing/compilation is not evidence of manufacturability. | Separately preregister a fabrication-aware benchmark with process/material/load assumptions and physical checks. |
| The successor study can be independently reproduced by an outside engineer/team | **UNTESTED** | Internal provenance infrastructure exists; independent reproduction has not occurred. | Freeze a complete reproduction package and have an external engineer rerun without author intervention. |
| COPES feedback/meeting constitutes scientific validation | **NOT A VALID SCIENTIFIC CLAIM** | External criticism can improve protocol quality but does not establish a positive result, adoption, or independent reproduction. | Preserve concrete criticisms and convert blocking/major findings into pre-outcome protocol changes or tracked issues. |

## Current scientific boundary

Scientifically established: the historical typed-parser causal story remains rejected; current Stage-2 infrastructure has engineering evidence and fail-closed controls.

Not scientifically established: successor superiority, broad semantic correctness, manufacturability, external adoption/validation, or independent reproduction.

The decisive gate is to complete [issue #21](https://github.com/THE-BU1LD/NeuroCAD/issues/21) and [issue #22](https://github.com/THE-BU1LD/NeuroCAD/issues/22) without outcome access, incorporate any blocking external criticism, and then execute only the bounded preregistered pilot. Positive, mixed, negative, or inconclusive outcomes must be preserved unchanged.

## Related evidence surfaces

- Software/release evidence: [`PUBLIC_ALPHA_EVIDENCE_LEDGER.md`](PUBLIC_ALPHA_EVIDENCE_LEDGER.md)
- External pressure-test capture: [issue #27](https://github.com/THE-BU1LD/NeuroCAD/issues/27)
- Held-out benchmark freeze: [issue #21](https://github.com/THE-BU1LD/NeuroCAD/issues/21)
- Stage-2 authorization/execution: [issue #22](https://github.com/THE-BU1LD/NeuroCAD/issues/22)

## Integrity rules

- Do not upgrade a scientific claim because CI is green, a demo works, or an external meeting occurs.
- Do not relabel reused historical diagnostics as new held-out/OOD evidence.
- Do not change benchmark selection, prompts, baselines, provider/model identity, seeds, budgets, thresholds, or analysis after outcome access to rescue a result.
- Negative, mixed, inconclusive, contradicted, and falsified outcomes remain first-class results.
