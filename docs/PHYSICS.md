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

The base request has exactly two top-level fields, `model` and `inputs`; a
Physics v2 request may also include the `context` field documented below.
Supported models are:

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
