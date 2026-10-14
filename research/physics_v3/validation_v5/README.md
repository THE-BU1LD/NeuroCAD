# Corrected composite conformance successor

This is source-bound engineering regression. The original failed beam study, earlier passing conformance scopes, and later failed biaxial-shaft reference are preserved. The protocol and source inventory are in PROTOCOL.md and freeze.json.

- Source-only scalar: `python3 scripts/validate_physics_v3_v5.py --output /new/empty/output`
- Verifier checks: `python3 tests/test_v3_validation_v5_harness.py`
- Installed acceptance: use the isolated-wheel sequence in `.github/workflows/physics-v3-validation-v5.yml`; a fresh output directory is required.
- Composite references: `tests/test_composite_reference.py` and supplementary `tests/test_section_integral_reference.py` have separately retained source/contract identities.

Do not rewrite the freeze to accommodate different code. Use the exact source revision recorded in the receipt. No physical, external-reproduction or intended-user evidence is created by these commands.

The v5 wrapper reuses the immutable v4 execution engine while binding a new complete source manifest. Additional geometry/property tests retain their own prospective contracts.
