# Public alpha completion — 2026-10-14

**PASS: v0.5.0a6 published and anonymously installed.**

Release: https://github.com/THE-BU1LD/NeuroCAD/releases/tag/v0.5.0a6
Source: `5ce2092db7203cf2bd532a742ea0697e1cf8479c`
Merged PR: https://github.com/THE-BU1LD/NeuroCAD/pull/103

## Completed checklist

- [x] Exact candidate reviewed; 12 engineering checks passed; Bugbot later completed with no findings.
- [x] Full matrix on merged main passed: Python 3.10/3.11/3.12 packaging, Python 3.13 portable Linux/macOS/Windows, three browsers, optional build123d.
- [x] Published tag and prerelease with wheel, sdist, SHA256SUMS and generated RELEASE_PROVENANCE.json.
- [x] Enabled GitHub server-side immutable releases and republished the same release without changing its tag or assets. API reports `immutable: true`; signed release attestation and both downloaded package assets verified with `gh release verify` / `verify-asset`.
- [x] Reproducible double builds, archive inspection, locked dependency/security checks, fresh wheel/sdist installs and extracted-source tests passed.
- [x] Public downloads without credentials verified exact tag/SHA, prerelease state, installer bytes and artifact hashes.
- [x] Public installer installed the published wheel into a clean environment; doctor, edits, invalid inputs, collision protection, stale revisions, compiled body/lid meshes and tamper rejection passed.
- [x] Default tagged-source installer passed in a second fresh environment.
- [x] Retained both public artifact files from hosted evidence and independently rehashed them locally.
- [x] Updated onboarding, release notes and canonical product status; preserved frozen research.

## Evidence

- `main-ci.json`: run 38495962707, PASS at released SHA.
- `release-ci.json`: run 38498546483, all five jobs PASS.
- `anonymous-install.json`: PASS including default tagged-source path.
- Post-lock anonymous recheck also passed: https://github.com/THE-BU1LD/NeuroCAD/actions/runs/38501125026.
- `enclosure-acceptance.json`: installed compiled-mesh commands and results.
- `published/RELEASE_PROVENANCE.json`, `published/SHA256SUMS`, `published/release.json` (initial publication).
- `published/immutable-release.json`, `published/attestation-verification.txt` (final locked state).
- Source tests: 1,227 passed / 9 skipped; extracted-sdist tests: 1,220 passed / 9 skipped (separate suites, not additive).
- 14 focused workflow tests passed locally. Local full installs/builds were not run below the 512 MiB resource floor.

## Preserved failures and corrections

1. Run 38494422164: test set-comprehension lint and Windows import of the POSIX-only frozen study harness. Corrected lint; explicitly scoped the research harness to Unix, preserving portable product tests. Excluded repository-only study tests from source packages, as they depend on Git and unshipped frozen study inputs.
2. Run 38494859698: the release-shell regression parsed a following YAML job as shell. Corrected its YAML block boundary; retained alpha/RC/stable labeling checks.
3. A redundant local public-installer curl stalled and was terminated. It produced no successful download receipt. Hosted credential-free download and both installations subsequently passed.

4. Documentation-only run 38501257817: README wording omitted the literal anonymous-install gate phrase required by an integrity test. Restored that phrase while stating its verified PASS status; no test or release code changed.

## Artifact hashes

- Wheel: `3c301397c4d9e33a29f854228d304e6101f25ba9e26485c2a4a0c511b2e3ac1c`.
- Source distribution: `357a778679d8710e864187e3b88fbb39e63dacd87d8affc1f306e5654d86b456`.

## What still needs the owner

Nothing to complete this bounded public-alpha release. Physical prints/fit measurements, human usability studies and independent scientific reproduction remain separate work. The hosted anonymous-install receipt excludes persistent OS service setup. No scientific conclusion, frozen protocol, research release tag or protected outcome was changed. The release is an alpha design aid, not production or safety certification.
