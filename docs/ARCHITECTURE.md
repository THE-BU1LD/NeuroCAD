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

The enclosure path is `natural_language → project → enclosure → IR → OpenSCAD`.
`project.py` validates immutable revision history and `edit_language.py` proposes
one explicit semantic change. `manufacturing.py` performs profile-based preflight;
`enclosure_verification.py` independently probes the compiled mesh against the
specification. Rounded lid corners, boss relief and insertion-depth reservations
are generated/checked from that specification. Topology and sampled occupancy
are complementary checks and do not establish complete physical assembly fit.

The browser in `workbench.py` talks only to `demo_server.py`. Generation IDs and
request cancellation prevent stale responses from replacing newer drafts.
Unchanged validated downloads survive a failed compilation. The server stores no
projects; `mesh_preview.py` owns one compiler lock and the bounded expiring STL
cache. CLI bundle workflows use staging directories and verify inventory,
canonical regeneration and hashes before handoff.

Distribution tests run both from the checkout and an extracted sdist. Historical
archive checks live in `tests/test_repository_archive.py` and run only from the
checkout because `legacy/` is deliberately absent from distributions. The optional
`scripts/check_blender_import.py` runs inside a separate Blender process and
records actual imports; it is not part of the runtime library or native CAD API.
