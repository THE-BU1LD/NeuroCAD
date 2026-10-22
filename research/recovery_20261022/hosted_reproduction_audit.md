# Hosted Physics v2 reproduction audit

**Disposition: PASS — internal cross-environment reproduction of the known
216-case software contract.** This audit validates retained evidence; it
does not execute a study case. The original study, its ledger and its
terminal disposition remain unchanged.

## Run and identity

GitHub Actions run [39726824693](https://github.com/THE-BU1LD/NeuroCAD/actions/runs/39726824693)
produced artifact `12402399676`. The coordinating session retrieved the
archive and its GitHub digest. The audit independently recomputed archive
SHA-256
`4c8c9e7af18fcaed4a88d3ecd0bfa00d9b5161ae898ee20c7840d17e2220d217`
and verified that all ten extracted files equal their ZIP entries byte for
byte, without missing or additional extracted files.

The evaluated source is commit
`786ba9ba5c2249a710529c3b07bf82d4e29c7f36`; the initiating workflow is
`95aa315e87e0546191bbcdbce60f9c083b43b4b6`. All eight frozen source files,
read directly from the evaluated Git commit, match the freeze, the original
manifest, the hosted declaration and the hosted manifest. The freeze and
case file also equal that commit's blobs. The retained post-run Git status
contains only the newly created execution ledger.

The two case hashes describe different serialized representations:

| Representation | SHA-256 |
| --- | --- |
| Frozen JSONL file bytes | `9caa80fb7e5257f514143ec0b297711464767c5a68ffa49988070a2f97c94c49` |
| Canonical JSON serialization of the parsed case list | `2e6bb79b5a649b191fb7b9a0635b9e0ae4053aae8d23b72af104fc5937ac0696` |

Both digests were recomputed successfully. The declaration uses the first;
the runner manifest uses the second. There is no case-identity mismatch.
The freeze digest is
`e41cb8557cf9217915ae80031a245f2133f8ba3f5b1b14aa70cc6aa973e1f6ac`.

## Outcomes

All 216 hosted records match the frozen and historical task order, IDs,
families, models and expected predicates. Every retained arm acceptance,
detection, freshness, determinism and error field equals the historical
record. There are 648 arm observations on **216 unique designed cases**;
repeating this same matrix does not double the scientific sample size.

All 13 endpoint dictionaries, including their descriptive intervals, match
the original. Full binding accepts 48/48 valid requests with 48/48 repeated
agreement, detects 72/72 semantic contradictions and 24/24 stale expected
hashes, detects 48/48 later geometry changes, and retains 24/24 non-geometric
changes as current. Hash-only and unbound arms miss all 72 semantic
contradictions; hash-only detects 48/48 later geometry changes and unbound
detects 0/48. No study execution errors are recorded. The frozen scorer's
disposition remains `SUPPORTED_WITHIN_CONTROLLED_CONTRACT`.

The audit extracts only the five pure analysis functions from the verified
frozen source and regenerates both historical and hosted `metrics.json`
**byte for byte**. It verifies both ledger-to-manifest-to-raw/metrics digest
chains. Hosted identities are:

| File | SHA-256 |
| --- | --- |
| `run/raw_results.jsonl` | `0e6e61dfc61934e074836f30d42db7bfea508f19d386095af8ba182a5d5bdd79` |
| `run/metrics.json` | `4f6eaec3c551af8821164a5231179fbbd82d8c009d256f51f4ac7d5f32e91a8d` |
| `run/manifest.json` | `8ab327a13d1a6682579efbe0cd3b49ae1572c184f8e1f75b63023b77b10a8e72` |

The raw records contain contract verdicts and within-run determinism flags,
not full numerical analytical reports. These artifacts therefore establish
agreement of the retained contract outcomes; they do not establish bitwise
cross-host identity of every numerical physics output.

## Engineering and environment

The frozen `tests/` invocation reports **1,203 passed, nine skipped, zero
failures and zero errors**. The console and all 1,212 JUnit entries agree.
Three skips are module collection skips; the other six are test skips.
All concern unavailable optional `build123d` or `gmsh` backends. This is not
a claim that those optional native backends were exercised. Console test
duration is 66.56 seconds.

The run records Python 3.12.14 on Linux x86-64. The original records Python
3.14.0 on macOS ARM64. The hosted resource receipt preserves the original
2,048-MiB disk and 512-MiB memory floors, with 85,648.8203125 MiB free disk
and 14,978.5703125 MiB available memory. The dependency version receipt
matches the frozen Linux lock pins; the job log records locked pip 26.2.1
installation and a successful dependency check. These are retained runtime
receipts, not binary or cryptographic execution attestations.

Only evaluation/verification timing, 48 path-dependent binding hashes and
120 report byte counts differ across hosts. Every full receipt is 56 bytes
shorter, consistent with the 56-character shorter output prefix and the
source's embedded absolute project path. The hosted full/hash-only/unbound
upper-middle timing values are 0.307244/0.143867/0.008082 ms, over
120/192/216 successful evaluations; conventional medians are
0.306703/0.143862/0.008082 ms. No speed claim follows from different hosts
or these unequal successful-only denominators.

## Interpretation and repeatable audit

This is one internal post-outcome reproduction under another environment.
The original runner's `confirmatory` phase string is retained unchanged;
the wrapper declaration explicitly records known prior outcomes and
`independent_party=false`. It is neither independent confirmation nor a
Kaggle run. It supplies no physical, intended-user or external-language
validation. The earlier local preflight is recorded in
`research/recovery_20261022/evidence_audit.json` under
`reproduction_preflight`: `NOT_EXECUTED_RESOURCE_GATE`, with
`attempt_started=false`. That audit record retains observed storage values
and clean-source checks. No local study execution log was produced because
the case execution was never launched.

From the repository root, with the frozen Git object available:

```bash
python3 research/recovery_20261022/audit_hosted_reproduction.py \
  --check research/recovery_20261022/hosted_reproduction_audit.json
```

The standard-library-only validator is read-only in this mode. Its complete
machine-readable report includes every extracted file hash, frozen source
hash, endpoint, raw-field difference, dependency version and skipped test.
