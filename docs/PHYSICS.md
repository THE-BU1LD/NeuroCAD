# Analytical physics models

NeuroCAD provides a small versioned set of closed-form engineering models for
early constraint checks. Every input name carries its unit. Every report states
its assumptions and the boundary that it is not simulation, certification, or
physical validation.

Run a model from a strict JSON request:

```bash
neurocad physics docs/examples/physics-buckling.json -o buckling-report.json
```

The request has exactly two top-level fields: `model` and `inputs`. Supported
models are:

- `euler_buckling`: ideal elastic column buckling using supplied effective
  length, modulus, and second moment; optional area, applied load, and safety
  factor produce slenderness and an explicit pass/fail constraint.
- `thermal_expansion`: one-dimensional free expansion and optional ideal fully
  restrained elastic stress/reaction.
- `steady_conduction`: one-dimensional steady Fourier conduction through a
  uniform slab.
- `internal_pipe_flow`: Reynolds number and Darcy-Weisbach major loss. The
  laminar factor is `64/Re`; transitional and turbulent cases require an
  explicit user-supplied Darcy friction factor.
- `thin_wall_cylinder`: ideal closed-end membrane stress, accepted only when
  mean radius divided by thickness is at least 10.

These models intentionally fail outside their declared input and applicability
contracts. They do not infer material properties, boundary conditions,
correlations, friction factors, or safety factors. They omit geometry-specific
stress concentrations, defects, fatigue, creep, nonlinear material behavior,
multidimensional heat flow, turbulence closure, multiphase flow, and coupled
physics. Use an appropriate verified solver and qualified review for those
problems.
