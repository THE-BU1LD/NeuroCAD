# External evidence collection and audit

Prepared for the six-gate NeuroCAD validation request. This is a separate
successor package; v2 and the concurrently authored `../validation_v1` suite
are not edited. Physical, independent and intended-user outcomes are absent.

1. Read [PROTOCOL.md](PROTOCOL.md) and [CAPABILITIES.json](CAPABILITIES.json).
2. Copy a plan from `templates/` into an external collection directory.
3. Fill all nulls from real apparatus, release identity and executor details.
   Enumerate every condition/trial/task as a distinct case. Add protocol,
   procedure and reference files to `frozen_artifacts`, with relative paths and
   SHA-256 hashes. Keep paths inside that collection directory.
4. Freeze **before** collecting outcomes:

   ```sh
   python3 evidence.py freeze /path/to/collection/plan.json /path/to/collection/freeze.json
   ```

5. The actual external operator collects evidence using the frozen procedure.
   Copy `templates/evidence.json`, fill the freeze hash and include exactly all
   planned cases. Every artifact role contains `{"path": "...", "sha256": "..."}`.
   Physical PASS rows add predicted/measured values, units, expanded_uncertainty
   and coverage_factor. Reproduction PASS rows add the four explicit attestations
   listed in `evidence.py`. Usability PASS rows contain per-participant rubric
   booleans. Failed or blocked attempts still require retained evidence.
6. Audit into a new output file:

   ```sh
   python3 evidence.py audit /path/to/collection/freeze.json /path/to/collection/evidence.json /path/to/collection/audit.json
   ```

7. Obtain the named external review described in PROTOCOL.md. No automatic
   status is scientific certification. `all_case_criteria_pass=false` must
   remain visible even when a complete negative study passes structural audit.

Both commands refuse to overwrite output. The frozen auditor must be used for
replay. A hash-bound declaration cannot prove authenticity or independence.

Run the lightweight integrity regressions (synthetic test data only):

```sh
python3 -m unittest discover -s research/physics_v3/external_validation_v1 -p 'test_*.py' -v
```

Immediate external inputs still required: an identified experimenter and actual
apparatus/calibrations; a distinct reproduction executor; intended users and
consent. No messages have been sent and no evidence has been invented.
