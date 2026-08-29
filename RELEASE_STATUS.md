# NeuroCAD Release Status

Target: `v0.4.0a1` public alpha.

## Implemented release surface

- Python package metadata under `neurocad-research`.
- `neurocad` CLI.
- `neurocad --version`.
- `neurocad doctor`.
- `neurocad create` for prompt-to-OpenSCAD generation.
- `neurocad validate` for prompt/design smoke validation.
- `neurocad export --format scad`.
- Legacy `text-to-cad` command retained.
- One-command bootstrap installer in `install.sh`.
- CI across Python 3.10, 3.11, and 3.12.
- Fresh-wheel-install smoke gate.
- Git-history high-confidence secret-pattern gate.
- Tagged-release workflow producing wheel/source artifacts.

## Required before announcing the public alpha

1. The repository must be public so the anonymous raw `curl` URL and GitHub source archive are reachable.
2. The exact public commit must pass the `NeuroCAD CI` workflow.
3. Run the documented curl command from a clean shell and confirm `neurocad doctor` succeeds.
4. Tag the passing commit `v0.4.0a1`; the release workflow will build and attach distributions.

## Explicit non-goals for this alpha

- STEP/BREP export.
- General arbitrary sketch constraint solving.
- Full structural/thermal/fluid/electromagnetic simulation.
- Fabrication-calibrated nanotechnology simulation.
- Unbounded natural-language CAD generation.

The project should be presented as a bounded public alpha, not as a complete replacement for production CAD systems.
