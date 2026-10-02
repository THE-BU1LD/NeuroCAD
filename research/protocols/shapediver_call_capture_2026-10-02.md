# ShapeDiver call capture — 2026-10-02

> **Status update — 2026-10-02:** the scheduled discussion was **not completed** because the external participant was not present. A reschedule/update request was sent. No ShapeDiver technical feedback has been received or inferred from the missed call, no invariants below are frozen, and no benchmark fixture may be executed from this template until an actual discussion or another independently sourced public protocol supplies the missing technical inputs.

**Use immediately after the call. Do not fill from memory later if exact wording is uncertain.**

## Call metadata

- Date/time:
- Participant: Mathieu Huard, ShapeDiver
- NeuroCAD participant: Ryan Gomez
- Public/non-confidential discussion only: yes / no
- Recording used: no unless explicitly agreed
- Follow-up invited: yes / no

## Recommended test case

- Public model/configurator/reference:
- Geometry family:
- Parameter to change:
- Allowed range:
- Baseline value:
- Candidate changed value(s):

## Frozen invariants

Record only invariants Mathieu actually recommends or clearly agrees are reasonable.

1.
2.
3.
4.
5.

For each invariant, specify whether it should be checked as:
- stored parameter value;
- resulting geometry;
- topology/relation;
- downstream behavior;
- other.

## Explicit failure conditions

1.
2.
3.

## Parameter-range logic

- How should allowed ranges be chosen?
- Are ranges hard constraints, soft design guidance, or context-dependent?
- What happens when a parameter edit remains numerically in range but creates invalid geometry?

## Geometry-versus-parameter checks

- Is checking named parameters alone sufficient?
- Which resulting-geometry checks matter?
- Which silent failures are common in real configurator workflows?

## Public implementation/reference material

- Link/reference 1:
- Link/reference 2:
- Link/reference 3:

## Claim boundary

What ShapeDiver/Mathieu did **not** validate:

- NeuroCAD correctness:
- NeuroCAD–ShapeDiver integration:
- manufacturability:
- general engineering suitability:
- endorsement:
- other:

## Proposed frozen evaluation statement

Fill only after the call:

> Starting from [public baseline], change [parameter] from [baseline] to [candidate / range]. The revision passes only if [invariants] remain satisfied and [failure conditions] do not occur. Evaluation checks [parameter values / resulting geometry / topology / downstream behavior]. This protocol is informed by public technical feedback and does not imply ShapeDiver validation or endorsement.

## Follow-up email summary

Before sending, reduce this to 4–6 lines and ask Mathieu only to correct technical misunderstandings. Do not ask for endorsement.

## Repository actions after capture

- [ ] Create/freeze benchmark fixture.
- [ ] Hash source identity.
- [ ] Freeze invariants before execution.
- [ ] Add receipt schema instance.
- [ ] Execute positive case(s).
- [ ] Execute at least one adversarial/silent-failure case.
- [ ] Preserve all failures.
- [ ] Update issue #82 claim ledger.
- [ ] Add result only if artifact-backed.
