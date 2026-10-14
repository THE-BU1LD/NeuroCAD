# NC-PHYSICS-V2-PROVENANCE research state

## Current verdict

`CONFIRMATORY_SUPPORTED_WITHIN_CONTROLLED_CONTRACT / INTERNAL_CLEAN_CHECKOUT_PASS / RELEASE_PACKAGED / EXTERNAL_VALIDATION_OPEN`

This is a versioned successor to the terminal NeuroCAD controlled-compiler
study. It does not reopen, overwrite, or upgrade the predecessor's evidence.

## Research question

For bounded analytical-physics requests over NeuroCAD agent primitives, do
geometry-, material-, and load-bound receipts detect predeclared stale or
contradictory analyses that an unbound request file cannot detect, while
retaining deterministic valid-case behavior?

## Contribution boundary

The intended contribution is an executable reference contract plus a controlled
conformance study. It is not a new physics method, FEA/CFD system, material
authority, full CSG property engine, safety proof, or general CAD/CAE result.

## Central mechanism

Each result retains the exact analytical inputs and hashes of the complete
request, selected CAD component geometry, versioned material card, and named
load case. Exact geometry/model mappings are checked before evaluation. Saved
reports can be rechecked against the current component; geometry drift yields a
machine-readable stale result and a nonzero exit status.

## Primary falsifiers

- Any in-scope contradiction is accepted by the full binding.
- Any in-scope geometry mutation leaves a bound result current.
- Any declared non-geometric mutation invalidates the geometry receipt.
- Valid bound requests lose deterministic scientific fields.

## Resource state

Initial checks on 2026-10-11 were below the mandatory 512 MiB research-run
floor. Protected materialization later passed the unchanged gate. Freeze passed
with 868.71875 MiB free plus speculative memory and over 2 GiB free storage.
The single execution subsequently passed with 1004.328125 MiB free plus
speculative memory and over 2 GiB free storage. The execution ledger now
prohibits a version-1 rerun.

## Development evidence

- `NC-PHYS-V2-DEV-001`: retained harness failure, `NO_RESULT`; a relative
  project path was resolved twice.
- `NC-PHYS-V2-DEV-002`: 12/12 bounded development cases behaved as declared,
  with no execution errors. This is development evidence only.
- The two-revision development budget is exhausted. Version 1 must now remain
  unchanged or be superseded by a new version before protected execution.
- The version-1 implementation and pre-results manuscript were committed at
  `faeede8`; a subsequent governance-only commit records that identity.

## Frozen identity

- source commit: `2627c106ede6c2ac4e3570700f2bd545a763943c`
- case count: 216
- case-file SHA-256: `9caa80fb7e5257f514143ec0b297711464767c5a68ffa49988070a2f97c94c49`
- semantic case SHA-256: `2e6bb79b5a649b191fb7b9a0635b9e0ae4053aae8d23b72af104fc5937ac0696`
- outcome state: observed once; execution ledger locked

## Confirmatory result

- disposition: `SUPPORTED_WITHIN_CONTROLLED_CONTRACT`
- cases: 216; execution errors: 0
- valid full acceptance and determinism: 48/48 each
- full-binding contradiction detection: 96/96 across geometry, material, load,
  and stale expected-hash families
- post-result geometry detection: full 48/48; hash-only 48/48; unbound 0/48
  because the control exposes no freshness mechanism
- non-geometric specificity: full 24/24; hash-only 24/24
- paired full-only versus unbound-only drift detections: 48 versus 0; exact
  two-sided McNemar `p=7.105427357601002e-15`
- internal post-outcome artifact audit: pass, with no case re-execution

These results are controlled synthetic conformance evidence. They are not
physical validation, solver validation, safety evidence, algorithmic novelty,
enterprise CAD/CAE generalization, independent reproduction, or external
adjudication.

The result artifacts were committed at
`64ec85fa0b98f170ee4b6b205111ed27ae0bbd36`; the following governance-only
commit records that identity.

## Release verification

The release candidate was committed at
`0896fba43336c03af8bd5ff7008506691832d7f5` and verified from a fresh local
clone made with `--no-hardlinks`. Without executing a study case, the locked
raw evidence regenerated `generated_results.tex` and the post-outcome audit
byte-for-byte. Repository and minimal two-file arXiv sources both compiled to
six-page PDFs whose extracted text matched the committed paper. The clean
checkout passed 1,203 tests with 9 expected skips in 186.93 seconds, scoped
Ruff checks, and mypy across 71 in-scope source files.

This is internal clean-checkout verification using the project's existing
locked virtual environment. It is not a clean-environment dependency install,
independent reproduction, external adjudication, physical validation, or an
arXiv submission receipt. Exact author metadata, arXiv license/category,
submission, and independent execution remain external actions.

## Release identity

- release version: `NC-PHYSICS-V2-PROVENANCE-v1.0.0`
- release source commit: `9d3733ca15816f23c63f5382dedef548d0034ea7`
- local tag: `physics-v2-v1.0.0`
- final six-page PDF SHA-256:
  `8747cdb42ad497a0a24217bac9af7762461e8f9bb9c4070d15b27fe99cc5cfb5`
- minimal two-file arXiv source SHA-256:
  `2b2c34c6c66e98067ca716e35a1c06709c7b036d8ec0014185f96840d8fc7c78`
- 53-file release manifest SHA-256:
  `f74f2cdc560447c012b00f11b608b55be30b834e5faecdb41706409ba2d1b3fb`
- complete release archive SHA-256:
  `386079a3cec9b5f417a8ec7ae88858540be3eacdc4f7dc5fbf3f534aff452372`

The release package was extracted and all 53 manifest entries were rehashed
successfully. The arXiv bundle contains only `main.tex` and
`generated_results.tex` and compiles locally. These are local technical release
receipts, not publication or external-verification receipts.

The machine-readable authority is `RESEARCH_STATE.json`. Update it before every
session ends and preserve negative, mixed, invalid, and blocked outcomes.
