# Enclosure installation and revision acceptance

Use a fresh virtual environment and a wheel built from the intended source.
Record the source revision and wheel SHA-256. Install dependencies normally;
do not use system-site-packages or an editable install for release acceptance.
OpenSCAD must be installed separately for the mesh acceptance gate.

From the checkout, after resource admission:

```bash
python3 -m venv .tmp-release-work/enclosure-clean
python3 -m build --wheel --outdir .tmp-release-work/enclosure-dist
.tmp-release-work/enclosure-clean/bin/python -m pip install .tmp-release-work/enclosure-dist/neurocad_research-0.5.0a6-py3-none-any.whl
.tmp-release-work/enclosure-clean/bin/python -m pip check
python3 scripts/verify_enclosure_install.py \
  --executable .tmp-release-work/enclosure-clean/bin/neurocad \
  --output .tmp-release-work/enclosure-acceptance \
  --require-stl
```

The output directory must be new. The driver executes the installed command with
an external working directory, clears PYTHONPATH, disables user site packages,
and retains command outputs and failures in `acceptance.json`. It checks:

- interpretation of an enclosure with a friction lid and USB cutout;
- one audited wall edit with all unrelated specification fields preserved;
- invalid edit rejection and preservation of the original revision;
- preflight, source generation, and required body/lid mesh verification;
- rejection of a bundle for the wrong project revision;
- refusal to replace an existing bundle and rejection of extra bundle files.

CI runs this driver against the freshly installed wheel and retains its outputs.
Omitting `--require-stl` is a source-only diagnostic, never mesh acceptance.
This is internal engineering acceptance. Physical fit, independent reproduction,
external language evaluation, human usability, and public tagged-release
installation remain separate gates. No frozen scientific case is executed.
