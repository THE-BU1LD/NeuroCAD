# Engineering repair audit — 22 October 2026

## Scope and disposition

Two observed implementation defects were repaired against baseline commit
`66f02644d20c7876c0f9421045aae33f2fa9af9e`: Feature IR admission and demo-receipt
source attribution. This is bounded software verification. It does not reopen
the terminal mixed compiler study, establish an ML result, or supply independent
language, physical-fit, manufacturing, or safety evidence.

The implementation author performed a subsequent source-diff compatibility review.
No blocking compatibility issue was found in the reviewed changes; this is not
independent human review. The review introduced no source edits or optional test
runs. All 85 implementation-file hashes still match the completed native demo's
inventory. The table below additionally records the reviewed script, documentation
and tests; those additional files are outside that runtime identity inventory.

## 1. Feature IR admission

**Failure witnesses.** JSON lists or objects in parameter IDs, parameter units,
feature IDs/kinds, graph inputs, selector entities/provenance, or outputs reached
set/dictionary operations and raised `TypeError` instead of a structured parsing
failure. Malformed parameter roles were accepted. Explicit `null` values in
mandatory geometry fields, including a box's `size`, bypassed checks that treated
`None` only as the missing-field sentinel. Direct dataclass construction could
also send invalid containers into iteration or attribute access.

**Repair.** A shared structural gate validates record and container types before
graph lookup or feature dispatch. Required geometry fields reject explicit null;
operation names are type-checked before set membership. Parameter roles receive
the same bounded-string requirement as feature roles. Dictionary parsing rejects
nonstring keys and nonobject roots with `FeatureIRParseError`. Valid parameter
references, intentional optional null bounds/selector roles, and stable JSON
round trips are retained.

**Evidence.** The new 74-case authored admission suite failed 46 cases and passed
28 on the baseline; the repaired implementation passes all 74 as part of the
122-case focused cohort. These cases are targeted engineering counterexamples,
not a random sample or externally authored scientific benchmark.

## 2. Demo source attribution and stability

**Failure witnesses.** The original shell script generated artifacts with
`NEUROCAD_CLI` but imported/hashes source through `PYTHON_BIN`. Two different
installations therefore produced a receipt attributing artifacts to the wrong
code. The script also published a success receipt after an implementation/schema
change during generation. Both failures were reproduced through the real shell
script with mocked geometry commands; the mock geometry is not native CAD evidence.

**Repair.** The executing CLI now exposes `provenance --json`, recognized by the
normal CLI dispatcher. It reports hashes of the CLI, both compiler entry modules,
core Python source, JSON resources/schemas, JavaScript resources, and the packaged
JavaScript license. Names use stable relative POSIX paths. Before/after CLI
snapshots must agree, file-inventory digests must recompute, and CLI version must
match before the script writes receipt version `neurocad-demo-v2`. The receipt
writer cannot replace this identity with imports from its own installation.

**Compatibility review.** Existing Feature IR valid programs keep their representation;
the changes tighten malformed-input admission. The new provenance command is
additive. The updated demo script requires the candidate CLI containing that
command and will fail early with an older installed release. Normal package
discovery includes the new core module. The source uses APIs available in the
declared CPython 3.10–3.12 range; this session's execution used Python 3.12.14.

## Verification and retained failures

| Evidence | Observed result | Retained record |
| --- | --- | --- |
| Feature IR baseline, new authored suite | 46 failed; 28 passed | `feature-baseline.txt` |
| Feature IR candidate plus existing feature/inspection tests | 122 passed | `feature-candidate.txt` |
| Connected feature, inspection, CLI, revision, backend and export tests | 158 passed; 5 skipped | `feature-connected.txt` |
| Demo provenance baseline | 2 failed; 1 passed | `demo-provenance-baseline.txt` |
| Candidate demo and source-identity tests | 13 passed | `demo-provenance-candidate.txt` |
| Connected demo, source identity, integrity and CLI tests | 34 passed | `demo-provenance-connected.txt` |
| First full suite, restricted socket environment | 2208 passed; 13 skipped; 4 failed; 27 errors; 53 subtests passed | `full-tests.txt`, `full-tests.xml` |
| Full suite with socket access | 2240 passed; 12 skipped; 53 subtests passed; no failures/errors; 98.32 s | `full-tests-with-sockets.txt`, `full-tests-with-sockets.xml` |
| Native OpenSCAD demo | Completed; 32 artifact entries, matching source snapshots | `native-demo.txt`, `../native-demo/DEMO_RECEIPT.json` |

Ruff passed on changed source/tests; mypy passed for `core/feature_ir.py`,
`core/source_identity.py`, and `neurocad_cli.py`. Bash syntax and diff whitespace
checks passed. After resolving Git to a fixed absolute executable, the 10 source
identity tests passed again. Cohorts overlap and must not be added into a unique
test total.

All 31 nonpassing records in the first full-suite XML are
`PermissionError: [Errno 1] Operation not permitted` from socket creation, either
during a test or fixture setup. Their original output is retained. This first run
is not a passing full-suite gate. The rerun with socket access passes all 31 and
also runs the previously skipped durable-daemon case, explaining the increase
from 2208 to 2240 passes and decrease from 13 to 12 skips. The XML's 2305 record count includes the 53
passing subtests and should not replace pytest's top-level counts.

The 13 skipped records break down as follows:

| Missing capability | Skip records | Coverage not established by this run |
| --- | --- | --- |
| `build123d` absent | Five module collection skips and six individual test skips | Exact/native CAD, final bore/final geometry, native acceptance, STEP revision publication/reopening |
| `gmsh` absent | One module collection skip | Gmsh backend execution |
| Unix-domain socket support restricted | One individual test skip | Durable daemon job execution under the first environment |

The final socket-enabled run retains the 12 build123d/Gmsh skip records; its
durable-daemon case passes. Collection skips do not report how many tests inside the skipped modules would
have run. The native demo uses OpenSCAD 2021.01 and does not fill the missing
build123d/STEP or Gmsh coverage. Its implementation identity is
`64b9e70c64633cf94d52b6254178b6aaa7521a45869c97d4939a818b3a64935f`.
The native audit matched all 32 artifact entries and all 85 implementation files.

## Limits

The Feature IR remains an experimental representation; these repairs do not prove
all CAD contracts, arbitrary hostile Python-object handling, or native-kernel
correctness. Source identity is an on-disk snapshot. Loaded bytecode, third-party
dependencies, executable authenticity and transient changes restored before the
second observation are outside it. Observed Git HEAD and user-supplied revisions
are explicitly unverified against source bytes. A failed demo may leave partial
files, but source drift prevents a success receipt. Physical validation remains
`not performed` in the native receipt.

## Source identity at review

| File | SHA-256 |
| --- | --- |
| `core/feature_ir.py` | `eebba6a0bc8cd8df20d0d81d778b11a7e65d47edb0341eb46e00e6cb72edaa95` |
| `core/source_identity.py` | `c1e610205ea9496f143099da45708e0c26a7e067d07e36650a184d2844e7397d` |
| `neurocad_cli.py` | `bb9ae1cbd321c997dfc9fc64d274c8e88b753872e2872bd7fafc94fafef3e7d9` |
| `demo/build_demo_kit.sh` | `341b67cc94302a16fae4fb5a6dc4c040e75c98658ff13702a987dcf07531d0d1` |
| `demo/README.md` | `12047281d1f853cd15493d128bf4c9cc2c438e00ee3f666cfc8640553e1a6f0d` |
| `tests/test_feature_ir_malformed.py` | `5249dd8983ec98f518b6a5d76fbc03de449237409c09163a25eaec16f1d9d187` |
| `tests/test_demo_kit.py` | `fd8c7adb3d3c7d92a55ac1d2eee22819da9569599d4f7ab4592f846e163a8cf4` |
| `tests/test_source_identity.py` | `4fb22f3da4e358e152142430ec7903d838fe1f6f21a193ff4f1a8736ad4bbbf1` |

The three demo-provenance logs were copied byte-for-byte from their original
`/tmp/neurocad-demo-provenance-{baseline,candidate,connected}.log` files. No
failure text was removed, and no source, commit, protected evidence or native
artifact was altered while preparing this audit.
