# Architecture

The canonical execution path is:

`prompt -> prompt_engine -> DesignGraph -> IR adapter -> neurocad-ir-v1 ->
validation -> deterministic OpenSCAD -> optional STL -> mesh/topology verification`.

`neurocad_cli.py` owns command routing. `core/prompt_engine.py` recognizes the
bounded language. `core/ir.py`, `core/ir_parser.py`, and the JSON schema own the
canonical representation. `core/ir_export.py` emits OpenSCAD. `core/artifacts.py`
and `core/topology.py` verify compiled output. Typed enclosure projects use the
model, revision, preflight, verification, and integration modules under `core/`.

Research orchestration is in `core/research_suite.py`; stored-prompt evaluation is
in `core/challenge.py`. See `../audit/REPOSITORY_MAP.md` for full ownership and
evidence flow.
