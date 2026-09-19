# Scientific kernel

`core.scientific_kernel` supplies small, audited mathematical building blocks
for typed agent tools. These methods are useful for model setup, diagnostics,
and bounded concept optimization. They are not substitutes for established
geometry, meshing, finite-element, or CFD engines.

## Dimensional quantities

`quantity(value, unit)` stores SI values with seven base dimensions. Addition,
subtraction, and conversion require matching dimensions; multiplication,
division, and integer powers derive dimensions. Registered units include common
SI length, time, mass, force, pressure, energy, power, and volume units. Compound
expressions such as `kg/m^3` and `N/mm^2` are parsed without evaluating code.

```python
from core import quantity

stress = quantity(1, "N") / quantity(1, "mm^2")
assert stress.to("MPa") == 1
```

Offset-temperature conversions and fractional dimensions are intentionally not
implemented. Absolute temperature uses kelvin.

## Derivatives and nonlinear constraints

`value_gradient_hessian` performs second-order forward automatic
differentiation using `Jet` values. It returns a scalar value, gradient, and
Hessian. Supported elementary functions are sine, cosine, exponential,
logarithm, and square root.

`solve_nonlinear_constraints` handles bounded equality and inequality residuals
with damped least squares, finite-difference Jacobians, projected bounds,
conditioning diagnostics, and named conflict reports. It reports convergence
only when the declared residual tolerance is met. The algorithm is local: a
failure may be caused by a poor starting point or scaling, and convergence is
not a global-feasibility proof.

`minimize_constrained` performs bounded projected local optimization and reports
the objective, feasibility, convergence state, projected-gradient norm,
iterations, and named constraint conflicts. It is suitable for small concept
parameters, not global topology optimization or certification.

## Numerical reliability and uncertainty

`Interval` uses outward-rounded endpoints for elementary arithmetic and rejects
division by an interval containing zero. It does not yet implement transcendental
interval functions or a full IEEE 1788 decoration model.

`monte_carlo_propagate` validates a covariance matrix, uses an explicit seed,
propagates correlated normal samples through a scalar model, and reports summary
statistics and quantiles. Results are numerical uncertainty propagation, not
empirical validation or a reliability certificate. Polynomial chaos,
distribution fitting, FORM/SORM reliability indices, and probabilistic CAD
tolerancing are not implemented yet.

`linear_system_diagnostics` reports rank, residual norm, condition number, and
relative backward error for a proposed dense linear-system solution. Sparse
factorization, preconditioners, arbitrary precision, PDE discretization error,
and convergence studies belong in future typed external-engine adapters.

## Engine boundary

Robust BREP Booleans, NURBS, adaptive predicates, production meshing, mechanics,
heat transfer, CFD, electromagnetics, acoustics, optics, and coupled multiphysics
need mature third-party engines and domain-specific verification. NeuroCAD should
generate versioned inputs for those engines, execute them under bounded resource
policies, retain logs and hashes, inspect convergence, and explain results. This
release provides the foundations and existing bounded analytical calculators;
it does not claim those external solvers are integrated.
