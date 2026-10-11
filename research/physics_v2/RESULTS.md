# NC-PHYS-V2-CONFIRM-001 results

## Verdict

`SUPPORTED_WITHIN_CONTROLLED_CONTRACT`

The single frozen execution completed all 216 synthetic cases with no execution
errors. This supports the predeclared software-contract claims within the
matrix. It does not establish physical accuracy, safety, solver validity,
algorithmic novelty, enterprise generalization, or independent external
validation.

## Primary outcomes

| Endpoint | Outcome |
|---|---:|
| valid full acceptance | 48/48 |
| valid full repeat determinism | 48/48 |
| full geometry/input contradiction detection | 24/24 |
| full material/input contradiction detection | 24/24 |
| full load/input contradiction detection | 24/24 |
| full stale expected-hash detection | 24/24 |
| hash-only semantic non-detection | 72/72 |
| unbound semantic non-detection | 72/72 |
| full post-result geometry-drift detection | 48/48 |
| hash-only post-result geometry-drift detection | 48/48 |
| unbound post-result non-detection | 48/48 |
| full non-geometric specificity | 24/24 |
| hash-only non-geometric specificity | 24/24 |

For the paired post-result mutation comparison, full-only detections were 48
and unbound-only detections were 0. The exact two-sided McNemar value was
`7.105427357601002e-15`. This describes the presence versus absence of the
predeclared mechanism; it is not a population effect or a general product
comparison.

## Diagnostics

Successful-evaluation median times on this host were 0.619 ms for full binding
(`n=120`), 0.248 ms for hash-only (`n=192`), and 0.013 ms for unbound
(`n=216`). Failed evaluations have no elapsed-time record, so these are
conditional samples and must not be treated as balanced performance arms.
Median full-receipt size was 3,902 bytes; maximum was 4,199 bytes.

## Locked identities

- execution commit: `786ba9ba5c2249a710529c3b07bf82d4e29c7f36`
- case-file SHA-256: `9caa80fb7e5257f514143ec0b297711464767c5a68ffa49988070a2f97c94c49`
- semantic case SHA-256: `2e6bb79b5a649b191fb7b9a0635b9e0ae4053aae8d23b72af104fc5937ac0696`
- raw-results SHA-256: `97bae6a791a16088d4b9902ccc45fd0f291751d3dde822f7fad5c21c4add9023`
- metrics SHA-256: `34bb77ddf92225a4ee85e5c3f2a67dbca74c1cda23f60e3c9548ddf3fb013573`
- manifest SHA-256: `d01bc8b449babcaec2805a056492d2a80dd1aa375b11d7461d2d2a0dc990f1a5`
- freeze SHA-256: `e41cb8557cf9217915ae80031a245f2133f8ba3f5b1b14aa70cc6aa973e1f6ac`
- paper PDF SHA-256: `8443a359789854d4aec8da99844d995044ccbd246cf0028e3f400cc716cba733`
- arXiv source SHA-256: `b9ec3c45f7280a38cb58a77283f92e65159b300b6adf0c439a1fb4575f8afa60`

The two release hashes above identify the original five-page result artifact
at commit `64ec85f`. The release-candidate paper adds audit appendices and an
explicit submission boundary without altering the generated results. Its final
hashes are recorded by the release receipt rather than overwriting the original
result identity.

The internal post-outcome audit passed without case re-execution. It is not an
independent reproduction or external adjudication.

The repository-wide engineering gate passed with 1,203 tests and 9 expected
skips. Ruff passed, and mypy reported no issues across 100 source files. These
are engineering checks, not additional scientific or external evidence.

The later clean-checkout release pass independently re-read the retained raw
artifacts (but did not independently author or execute the cases), regenerated
the analysis byte-for-byte, compiled both repository and arXiv sources, matched
the extracted PDF text, and passed 1,203 tests with 9 expected skips. See
`CLEAN_CHECKOUT_VERIFICATION.json` for its exact narrower boundary.
