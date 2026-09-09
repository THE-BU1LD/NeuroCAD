# Contributing

NeuroCAD accepts changes to the documented plate, rectangular box/enclosure, and
basic primitive workflow. New domains must not be advertised as supported until
they have strict parsing, semantic validation, exact expected-geometry tests,
compiled OpenSCAD coverage, and a fabrication review plan.

Set up and run the maintained gates:

Install Node.js 18 or newer for the shipped browser-script regression tests.
Node is a test dependency, not required to install or run NeuroCAD. CI explicitly
checks its availability so those tests cannot silently skip there. OpenSCAD is
required for the kernel-specific tests; a kernel-free run is not full release
validation. Keep source files unchanged during research tests: their provenance
guard intentionally rejects runs whose implementation changes mid-experiment.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
node --version
python -m compileall -q neurocad_cli.py text_to_cad.py text_to_openscad.py core
python -m pytest -q tests
neurocad doctor
```

`PYTHON_BIN=.venv/bin/python sh scripts/test.sh` runs the maintained tests,
lint, typing and dependency consistency checks, and requires the Node harness.
CI additionally runs security audits, real browsers, reproducible builds and
fresh installations. The sdist includes its test dependencies' source files;
only `tests/test_repository_archive.py` is omitted because it checks historical
files deliberately excluded from distributions. Its two checks still run in
every checkout CI run. CI and release also extract and execute the sdist tests
so a successful package install cannot hide missing test inputs.

If OpenSCAD is installed, also run:

```bash
neurocad validate "a 120 x 80 x 4 mm plate with four 4 mm holes" --compile
neurocad export "a 40 x 30 x 3 mm plate with four 3 mm holes" --format stl -o /tmp/neurocad.stl
```

Every parser change needs success and rejection tests. Never silently substitute
a fabrication-critical dimension. All geometry lengths remain millimetres from
parsing through manifests, SCAD, STL verification, and documentation.

## Real-browser acceptance

The fast Node harness protects async state logic; it does not simulate away the
need for real imports, keyboard focus, downloads and layout checks. Install the
optional, pinned [Playwright test tooling](https://playwright.dev/python/docs/library)
separately from normal runtime dependencies:

```bash
python -m pip install -e '.[browser]'
python -m playwright install chromium firefox webkit
python tests/browser/run_workbench.py --require-kernel --output /tmp/neurocad-browser-run-1
```

Use a new output directory per run. The default runs Chromium, Firefox and WebKit;
`--browser chromium` selects one during development. The runner fails if a
required browser/kernel is missing. Omitting `--require-kernel` is a UI-only run,
not the required CI lane. On Linux CI, browser installation uses `--with-deps`.

Successful runs retain source-bound receipts, actual project/STL downloads,
responsive screenshots and browser traces. Failures retain diagnostic artifacts
but do not write a success receipt. Fixtures are synthetic engineering requests;
no physical fit or screen-reader compliance is inferred from these results.
Do not edit product sources during a run: the receipt guard rejects changing
sources. The CI browser jobs are mandatory failures, not `continue-on-error` jobs.

## Optional external import acceptance

With Blender installed, verify the exchange bundle first, then run Blender in a
separate factory-startup process. Use a fresh output directory:

```bash
neurocad integrations verify controller-exchange
blender --background --factory-startup --python scripts/check_blender_import.py -- \
  --bundle controller-exchange --output /tmp/neurocad-blender-run-1
```

The script imports each STL at 0.001 scale (millimetres to Blender's internal
metres), checks part count and dimensions, then saves a `.blend` review scene and
a receipt containing file hashes, importer settings and Blender version. This
validates file exchange; it does not create a native parametric CAD feature tree.
