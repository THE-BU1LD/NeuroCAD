# NeuroCAD human-AI process measurement rubric

Status: **secondary/process measurement amendment; not the frozen primary endpoint**.

This file operationalizes the bounded human-AI measurement requested after Professor Jessie Chin's 2026-09-10 recommendation. It is intentionally narrow. Objective task performance remains primary unless the canonical study protocol is formally amended before the relevant freeze.

## HAS-derived required-human-involvement item

Administer only after AI-assisted blocks:

> For the task you just completed with this AI assistant, how much human involvement was required to complete the task effectively?

- **H1** — The AI could handle the task entirely without my involvement.
- **H2** — The AI needed my input at a few key points to achieve better task performance.
- **H3** — The AI and I needed to work together as approximately equal partners.
- **H4** — The AI needed my input to successfully complete the task.
- **H5** — Successful task completion fully relied on my involvement.

Do **not** administer this item in an unaided-control block. Call it the **HAS-derived required-human-involvement rating** unless the exact administration is independently validated as the original instrument in this context.

### Frozen analysis boundary

H1-H5 is ordinal. For the pilot, report:
1. H1-H5 counts/distribution per assisted condition.
2. Median and ordinal IQR per condition.
3. Participant-level category transitions between useful-advice and plausible-wrong-advice blocks where paired observations exist.
4. Objective task performance separately.
5. Behavioral reliance separately.

Do not compute or headline a 1-5 mean just for convenience. Do not average HAS with accuracy, response time, advice uptake, or any other measure into an invented composite.

## Behavioral triangulation coding

This coding is **not HAS**. It exists to compare self-reported required human involvement with observable reliance behavior.

Code the participant's handling of a discrete AI recommendation as exactly one of:

- `accepted`: final action/answer adopts the recommendation materially unchanged.
- `modified`: recommendation is used but materially edited, qualified, or combined with independent work.
- `rejected`: participant explicitly or behaviorally overrides/declines the recommendation.
- `not_observable`: the retained log does not support a defensible classification.

Two coders should independently code the same initial subset before the behavioral variable is used in analysis. `core.human_agency.pair_behavior_codes` and `agreement_report` produce exact agreement, Cohen's kappa, and a confusion matrix. Never resolve disagreements by looking at the study outcome first.

## Integrity gates

Before collecting or analyzing new participant outcomes:

- archive the canonical human-study protocol/preregistration and its timestamp/version;
- record whether enrollment, treatment exposure, or outcome inspection has started;
- record this addition as a dated amendment with the correct preregistration status;
- freeze the exact item wording and administration schedule;
- preserve the useful-vs-plausible-wrong advice definitions independently of HAS outcomes;
- retain matched tasks, counterbalancing, blinded scoring, and the frozen primary endpoint;
- preserve null, mixed, contradictory, and negative findings.

The implementation rejects unaided HAS rows, duplicate participant/block/task rows, invalid H labels, and unexpected record fields to make accidental protocol drift visible instead of silently absorbing it.
