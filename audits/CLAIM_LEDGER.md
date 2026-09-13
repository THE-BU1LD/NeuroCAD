# Claim ledger

| Claim ID | Allowed manuscript claim | Evidence | Status/boundary |
|---|---|---|---|
| C-01 | NeuroCAD is a deterministic compiler for a bounded dimensioned-English CAD subset. | code, schema, tests | Supported; not general NLU |
| C-02 | It achieved 240/240 semantic-exact controlled compilations. | NC-EXP-001; `NC-REPRO-508EC40` | Source-bound support on synthetic frozen set only |
| C-03 | It exceeded retrieval (144/240), raw-number (110/240), and fixed-box (0/240) baselines. | NC-EXP-001; exact McNemar p-values | Supported; baselines are not contemporary trained CAD systems |
| C-04 | 1,000/1,000 generated typed programs passed validity, constraints, exact round trip, and deterministic export. | NC-EXP-002; `NC-REPRO-508EC40` | Source-bound support for generated distribution |
| C-05 | The retained run rejected all 240 unique generated malformed fixtures. | NC-EXP-003; `NC-REPRO-508EC40` | Eight designed categories; regression evidence only, with no population interval. |
| C-06 | Declared constraints detected 200/200 injected parameter drifts versus 0/200 without constraints. | NC-EXP-004 | Supported; not intent inference or solving |
| C-07 | 200/200 automated named-parameter edits survived the full static pipeline. | NC-EXP-005 | Supported; not human usability |
| C-08 | 240/240 benchmark programs compiled freshly to STL passing topology, connectivity, finite-value, volume, and expected-extents checks. | NC-EXP-006; `NC-REPRO-508EC40` | Source-bound support for the controlled benchmark; zero reuse; Wilson 95% interval 98.42–100% |
| C-09 | Depth 128 exports; depth 129 is explicitly rejected. | NC-EXP-007 | Supported for constructed stress programs |
| C-10 | Historical typed-parser causality was falsified and remains falsified. | HT-01; historical protocol/receipt | Supported negative evidence |
| C-11 | NeuroCAD improves learned model reasoning. | none | Prohibited/unsupported |
| C-12 | NeuroCAD matches or exceeds published text-to-CAD systems. | none | Prohibited; task/representation mismatch |
| C-13 | NeuroCAD guarantees manufacturability or safety. | none | Prohibited |
| C-14 | NeuroCAD is algorithmically novel. | novelty audit | Prohibited; engineering case study only |

Every quantitative claim in the paper cites an `NC-EXP-*` identifier. Anything outside this ledger must be treated as background, implementation description, or limitation rather than a result.
