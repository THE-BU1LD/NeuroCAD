# Scalar intent maintenance specification

This implements existing-product requirements, not a new research contribution. The research successor remains Checkpoint 1 blocked.

1. Normalize a clause with existing bounded typo/politeness rules while retaining original source spans.
2. Recognize complete scalar preservation clauses and map them to existing field constraints. `floor` means floor thickness; `lid` alone is ambiguous and is not inferred.
3. `only` before a supported scalar operation preserves every other stored specification field. For a lid property, protect all other lid properties individually. Never interpret `only` as removable filler. Conflicting subsequent changes prevent publication.
4. A complete `not QUANTITY UNIT SCALAR` clause records an excluded stored value and requires an immediately adjacent replacement for that same scalar. Only that explicit source-local target can resolve `it` or `them`; no conversation history is read. Missing/mismatched replacement refuses the whole transaction.
5. Convert both values through the existing bounded Decimal quantity path. Reject the excluded stored value, including unit-equivalent values and later self-corrections back to it.
6. Retain quantity metadata (target, absolute value, relative flag and directional verb). A bare self-correction inherits the prior directional intent and is checked against the immutable baseline. A full explicit replacement clause can specify a new verb.
7. Existing absolute canonical edit validation, source coverage, preserve checks, candidate review and stale-context hash checks remain in force. The persisted proposal schema remains v1; local interpreter metadata advances to v3.

No learned parameters, training loss or scientific dataset change is introduced. Time is bounded by the existing 8192-character input and 32-entry proposal collections. New matchers are precompiled; no latency claim is promised. ONLY protection generation is linear in specification field count and deduplicates fields already protected by earlier ONLY clauses.

Acceptance: authored positive cases must match the complete intended spec; adversarial missing units, negative scope, contradictions, mismatched references, forbidden-value restoration and opposite-direction correction must publish no candidate. All inherited parser/directional/evaluator regressions must pass in the explicit allowlist. One replay of the unchanged observed diagnostic may measure regression repair; no tuning after that replay.
