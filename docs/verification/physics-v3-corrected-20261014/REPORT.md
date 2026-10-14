# Corrected Physics v3 conformance

The source correction at `5676436719415302ce94076c4d49c37e302308f7` passed
[hosted verification](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38557278466).
37/37 scalar cases and 52/52 installed cases/workflow checks passed. Four
complex-shape meshes compiled; regression passed 1,236 tests with 9 skips and
43 passing subtests. The external evidence auditor passed 11 integrity tests
in a separate hosted job. Raw job metadata/log and SUMMARY.json are retained.
Generated bundles, complete installed receipts and meshes remain in the hosted
artifact; they were not independently reproduced or physically measured.

The correction includes the interior moment extremum for signed opposing beam
loads. The known counterexample now reports 2.1 MPa maximum stress rather than
zero; the added yield case reports 1.05 utilization and fails its constraint.
Root reactions, slope and deflection are unchanged. Existing v1 protocol,
references, freeze and failed outcome are retained. Replay v1 at its recorded
commit; its freeze correctly refuses the corrected production source.

This is project-authored regression/conformance with known predecessor outcomes.
It does not establish every inherited formula or composite structural output,
independent derivation/reproduction, physical accuracy, user benefit, safety,
manufacturing readiness or a new published release. The old release remains
unchanged. Physical measurements, an independent executor and intended users
have not been supplied. Their prospective procedures and evidence auditor are
in research/physics_v3/external_validation_v1.

PR #106 is stacked on the preserved validation PR #105. Receipt-only commits
after the verified source do not change frozen production/runner identities.
