# Contributing

NeuroCAD accepts changes to the documented plate, rectangular box/enclosure, and
basic primitive workflow. New domains must not be advertised as supported until
they have strict parsing, semantic validation, exact expected-geometry tests,
compiled OpenSCAD coverage, and a fabrication review plan.

Set up and run the maintained gates:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m compileall -q neurocad_cli.py text_to_cad.py text_to_openscad.py core
python -m pytest -q tests
neurocad doctor
```

If OpenSCAD is installed, also run:

```bash
neurocad validate "a 120 x 80 x 4 mm plate with four 4 mm holes" --compile
neurocad export "a 40 x 30 x 3 mm plate with four 3 mm holes" --format stl -o /tmp/neurocad.stl
```

Every parser change needs success and rejection tests. Never silently substitute
a fabrication-critical dimension. All geometry lengths remain millimetres from
parsing through manifests, SCAD, STL verification, and documentation.
