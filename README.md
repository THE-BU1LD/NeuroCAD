# NeuroCAD

NeuroCAD is a public-alpha natural-language CAD toolkit that turns bounded engineering prompts into structured designs and OpenSCAD geometry.

## One-command install

Once this repository is public, install NeuroCAD with:

```bash
curl -fsSL https://raw.githubusercontent.com/THE-BU1LD/NeuroCAD/main/install.sh | sh
```

The installer creates an isolated environment under `~/.local/share/neurocad`, exposes the `neurocad` command through `~/.local/bin`, and runs a post-install doctor check.

If `~/.local/bin` is not already on your PATH, add:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Verify the installation

```bash
neurocad --version
neurocad doctor
```

## Create geometry

```bash
neurocad create "a compact box with two holes" -o design.scad
```

Validate a prompt without writing an output file:

```bash
neurocad validate "a plate with four holes"
```

Explicitly export OpenSCAD:

```bash
neurocad export "a compact enclosure with holes" --format scad -o enclosure.scad
```

The legacy command remains available:

```bash
text-to-cad "a compact box with two holes" -o out.scad
```

## Python installation

For development:

```bash
git clone https://github.com/THE-BU1LD/NeuroCAD.git
cd NeuroCAD
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
neurocad doctor
```

## Software status vs scientific status

NeuroCAD deliberately separates release-engineering evidence from research evidence.

**Software / release evidence:** the maintained public-alpha path has CI, packaging, clean-install, CLI, generation-smoke, and secret-history gates. The exact public release is still gated on anonymous clean-environment verification and exact tagged-artifact provenance. See [`docs/PUBLIC_ALPHA_EVIDENCE_LEDGER.md`](docs/PUBLIC_ALPHA_EVIDENCE_LEDGER.md).

**Scientific evidence:** passing CI, generating compilable OpenSCAD, or completing a scripted smoke test does **not** validate a NeuroCAD research hypothesis. The historical typed-parser causal interpretation is retained as **falsified / validation-dominant** rather than promoted by later release work. The current VeriCodeGen successor comparison remains **untested** at the scientific level: Stage-1 scripted/offline checks are engineering evidence only, and outcome-bearing Stage-2 execution remains blocked until the held-out benchmark, provider/model identity, prompts, verifier/analysis hashes, budgets, and authorization record are frozen and reviewed. See the maintained research gates in [issue #21](https://github.com/THE-BU1LD/NeuroCAD/issues/21) and [issue #22](https://github.com/THE-BU1LD/NeuroCAD/issues/22).

Current claim boundary:

- **Implemented:** bounded text-to-OpenSCAD generation, validation, CLI/package/release plumbing, and fail-closed evaluation infrastructure.
- **Engineering-verified:** selected install/build/CLI/smoke paths represented by repository CI and the release evidence ledger.
- **Falsified:** the historical claim that the typed-parser mechanism itself caused the reported NeuroCAD advantage.
- **Not yet scientifically established:** VeriCodeGen successor superiority, broad semantic CAD correctness, manufacturability, external validation/adoption, or independent reproduction.

Negative, mixed, inconclusive, or falsified findings are treated as valid outcomes and must not be rewritten as positive evidence.

## Release gates

Every push to `main` is configured to run clean-install and package gates across Python 3.10, 3.11, and 3.12. CI compiles the source, runs tests when present, exercises the CLI, builds a wheel/source distribution, installs the wheel into a fresh environment, performs a second generation smoke test, and scans Git history for high-confidence secret patterns.

## Public-alpha scope

NeuroCAD currently focuses on a bounded, demonstrable text-to-parametric-geometry workflow. The current CLI exports OpenSCAD. It should not be described as a general replacement for full commercial CAD systems.

Not yet promised by this alpha:

- general arbitrary sketch constraint solving;
- STEP/BREP export;
- full structural, thermal, fluid, or electromagnetic simulation;
- fabrication-calibrated nanotechnology simulation;
- arbitrary natural-language CAD with no supported-domain boundary.

## License

MIT. See `LICENSE`.
