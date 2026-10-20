# Feature IR fail-closed hardening — candidate receipt

Status: focused local verification passed; hosted verification pending.

## Identity

- Upstream repository: `THE-BU1LD/NeuroCAD`
- Merged baseline: `ca15203738fd45113ace7ee649543a42717c5787`
- Candidate branch: `codex/neurocad-perfect-20261020`
- Candidate code commit: `14c2e10edd288d8ebf8be6afe5e295f2f4307a90`
- Recorded at: `2026-10-20T15:56:11Z`

## Defect and repair

Malformed JSON values in fields used as hash keys or set members could reach
`validate_feature_program` and raise raw `TypeError` exceptions. Affected
surfaces included parameter and feature identifiers, units, kinds, input
references, selector provenance, and output identifiers. Design-parameter roles
also lacked the bounded string validation already applied to feature roles.

The candidate validates scalar types before hash/set membership, constructs the
parameter-value map only from string identifiers, validates design-parameter
roles, and performs output duplicate detection without constructing a set from
untrusted values. Regression cases exercise malformed list/object values across
all affected fields and require the public parser to raise
`FeatureIRParseError`.

## Verification performed

The repository's maintained Feature/Requirement IR gate was run from the
existing development environment with third-party pytest plugin autoload
disabled and BLAS/OpenMP thread counts capped at one:

```text
71 passed, 7 skipped in 5.29s
```

The seven skips are native `build123d` cases; they are not reported as passes.
The matching scoped Ruff gate passed, and `git diff --check` passed.

## Resource and claim boundary

Free plus speculative memory was 240.9375 MiB after the focused run, below the
repository's 512 MiB admission floor. The heavy/native local suite was therefore
not run. Hosted checks remain required before this candidate can be merged or
described as fully verified.

No frozen research protocol, result, paper, release asset, or tag was changed.
This repair is software-boundary evidence only. It does not establish physical
fit, manufacturing safety, scientific validity, independent reproduction, or
intended-user usability. Published prerelease `v0.5.0a6` remains unchanged.
