# Reviewer attack and repairs

## “There is no scientific novelty.”

Valid. The framing was repaired from a general machine-intelligence system to a controlled compiler engineering case study. `NOVELTY_AUDIT.md` explicitly disclaims algorithmic novelty.

## “The dataset is generated from the grammar, so 100% is circular.”

Valid threat. The paper calls this contract coverage, not natural-language generalization. Split labels introduce unit/lexical shifts but do not create a natural distribution. External CAD datasets were audited and not force-converted into an incompatible task.

## “Baselines are weak.”

Valid for an ML paper. Retrieval was added as a train-fitted baseline. Published models are documented but not compared because their inputs, representations, data, and compute differ. No state-of-the-art claim remains.

## “Syntax is being called geometry.”

Repaired. Static syntax/type/reference/constraint results are separate from NC-EXP-006 kernel execution and `trimesh` topology/dimension verification. The expanded run executed all 240 benchmark programs; its uncertainty and CSG/STL boundary remain visible.

## “Examples were cherry-picked.”

Repaired. Qualitative task IDs use the first eight IDs before outcome inspection; all 240 kernel tasks follow the predeclared deterministic round-robin order. All failures remain in per-system records.

## “The ablation is trivial.”

It is intentionally narrow: removing constraints should remove drift detection. The claim is limited to declared parameter-drift detection, not learned mechanism attribution.

## “Editability is not usability.”

Agreed. The manuscript reports automated modification success only, and the unexecuted human protocol is clearly marked.

## “One seed is inadequate.”

No training randomness exists. The seed defines deterministic synthetic data; repeating the same run checks reproducibility, not statistical variation. A learned successor would require multi-seed training.

## “OpenSCAD is not a commercial BREP kernel.”

Agreed. Results establish executable CSG-to-STL behavior only. STEP/BREP identity, exact topology, precision-sensitive booleans, and manufacturing validity remain unsupported.

## “The old failures disappeared behind a new implementation.”

Repaired by `HISTORICAL_TRUTH.md`, separate `NC-EXP-*` IDs, retained VeriCodeGen artifacts, and explicit manuscript language that new engineering results do not rehabilitate the falsified historical parser claim.

## “Reproduction provenance is incomplete.”

Still a limitation: the audit initialized a local `.git`, but it does not recover
the absent historical ancestry and has no merge base with the canonical remote.
Hashes cover data/config artifacts; public commit/tag provenance remains pending.
