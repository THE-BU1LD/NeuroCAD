# Public-main engineering handoff — 2026-09-09

The owner requested committing and pushing the upgrades, managing all open PRs,
and testing end to end. Maintained product, tests, packaging, workflow and
documentation changes were pushed. Frozen evidence, generated outputs, local
environments and credentials were not churned or uploaded merely to modify every
file. A bounded alpha is not a claim of arbitrary CAD or scientific completeness.

## Merged implementation and verification

- PR [#47](https://github.com/THE-BU1LD/NeuroCAD/pull/47) merged as documentation
  only. Its manuscript remains explicitly pre-outcome and non-authorizing.
- PR [#49](https://github.com/THE-BU1LD/NeuroCAD/pull/49) merged at
  `cc8c534412701439da0d346b5445b37dc8f74122`, preserving both Git histories.
- Implementation head `8fed84a362d673cd302e97fa2c711115c54066d4` passed all twelve
  exact-head checks. [CI run 34358865144](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/34358865144)
  records **511 tests passed** on each Linux Python 3.10/3.11/3.12 lane and
  **509 tests passed** from the actual source distribution. Two archive-only
  checks are deliberately not shipped. Portable Ubuntu/macOS passed 484 tests
  with 27 intentional kernel skips; Windows passed 479 with 32 kernel/POSIX skips.
- Chromium, Firefox and WebKit passed real project/edit/download/kernel acceptance.
  Three additional research workflows passed development/methodology/ledger checks,
  not held-out scientific evaluation.
- Wheel/sdist installations, repeated byte-identical builds, complete script
  lint/type/security gates, and the staged installer passed in CI.

The preceding Windows failure was genuine: implicit platform decoding corrupted
UTF-8 text in the Node harness. Explicit UTF-8 reads/subprocess decoding fixed it;
a maintained-source encoding guard now prevents recurrence. It was not skipped.
The restored canonical S3 CSV and the pre-outcome manuscript `.tex` are now shipped
because their source-distribution consumers require them.

## Credential-free public end-to-end acceptance

The exact merged implementation was fetched from GitHub codeload without an
Authorization header or GitHub credentials, then installed from source into a
brand-new Python 3.12.14 virtual environment outside the checkout. The installed
`core` import resolved to that environment's `site-packages`, not the development tree.

- Public source archive SHA-256:
  `5183c09e5d6e7e42d6ccbb8f7b35fd6f7e9841e306c60d1ea8aca65c66fb516a`.
  This identifies the downloaded codeload snapshot, not a signed release asset.
- `neurocad doctor` passed with independently resolved runtime dependencies.
- An 80 × 60 × 30 mm rounded enclosure, 2 mm walls, 6 mm corner radius and M3
  screw lid was interpreted, compiled with OpenSCAD 2021.01 at `$fn=48`, and
  independently verified.
- Verification returned `valid: true`, both body/lid parts and nine artifacts.
  All seven source/schema/hash/IR/SCAD/preflight/mesh checks passed.

Repeat in new output paths after installing that snapshot:

```bash
neurocad doctor
neurocad enclosure interpret "80 x 60 x 30 mm electronics enclosure; walls 2 mm; corner radius 6 mm; profile fdm standard; screw lid 2.5 mm thick clearance 0.3 mm M3 fasteners at corners inset 8 mm" --project-id public-main-acceptance --project-output public-project.json
neurocad enclosure build public-project.json --output-dir public-built --stl --fn 48
neurocad enclosure verify public-built
```

Logs, the downloaded archive, isolated install and verified bundle are retained
locally in `.provenance/github-handoff-20260909/` as applicable. Large generated
evidence is intentionally not a source-distribution payload.

## Every pre-existing PR has an explicit disposition

| PR | Disposition | Boundary |
| --- | --- | --- |
| #49 | Merged after all checks passed | Public software source; no release tag or scientific authorization |
| #47 | Merged as pre-outcome documentation | No provider calls, submission or invented results |
| #46 | Updated and pushed at `c6b54fc`; all twelve fresh checks passed; remains draft | Three obsolete links resolved through a separate owner map; all seven historical JSON files unchanged; outside-subtree completeness review remains open |
| #45 | Reviewed and left draft with a concrete blocker comment | Independent 591-row taxonomy/dedup review, selection and final-environment bindings, then separate authorization review are still required |

Leaving the latter reviews open is deliberate. CI, an AI-generated review, or
an administrative merge cannot manufacture independent human/scientific evidence.
The seven frozen provenance JSON files and S3 pre-outcome state were not rewritten.

## What is not yet complete

There is no `v0.5.0a6` release tag or published release-provenance receipt. The
default immutable-tag bootstrap remains pending even though public source install
works. Follow [RELEASE_STATUS.md](../RELEASE_STATUS.md) for the tag/artifact gates.
Independent usability, screen-reader/native-mobile review and physical-fit trials
remain separate. No safety, manufacturing or learned-model certification is claimed.
