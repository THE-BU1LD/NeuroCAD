# NeuroCAD public-alpha evidence ledger

This ledger separates configured release machinery from observed release
evidence. No filename, checksum, test total, commit, or CI result is copied into
this document by hand.

## Release target

- Declared source version: `0.5.0a6`
- Target tag: `v0.5.0a6`
- Current status: **PENDING**
- Scientific-claim status: unchanged by release engineering

The checked-in historical `dist/` directory ends at a5. It is not evidence for
an a6 release. Local a6 candidates have been built and smoke-installed in an
ignored staging directory, but they are not authoritative release artifacts.
The 2026-09-06 audit initialized a new local Git baseline, explicitly not
recovered history. This checkout still has no remote, tag, or external CI
receipt.

## Gate status

| Claim / gate | Status | Evidence required to close it |
| --- | --- | --- |
| Package metadata and CLI entry point exist | Verified by source inspection | `pyproject.toml` and maintained tests |
| CI/release workflows are configured | Verified by source inspection | Pinned action SHAs and pinned quality-tool versions in `.github/workflows/` and `pyproject.toml` |
| Current tests/lint/type/security gates pass | Verified locally; external receipt pending | Successful CI URL for the exact release commit |
| a6 wheel and sdist build | Verified as local candidates; release build pending | Fresh artifacts listed in generated `RELEASE_PROVENANCE.json` |
| Exact artifacts clean-install | Verified locally for the candidate wheel; release job pending | Successful wheel and sdist smoke steps in the same release job |
| Full kernel-backed research rerun | Pending | Fresh, non-resumed run manifest retained by the release job |
| Anonymous installer succeeds | Pending | Credential-free environment receipt against the public tag |
| `v0.5.0a6` is public and externally installable | Pending | Public tag/release URL and independently verified artifact hashes |

## Authoritative generated receipt

The tag workflow creates `RELEASE_PROVENANCE.json` only after tests, static
gates, builds, clean-install smokes, and a fresh kernel run succeed. It records:

- repository, commit SHA, tag, workflow run ID and attempt;
- Python, platform, and OpenSCAD version;
- declared/installed package version and exact installed tool/dependency versions;
- maintained source-tree digest and per-file hashes;
- research-lock SHA-256;
- the fresh research manifest digest and its deterministic scientific hashes;
- wheel and sdist filenames and SHA-256 values;
- the quality gates completed before receipt creation.

The sibling `SHA256SUMS` is generated from the same fresh output directory. CI
retains both files with the distributions and attaches them to the GitHub
release. Those generated files—not prose in this ledger—are the authoritative
release evidence.

## External verification record

After a real release, link observed evidence without transcribing its contents:

```text
ci_run_url=
release_url=
generated_release_provenance_url=
anonymous_install_receipt_url=
independent_verifier=
verified_at_utc=
```

## Scientific integrity boundary

Packaging, installability, CI health, and checksum provenance are software
quality evidence only. They do not upgrade the frozen synthetic benchmark into
natural-language, manufacturability, learned-model, or safety evidence.

## Definition of done

The public-alpha gate closes only when a credential-free user can trace a
successful invocation from the public tag to the exact commit, external CI run,
generated provenance receipt, and downloaded artifact checksum.
