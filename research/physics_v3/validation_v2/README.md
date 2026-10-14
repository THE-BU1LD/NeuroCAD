# Corrected conformance successor

Version 1 and its 31/32 failure are preserved. This version corrects maximum
beam stress under opposing loads and replays known cases with five extra beam
checks. This is project-authored regression/conformance, not independent or
physical validation.

Run `python3 scripts/validate_physics_v3_v2.py --output /new/output/path`.
For installed execution add `--installed-python /clean/venv/bin/python`; the
resource and exact installed-source guards remain required.

The separate Physics v3 corrected conformance CI builds a fresh wheel, executes
scalar/installed cases and workflows, compiles meshes, and runs regression.
