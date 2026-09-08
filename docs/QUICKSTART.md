# Install and use NeuroCAD

Requires Python 3.10+. CI covers 3.10–3.13; OpenSCAD is needed only for compiled
STL and rendered mesh workflows. NeuroCAD is a bounded alpha, not arbitrary CAD.

## Obtain the current review candidate

As checked on 2026-09-08, the repo is private, PR #49 is draft, and there is no
published `v0.5.0a6` tag. With authorized GitHub access, use a **new directory**:

```bash
gh repo clone THE-BU1LD/NeuroCAD
cd NeuroCAD
gh pr checkout 49
```

Do not run checkout commands over unrelated uncommitted work. PR #49 is a review
candidate; checking it out does not merge it or make the repo public.

## macOS / Linux

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
neurocad doctor
```

Alternatively, from this checkout, install a persistent user-owned command:

```bash
NEUROCAD_PACKAGE="$PWD" sh ./install.sh
```

The installer prints PATH instructions, stages a new virtual environment, checks
the version, dependencies and generation, then replaces only owned launchers.
Failure before publication preserves the previous command. Old environments remain
under `~/.local/share/neurocad/releases/` (the original layout may use `venv/`).
Rollback is selecting an existing prior environment's `bin/neurocad` directly;
no retained environment is automatically deleted. Do not use sudo.

## Windows PowerShell

No activation-policy change is needed; run the environment executables directly:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\neurocad.exe doctor
.\.venv\Scripts\neurocad.exe create "a 120 x 80 x 4 mm plate with four 4 mm holes" -o plate.scad
```

## First usable outputs

```bash
neurocad create "a 120 x 80 x 4 mm plate with four 4 mm holes" -o plate.scad --manifest plate.json
neurocad ir "a 120 x 80 x 4 mm plate with four 4 mm holes" -o plate.ncad.json
neurocad compile plate.ncad.json --format scad -o edited.scad
neurocad demo
```

The demo opens a loopback-only workbench. It is not an authenticated cloud portal.
For STL, install [OpenSCAD](https://openscad.org/downloads.html), add its executable
directory to PATH, and verify `openscad --version`. Then:

```bash
neurocad export "a 120 x 80 x 4 mm plate with four 4 mm holes" --format stl -o plate.stl
neurocad topology plate.stl --require-closed-manifold -o topology.json
neurocad tolerance docs/examples/tolerance.json -o tolerance-report.json
```

See [Product workflow](PRODUCT_WORKFLOW.md) for editable enclosures, revisions,
fit samples, calibration, and reviewed KiCad/file handoffs. Existing outputs are
refused; choose a new filename or explicitly use `--force` where available.

## Common failures

- Incomplete prompt: specify every overall/feature dimension; arbitrary prompts
  outside the grammar are rejected rather than guessed.
- OpenSCAD absent: SCAD/JSON still work; install the kernel for STL.
- Kernel timeout: inspect system load and model complexity. CLI export has an
  explicit `--timeout`; increasing it is an operator choice, not evidence of fit.
- Install target occupied: the installer refuses unrelated files. Choose a new
  `NEUROCAD_BIN_DIR` or review the conflicting file yourself.
- Private GitHub/tag unavailable: obtain an authorized checkout and use the local
  command above. No secret should be embedded into a URL or script.

Public installation still requires reviewed main, an authorized visibility change,
a passing release tag/workflow, attached checksummed artifacts and a credential-free
install test. Local installation is not a substitute for those gates.
