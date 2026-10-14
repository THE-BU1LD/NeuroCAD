# Analytical physics models

NeuroCAD provides a small versioned set of closed-form engineering models for
early constraint checks. Every input name carries its unit. Every report states
its assumptions and the boundary that it is not simulation, certification, or
physical validation.

Run a model from a strict JSON request:

```bash
neurocad physics --list -o physics-catalog.json
neurocad physics docs/examples/physics-buckling.json -o buckling-report.json
```

`--list` returns a machine-readable catalog of every model, required input, and
default. This is the authoritative discovery surface for users and agents.

The base request has exactly two top-level fields, `model` and `inputs`.
Physics v2 may add `context`; Physics v3 may add the context-v2 contract and/or
an `uncertainty` object. The catalog currently exposes 18 models:

- `euler_buckling`: ideal elastic column buckling using supplied effective
  length, modulus, and second moment; optional area, applied load, and safety
  factor produce slenderness and an explicit pass/fail constraint.
- `thermal_expansion`: one-dimensional free expansion and optional ideal fully
  restrained elastic stress/reaction.
- `steady_conduction`: one-dimensional steady Fourier conduction through a
  uniform slab.
- `steady_convection`: Newton cooling at a uniform surface using an explicit
  user-supplied heat-transfer coefficient.
- `radiative_exchange`: diffuse gray-surface radiation to large isothermal
  surroundings using explicit emissivity and view factor.
- `lumped_thermal_transient`: transient heating or cooling with a calculated
  Biot number; it refuses the lumped model when `Bi > 0.1`.
- `internal_pipe_flow`: Reynolds number and Darcy-Weisbach major loss. The
  laminar factor is `64/Re`; transitional and turbulent cases require an
  explicit user-supplied Darcy friction factor.
- `thin_wall_cylinder`: ideal closed-end membrane stress, accepted only when
  mean radius divided by thickness is at least 10.
- `circular_shaft_torsion`: elastic stress and twist for a solid or hollow
  circular shaft, with optional yield utilization.
- `spring_mass_damper`: natural frequency, damping ratio/regime, damped
  frequency, and optional static deflection for a linear single-degree-of-
  freedom system.
- `hydrostatic_buoyancy`: static-fluid gauge pressure, buoyant force, and
  optional apparent weight for a declared fully submerged volume.
- `ideal_brayton_cycle`: ideal-gas compressor/heat-addition/turbine cycle with
  explicit pressure ratio, temperatures, heat capacity, heat-capacity ratio,
  and component efficiencies. It reports temperatures, specific work, and
  cycle efficiency only; it intentionally has no mass-flow, thrust, nozzle,
  blade, fuel, cooling, bearing, structural, or control-system model.
- `cantilever_beam`: signed tip and uniform transverse loading of a prismatic
  Euler-Bernoulli cantilever, including root reactions, tip slope/deflection,
  and optional bending-yield utilization.
- `combined_stress`: principal stresses, maximum shear, hydrostatic stress, and
  von Mises utilization for one explicitly supplied 3D stress tensor.
- `thermal_network`: temperatures, edge heat flows, boundary heat, and energy-
  balance residual for a steady linear conductance network.
- `forced_vibration`: steady force- or base-excited response of a linear
  viscously damped SDOF oscillator, with an explicit resonance warning band.
- `pipe_network`: Darcy-Weisbach losses for series segments and one parallel
  branch bank. Series segments use `64/Re` or Swamee-Jain when applicable;
  transitional cases fail closed, and parallel balancing requires explicit
  branch friction factors.
- `electro_thermal_wire`: a self-consistent lumped electrical/thermal
  equilibrium with optional free expansion and fully restrained elastic stress.

These models intentionally fail outside their declared input and applicability
contracts. They do not infer material properties, boundary conditions,
correlations, friction factors, or safety factors. They omit geometry-specific
stress concentrations, defects, fatigue, creep, nonlinear material behavior,
multidimensional heat flow, turbulence closure, multiphase flow, and coupled
physics. Use an appropriate verified solver and qualified review for those
problems.

## Physics v2 bindings

A request may add a strict `context` object that binds the calculation to an
exact component in a NeuroCAD agent project, a versioned material card, and a
named load case. The resulting report uses `neurocad-physics-v2` and records
the exact inputs plus canonical SHA-256 hashes for the request, geometry, and
every declared context object.

```json
{
  "model": "circular_shaft_torsion",
  "inputs": {
    "torque_n_m": 120,
    "length_mm": 100,
    "outer_diameter_mm": 20,
    "shear_modulus_mpa": 79000,
    "yield_strength_mpa": 250,
    "safety_factor": 2
  },
  "context": {
    "schema_version": "neurocad-physics-context-v1",
    "geometry": {
      "agent_project": "agent-shaft-project.json",
      "component_id": "shaft"
    },
    "material": {
      "schema_version": "neurocad-material-card-v1",
      "material_id": "documented-steel-example",
      "revision": 1,
      "source": "Replace with the exact datasheet, standard, or measured dataset used for the design.",
      "properties": {
        "density_kg_m3": 7850,
        "shear_modulus_mpa": 79000,
        "yield_strength_mpa": 250
      }
    },
    "load_case": {
      "schema_version": "neurocad-load-case-v1",
      "case_id": "rated-torque",
      "coordinate_system": "component-local",
      "source": "Declared design load; replace with a test, requirement, or measured source.",
      "values": {"torque_n_m": 120, "safety_factor": 2}
    }
  }
}
```

Material properties and load values remain explicit model inputs. If a card or
load case repeats an input, NeuroCAD requires the values to agree; it never
silently substitutes one for another. Primitive volume, surface area, centroid,
axis-aligned world bounds, and supported section properties are added to the
binding. Material mass is calculated only for an additive primitive with an
explicit `density_kg_m3` property.

Where the mapping is exact, model inputs are also checked against the bound
primitive: shaft diameter and length for `circular_shaft_torsion`, displaced
volume for `hydrostatic_buoyancy`, and volume and surface area for
`lumped_thermal_transient`. Ambiguous quantities such as an effective buckling
length, a convection face area, or a pipe's internal diameter are not guessed.

The geometry metrics describe the selected primitive before Boolean operations.
They do not claim the volume, mass, surface area, or center of mass of a complete
CSG part or assembly. Subtractive components are marked as isolated voids.

Recheck a saved result before reuse:

```bash
neurocad physics docs/examples/physics-bound-shaft.json -o shaft-report.json
neurocad physics --verify shaft-report.json
```

Verification exits successfully only while the component's geometry hash still
matches. A changed or missing component produces a machine-readable `stale` or
`unavailable` result and a nonzero exit status.

Additional runnable examples live in `docs/examples/physics-convection.json`,
`physics-radiation.json`, `physics-lumped-cooling.json`,
`physics-vibration.json`, `physics-shaft-torsion.json`,
`physics-bound-shaft.json`, and `physics-buoyancy.json`.

## Physics v3 workflow expansion

Physics v3 is a versioned engineering successor to the frozen Physics v2
provenance study. It adds the six analytical/network models above plus three
workflow layers. It does not revise the v2 protected result or claim that these
models have been physically validated.

### Temperature-aware materials and load combinations

`neurocad-physics-context-v2` accepts the same exact geometry binding as v1. A
`neurocad-material-card-v2` may combine constant `properties` with piecewise-
linear `temperature_tables`. The request must supply an
`evaluation_temperature_k`; interpolation is allowed only inside every table,
and extrapolation is rejected. Resolved values remain explicit model inputs and
must agree to numerical precision.

Multiple `neurocad-load-case-v1` objects can be combined by a
`neurocad-load-combination-v1`. Coefficients are algebraic, every referenced
case must exist, and all cases must declare the same coordinate system. The
resolved combined values must agree with any same-named model input. Source
cards, cases, the combination, resolved values, and the overall binding each
receive canonical SHA-256 receipts.

The exact geometry mapping is intentionally small. Existing v1 mappings remain
unchanged. `electro_thermal_wire` additionally accepts only an additive
cylinder and checks its length and cross-sectional area. NeuroCAD does not
guess beam axes, effective lengths, pipe bores, load directions, contact areas,
or assembly boundary conditions.

See `docs/examples/physics-v3-electrothermal-bound.json` for a complete bound
request with material interpolation, two load cases, a load combination, and
an uncertainty envelope.

### Generic uncertainty propagation

Add `uncertainty` to any model request. Only top-level numeric scalar inputs can
vary, every bound must be finite, and the base value must lie inside its range.

```json
{
  "method": "interval",
  "inputs": {
    "tip_force_n": {"lower": 900, "upper": 1100}
  },
  "outputs": ["tip_deflection_mm"]
}
```

The methods are:

- `interval`: evaluates all box corners for at most 12 variables. The result is
  labeled a corner envelope, not a rigorous global bound for a non-monotone
  interior.
- `monte_carlo`: runs 2 to 10,000 independent uniform samples with an explicit
  deterministic seed and reports empirical summary statistics and observed
  constraint-failure fraction.
- `local_sensitivity`: reports central finite-difference derivatives at the
  base point using an explicit or default step fraction. It requires each base
  value to lie strictly inside its declared bounds.

This layer never turns ranges into an unstated probability distribution and
never presents finite sampling as a certified tail or reliability result.

### Component result overlays

When a request has an exact geometry binding, the report includes a
`neurocad-component-overlay-v1` object. It identifies the component and geometry
hash, carries up to 32 scalar metrics with units, and reports `pass`, `fail`, or
`not_evaluated` from the model's explicit constraint. `spatial_field` is always
`false`: the overlay is a uniform component annotation, never a fabricated
stress contour, temperature map, displacement field, or CFD visualization.

### Explicit external-solver boundary

Physics v3 still contains no FEA or CFD engine and does not relabel analytical
formulas as one. A future adapter must be a separate evidence-gated stage with
an identified solver/version, mesh and convergence receipts, boundary-condition
manifest, material law, result-file hashes, and independent validation. Until
those artifacts exist, full-field structural, thermal, and fluid results remain
`NOT_IMPLEMENTED`, not inferred from these reports.

Runnable v3 examples:

```bash
neurocad physics docs/examples/physics-cantilever.json
neurocad physics docs/examples/physics-combined-stress.json
neurocad physics docs/examples/physics-thermal-network.json
neurocad physics docs/examples/physics-forced-vibration.json
neurocad physics docs/examples/physics-pipe-network.json
neurocad physics docs/examples/physics-v3-electrothermal-bound.json
```

The built-in agent can generate a non-operational educational jet-engine
cutaway. Its plan points to the applicable Brayton, transient thermal,
radiation, shaft-torsion, and vibration models, but does not silently attach
performance numbers or couple those calculations to the geometry. Run each
diagnostic separately with explicit inputs:

```bash
neurocad agent run "generate a physics-aware jet engine cutaway" --project jet-engine-concept
neurocad physics docs/examples/physics-brayton-cycle.json -o brayton-report.json
```

The cutaway omits aerodynamic blades, fuel and combustion hardware, bearings,
seals, cooling, shaft-speed design, materials, tolerances, and containment. It
must not be used as a propulsion or fabrication design.
