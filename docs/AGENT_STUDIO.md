# Conversational agent studio

NeuroCAD now has a persistent concept-design loop above its deterministic CAD
IR. The planner may be probabilistic and model-driven. Every accepted plan is
strictly decoded, converted to the bounded canonical IR, validated, and written
as hash-addressed progressive checkpoints.

## Start a project

```bash
neurocad studio ~/NeuroCADProjects/bottle --view
```

Inside the studio, ordinary underspecified requests such as `make a cylinder`
and `make a water bottle` immediately create editable concept drafts with visible
assumptions. Continue the same project with requests such as:

```text
make it 750 mL, add a carrying loop, and widen the base
```

Use `:view` for the live loopback browser workbench, `:assumptions` for inferred
choices, `:history` for revisions, and `:project` for the artifact directory.
`Ctrl-C` interrupts the active operation without deleting completed checkpoints.

The non-interactive equivalent is:

```bash
neurocad agent run "make a water bottle" --project ~/NeuroCADProjects/bottle
neurocad agent run "make it 750 mL and add a carrying loop" --project ~/NeuroCADProjects/bottle
neurocad agent inspect ~/NeuroCADProjects/bottle
neurocad agent view ~/NeuroCADProjects/bottle
```

Each revision writes `project.json`, `events.jsonl`, `design.ncad.json`,
`design.scad`, `preview.svg`, and per-component snapshots with SHA-256 hashes.
The live viewer polls project state and replaces the preview as each component is
published. It only binds to loopback and sends a restrictive browser security
policy. Its interactive 3D scene uses the locally packaged Three.js 0.180.0
runtime under the included MIT license, so the viewer has no runtime CDN
dependency. Additive geometry is solid; subtractive concepts are shown as
wireframes until the deterministic Boolean export is compiled.

## Planning providers

The built-in offline planner covers primitive concepts, capacity-driven water
bottles, and a decorative Mark III-inspired cosplay/display shell. It exists as
a credential-free baseline, not as general intelligence.

Use a local OpenAI-compatible Ollama endpoint:

```bash
export NEUROCAD_OLLAMA_MODEL=qwen3-coder
neurocad studio ~/NeuroCADProjects/new-design --provider ollama --view
```

Use another OpenAI-compatible chat endpoint:

```bash
export NEUROCAD_LLM_ENDPOINT=http://127.0.0.1:8000/v1/chat/completions
export NEUROCAD_LLM_MODEL=my-cad-planner
export NEUROCAD_LLM_API_KEY=optional-token
neurocad studio ~/NeuroCADProjects/new-design --provider compatible --view
```

For the hosted OpenAI-compatible option, set `OPENAI_API_KEY` and optionally
`NEUROCAD_LLM_MODEL`, then select `--provider openai`. Secrets are read from the
environment and are not stored in the project.

Provider output is not executed as code. It must match the agent-plan schema,
use supported bounded primitives, start each part with additive geometry, and
pass canonical IR validation. Weapon requests are rejected before a provider is
called.

## Current boundary

The agent produces a **concept draft**, not a fabrication approval. Current
progressive plans use boxes, rounded boxes, spheres, cylinders, cones, tori, and
Boolean composition. Open-ended quality depends on the configured model. There
is not yet native BREP/NURBS generation, part-aware STEP export, automatic mesh
repair, an external solver orchestrator, body-scan fitting, or verified
manufacturing planning.

The intended next layer is a typed tool protocol for OpenCASCADE/CadQuery, Gmsh,
CalculiX, FEniCS, OpenFOAM, Blender, and FreeCAD. Each adapter must declare units,
boundary conditions, solver version, convergence criteria, resource limits,
artifact hashes, and claim boundaries. A model may propose the run; only the
adapter and independent result checks may accept it.
