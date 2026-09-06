# NeuroCAD reproducibility

This document distinguishes a fresh reproduction from the retained historical
run `NC-RUN-2026-09-03-FULL`. The historical directory is immutable evidence;
the reproduction command never resumes or overwrites it.

## Requirements

- CPython 3.12.14 for the controlled research reproduction;
- the exact Python package versions and distribution hashes in
  `requirements-research.lock`;
- native OpenSCAD for STL compilation and PNG rendering;
- on headless Linux, `xvfb-run` (recommended) or a working offscreen Qt plugin.

`requirements-research.in` is the reviewed direct-input set. Regenerate its
universal CPython 3.12 lock with:

```bash
uv pip compile requirements-research.in --generate-hashes --universal \
  --python-version 3.12 --output-file requirements-research.lock
```

The reproduction and release workflows install that lock with
`--require-hashes`. Every run also records the lockfile SHA-256, installed
versions, Python/platform identity, and OpenSCAD path/version/executable digest.
A kernel-required run refuses
to start when the lock digest is unavailable or the installed distribution does
not match the version declared by the source tree.

## Product checks

For ordinary development, use one of the supported Python versions and the
pinned tool extra:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,security]'
python -m pytest -q tests
python -m ruff check core research/vericodegen neurocad_cli.py text_to_cad.py text_to_openscad.py tests
python -m mypy core research/vericodegen neurocad_cli.py text_to_cad.py text_to_openscad.py
python -m pip check
python -m pip_audit
python -m bandit -q -r core research/vericodegen neurocad_cli.py text_to_cad.py text_to_openscad.py -x '*/__pycache__/*'
```

Do not copy the resulting test count into a truth ledger. Test inventory changes
with the source; the command exit status and CI receipt are the evidence.

## Fresh controlled-suite reproduction

Install native OpenSCAD, CPython 3.12.14, and (on headless Linux) Xvfb, then run:

```bash
./scripts/reproduce_research.sh
```

The script:

1. rejects any Python patch version other than 3.12.14;
2. creates a fresh disposable virtual environment;
3. installs the exact research lock and the current source;
4. runs compile, test, lint, type, dependency, and security gates;
5. creates a new uniquely named run directory;
6. compiles every kernel sample from source with artifact reuse disabled;
7. verifies the recorded source/lock/OpenSCAD provenance;
8. builds one wheel and one sdist in a fresh temporary directory and smoke-tests
the exact wheel.

Future NC-EXP-003 runs generate a unique, SHA-256-identified malformed fixture
for every record. They intentionally report no binomial confidence interval:
deterministic generated fixtures are regression cases, not an independent random
sample. The retained historical FULL run instead contains eight templates
repeated 30 times and must be interpreted at that eight-category boundary.

To choose the parent directory for a unique generated run:

```bash
NEUROCAD_RESEARCH_RUN_PARENT=/absolute/new-run-parent \
  ./scripts/reproduce_research.sh
```

To choose an exact output path, it must not exist:

```bash
NEUROCAD_RESEARCH_RUN_DIR=/absolute/path/NC-REPRO-MY-RUN \
NEUROCAD_RESEARCH_RUN_ID=NC-REPRO-MY-RUN \
  ./scripts/reproduce_research.sh
```

The script refuses an existing path and specifically refuses the canonical
frozen directory. A failed run remains a partial, non-manifested directory for
diagnosis; retry into a new path.

## Result and provenance files

Each successfully completed new run contains:

- `manifest.json`: full artifact-integrity hashes plus source, lock (or explicit
  absence for a non-archival run), package, Git (when available), Python,
dependency, and OpenSCAD executable provenance;
- `metrics/results.json`: complete outcomes and observed timing fields;
- `metrics/deterministic_results.json`: the scientific outcomes with
  host-load-dependent timing/memory fields removed;
- `metrics/runtime_receipt.json`: environment details and extracted timing
  observations.

`manifest.scientific_sha256` is the cross-run comparison target only after the
maintained-source, configuration, dependency-lock, Python, and OpenSCAD
provenance match. It excludes timing and host-load observations; it does not
promise bit-identical meshes or renders across different kernels or platforms.
`artifact_sha256` authenticates one retained snapshot and is expected to change
when timing receipts, platform paths, meshes, or renders differ.

The runner hashes its maintained source inputs before and after execution. It
refuses to write a final manifest if those inputs changed during the run.

## Headless rendering

On Linux, the reproduction script automatically re-enters through `xvfb-run -a`
when it is installed and no `DISPLAY` exists; otherwise it requests Qt's
offscreen backend. It deliberately does not force that backend on macOS because
OpenSCAD's renderer requires `NSOpenGLContext` there. CI installs Xvfb and
executes the research runner through it. OpenSCAD PNG production remains an
external-kernel operation, so its exact version is recorded in the runtime
receipt.

## End-to-end program check

```bash
neurocad ir "a 120 x 80 x 4 mm plate with four 4 mm holes" -o /tmp/plate.ncad.json
neurocad compile /tmp/plate.ncad.json --format scad -o /tmp/plate.scad
neurocad evaluate --ir /tmp/plate.ncad.json
neurocad compile /tmp/plate.ncad.json --format stl -o /tmp/plate.stl
```

The STL command requires OpenSCAD and fails nonzero when kernel execution or
mesh verification fails.

## Distribution and release evidence

Build into a fresh directory instead of the checked-in historical `dist/`
snapshot:

```bash
out=$(mktemp -d)
export SOURCE_DATE_EPOCH=$(git show -s --format=%ct HEAD)
python -m build --no-isolation --outdir "$out"
python scripts/normalize_sdist.py "$out"/neurocad_research-*.tar.gz "$SOURCE_DATE_EPOCH"
python -m venv "$out/verify"
"$out/verify/bin/python" -m pip install "$out"/neurocad_research-*.whl
"$out/verify/bin/neurocad" doctor
```

`SOURCE_DATE_EPOCH` makes the pure-Python wheel deterministic; the normalizer
also removes archive-creation time and local ownership from the source archive.
CI and release each build twice and compare both artifacts byte-for-byte.

The tag release workflow builds in the runner temporary directory and generates
`RELEASE_PROVENANCE.json` from observed commit, tag, tool, source, lock, kernel,
and artifact hashes. Documentation intentionally contains no copied candidate
hashes or fixed test total.

## Remaining provenance boundary

This checkout now has a local Git audit baseline, so local commit and dirty-tree
state are inspectable. It has no configured external remote, passing hosted CI
run, signed release tag, or retained generated release receipt. Public-release
or archival claims therefore remain pending until an exact revision passes the
external workflow and its generated evidence is retained.

Historical VeriCodeGen execution is governed separately by
`research/VERICODEGEN_2026_PROTOCOL.md`. Do not execute an external outcome run
without its explicit authorization and frozen-manifest requirements.
