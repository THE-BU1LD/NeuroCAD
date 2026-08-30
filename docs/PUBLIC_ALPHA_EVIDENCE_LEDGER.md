# NeuroCAD Public Alpha Evidence Ledger

This file separates verified release evidence from pending release claims. It is intentionally conservative: a gate remains **PENDING** until evidence from the exact release commit is recorded.

## Release target

- Target tag: `v0.4.0a1`
- Release class: public alpha
- Scientific-claim status: unchanged by release engineering

## Evidence table

| Claim / gate | Status | Evidence | Missing evidence |
| --- | --- | --- | --- |
| Packaged CLI exists | VERIFIED | Repository history contains `feat: add NeuroCAD command line interface` and subsequent packaging/release hardening commits. | None for existence; exact release invocation should still be recorded below. |
| One-command installer exists | VERIFIED | Repository history contains `feat: add one-command NeuroCAD installer` and `installer: remove git dependency and harden bootstrap`. | Anonymous clean-environment execution on the final public commit. |
| Release CI covers supported Python versions | VERIFIED | Public-alpha hardening PR records passing matrix jobs on Python 3.10, 3.11, and 3.12 prior to merge. | Re-run on the exact commit that will be tagged after public visibility is enabled. |
| Wheel/sdist can be built and clean-installed | VERIFIED PRE-RELEASE | Public-alpha hardening PR records wheel/sdist build plus clean virtualenv wheel-install smoke test. | Repeat on exact tagged/public commit and retain run URL/artifact checksum. |
| Repository is safe for anonymous public bootstrap | PENDING | Secret-history gate passed during pre-release CI. | Public visibility transition plus anonymous bootstrap from a credential-free environment. |
| `v0.4.0a1` is externally installable | PENDING | Release automation exists. | Public repo, exact-commit CI pass, anonymous installer pass, tag, artifact verification. |

## Exact release evidence

Fill this section only with observed values from the final public release candidate.

```text
commit_sha=
ci_run_url=
python_versions=
installer_command=
installer_environment=
cli_smoke_command=
cli_smoke_output=
wheel_filename=
wheel_sha256=
sdist_filename=
sdist_sha256=
tag=
release_url=
verified_at_utc=
```

## Scientific integrity boundary

Release engineering does not upgrade scientific confidence. Packaging, installability, CI health, and documentation are evidence about software quality only. Any negative, contradicted, or falsified NeuroCAD research finding must remain represented as such in research documentation.

## Definition of done

The public-alpha gate is complete only when a new user with no repository credentials can execute the documented installer against the exact tagged public commit, invoke the installed CLI successfully, and trace the installed artifact back to the passing release evidence above.
