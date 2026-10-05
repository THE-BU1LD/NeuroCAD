# Physical World AI 2026 — Claim-to-Evidence Freeze

This file is the submission-specific claim ledger for GitHub issue #82.

| ID | Candidate claim | Current status | Minimum artifact needed before paper can state it as a result |
|---|---|---|---|
| PWAI-C1 | Visual plausibility, geometry validity, revision integrity, and meshability are distinct evaluation outcomes. | **Protocol claim; result pending** | At least one case with all applicable outcomes independently recorded. |
| PWAI-C2 | Immutable baseline + derived repair/revision artifacts make before/after evaluation traceable. | **Engineering mechanism supported; external case pending** | External case receipt with baseline hash plus distinct derived-artifact hash and transformation log. |
| PWAI-C3 | Frozen revision invariants can detect out-of-scope geometry drift independently of downstream meshing. | **Internal/fixture evidence exists; external fixture pending** | One frozen revision fixture with predeclared invariants and retained verdict artifacts. |
| PWAI-C4 | Passing geometry validation does not establish downstream meshability. | **Logical boundary; empirical case pending** | One retained case containing geometry-validation output and a separately executed mesh attempt. |
| PWAI-C5 | NeuroCAD's Gmsh evidence path detects the injected serialized-geometry corruption classes covered by the integrity suite. | **Supported for enumerated injected classes only** | Exact workflow/run IDs and final source commit referenced in manuscript. |

## Hard exclusions

Do not state any of the following as supported results:

- broad text-to-CAD superiority;
- general natural-language understanding;
- arbitrary CAD correctness;
- geometry validation implies meshability;
- meshability implies simulation correctness;
- manufacturability, physical fit, or safety;
- third-party endorsement from Coreform, C3D Labs, WayKen, Rimac, GrabCAD, or other public-case sources;
- population-level reliability estimates from the small external case set.

## Artifact rule

Every numerical or pass/fail statement in the manuscript must point to:
1. exact source identity;
2. exact repository commit;
3. exact command/config;
4. raw or machine-readable result artifact;
5. immutable artifact hash where practical.

If any of these are missing, downgrade the statement to a planned evaluation or limitation.
