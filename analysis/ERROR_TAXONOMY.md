# Error taxonomy and observed frequencies

Run `NC-RUN-2026-09-03-FULL` predeclared eight invalid-input categories. All 30 cases in every category were rejected (240/240); none silently compiled.

| Category | Definition | Cases | Rejected | Escaped |
|---|---|---:|---:|---:|
| Syntax error | malformed JSON/token structure | 30 | 30 | 0 |
| Type error | wrong schema value type | 30 | 30 | 0 |
| Invalid reference | root/child/constraint target does not resolve | 30 | 30 | 0 |
| Constraint inconsistency | declared dimension differs from referenced parameter | 30 | 30 | 0 |
| Non-finite number | NaN or infinity in structured input | 30 | 30 | 0 |
| Duplicate ID | two nodes share an identifier | 30 | 30 | 0 |
| Cycle | recursive composition dependency | 30 | 30 | 0 |
| Semantic input error | incomplete dimensioned-language request | 30 | 30 | 0 |

Additional requested categories have the following evidence status:

- **kernel failure:** 0/240 in the complete controlled compiler benchmark; not estimated for the entire IR space;
- **non-volume, non-manifold, empty, disconnected, inconsistent-winding, or dimension-mismatched geometry:** 0/240; `verify_stl` rejects each condition;
- **semantic or parameter mismatch:** 0/240 for NeuroCAD, 96/240 retrieval, 130/240 raw-number, 240/240 fixed-box;
- **incorrect measured STL topology:** 0/240 for the declared checks; exact BREP topology was not measured;
- **self-intersection:** not independently measured by the STL verifier and therefore unknown.

The raw records, including error messages and all baseline failures, remain in the run directory.
