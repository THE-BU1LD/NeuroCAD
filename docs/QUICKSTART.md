# Install and use NeuroCAD

Requires Python 3.10+. CI covers 3.10–3.13; OpenSCAD is needed only for compiled
STL and rendered mesh workflows. NeuroCAD is a bounded alpha, not arbitrary CAD.

## Obtain the current review candidate

As checked on 2026-09-09, the repository is public, PR #49 is the integration
candidate, and there is no published `v0.5.0a6` tag. No GitHub credentials are
needed to clone it. Use a **new directory**:

```bash
git clone https://github.com/THE-BU1LD/NeuroCAD.git
cd NeuroCAD
git fetch origin pull/49/head
git switch --detach FETCH_HEAD
git rev-parse HEAD
```

Do not run checkout commands over unrelated uncommitted work. PR #49 is a review
candidate; checking it out does not merge it or establish a tagged release.
Record the printed commit ID when sharing results so later branch updates are
not confused with the version you tested.

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

### Save, reopen, and export from the workbench

1. Enter an explicit supported enclosure description and choose **Interpret,
   validate & preview**. Review the specification and fabrication warnings.
2. **Save project** downloads canonical enclosure JSON, including its source,
   project ID, revision and change history. OpenSCAD and canonical IR downloads
   are available for each part without installing OpenSCAD.
3. Use **Open saved enclosure project** to reopen that JSON, including projects
   revised with `neurocad enclosure edit`. The current specification drives the
   build; historical prompt text is not re-interpreted. Invalid imports leave
   the current input and output intact. Files are limited to 1 MiB; the encoded
   API request must also fit in 1 MiB.
4. Under **Edit the validated project**, enter an exact edit such as
   `set wall thickness to 2.4 mm`. Optionally give a reason, then select
   **Review proposed edit**. Inspect the before/after values and explicitly
   **Apply reviewed revision** or discard it. Invalid proposals do not replace
   the current project. Applied edits preserve the original prompt and append
   history; download the revised project. Feature IDs are shown beside the editor.
5. Choose **Compile verified mesh & download STL** for actual kernel validation
   and per-part mesh downloads. Source validation alone leaves kernel geometry
   explicitly **unverified**. Physical fit remains unverified in both cases.

Input modes retain separate drafts within the tab. There is no browser or cloud
autosave: download the project before closing or reloading. Unsaved drafts trigger
replacement confirmation and a leave-page warning where the browser supports it;
mobile browsers may not show leave-page warnings. A download click is only a
request: confirm that the browser saved the file. Warnings remain active until
you reopen a saved project, and other unsaved mode drafts still need attention.
Editing invalidates
output and cancels obsolete browser requests; it does not promise cancellation
of a kernel process already running. Ctrl/Command + Enter validates the input.
The default compile deadline is 30 seconds per part. For heavier designs, you can
explicitly select 60 or 120 seconds; the single-compiler lock and all geometry,
input, output-size and verification limits remain enforced. The browser allows
twice the selected budget plus 30 seconds for an enclosure's body and lid (90
seconds by default). Validation/edit/file-open requests retain a 90-second limit.
A server-side kernel deadline returns HTTP 504 with `code: compiler_timeout`;
missing OpenSCAD returns HTTP 503 with `code: compiler_unavailable`. A timeout
publishes no new mesh. A failed compile retains previously validated source and
project downloads for unchanged input. If the compiler is busy, wait and retry;
the API returns HTTP 503 with `Retry-After: 5`, not an invalid-design error.
STL links expire after ten minutes or earlier cache eviction. Source downloads
remain available until the displayed output is invalidated or the tab closes.

### Compile and inspect a mesh

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
