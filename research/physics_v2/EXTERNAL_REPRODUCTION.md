# External reproduction handoff

**Status:** `READY / NOT EXECUTED BY AN INDEPENDENT PARTY`

This handoff was authored after the primary result. It is not a preregistration
and cannot make the existing result independent. A reproduction may be called
independent only when source checkout, execution, artifact custody, and
adjudication are performed by a party that did not author the implementation,
cases, analysis, or primary paper.

## Fixed starting identity

- checkout commit: `786ba9ba5c2249a710529c3b07bf82d4e29c7f36`
- frozen source commit recorded by the receipt:
  `2627c106ede6c2ac4e3570700f2bd545a763943c`
- case-file SHA-256:
  `9caa80fb7e5257f514143ec0b297711464767c5a68ffa49988070a2f97c94c49`
- semantic case SHA-256:
  `2e6bb79b5a649b191fb7b9a0635b9e0ae4053aae8d23b72af104fc5937ac0696`
- freeze-receipt SHA-256:
  `e41cb8557cf9217915ae80031a245f2133f8ba3f5b1b14aa70cc6aa973e1f6ac`

The checkout commit contains the frozen manifest and receipt but precedes the
primary execution ledger and outcomes.

## Independence declaration

Before execution, the reproducer should record:

1. name or organization and contact route;
2. relationship, funding, and conflicts with the author or project;
3. whether primary metrics were viewed before artifact sealing;
4. hardware, operating system, Python identity, and dependency installation;
5. exact checkout and all input-file hashes;
6. the designated custodian and immutable storage location for outputs.

Because the primary result is now public in later commits, a fully blinded
reproduction may no longer be possible. That limitation must be disclosed.

## Execution

Use a fresh clone or worktree at the fixed checkout. Install the declared
dependencies from `requirements-research.lock`, verify a clean Git state, and
run the full engineering tests. Do not edit the source, protocol, manifest,
freeze receipt, endpoints, thresholds, or exclusions.

The study itself enforces at least 512 MiB free plus speculative memory, at
least 2 GiB output storage, a new output directory, clean Git, exact frozen
source and case hashes, and an absent execution ledger. Execute exactly once:

```bash
python research/physics_v2/study.py run \
  --phase confirmatory \
  --cases research/physics_v2/frozen/NC-PHYS-V2-CONFIRM.jsonl \
  --freeze research/physics_v2/frozen/freeze.json \
  --output research/physics_v2/runs/NC-PHYS-V2-EXTERNAL-001
```

The ledger is written before case execution. A crash consumes the attempt; it
must be reported rather than silently retried. Archive the ledger, raw JSONL,
metrics, manifest, test logs, dependency inventory, and independence
declaration before comparison with the primary result.

## Adjudication

An independent adjudicator should verify all hashes and recompute family counts
and endpoint numerators directly from raw JSONL. Classify the reproduction as:

- `REPRODUCED_WITHIN_CONTROLLED_CONTRACT` only if the run is valid, all 216
  records are retained, no execution error occurs, and every applicable frozen
  endpoint meets its 100% threshold;
- `MIXED` if at least one endpoint misses while evidence remains interpretable;
- `NEGATIVE` if a core claim is falsified;
- `INCONCLUSIVE` for a retained infrastructure failure;
- `INVALID` for protocol, identity, exclusion, or artifact-integrity failure.

No reproduction outcome establishes physical accuracy, manufacturing safety,
solver validity, or enterprise CAD/CAE generalization.
