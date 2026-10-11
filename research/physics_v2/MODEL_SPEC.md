# Model specification: contract-carrying analytical-physics receipt

## 1. Inputs and outputs

An analytical request is

\[
R=(m, x, c),
\]

where `m` is a versioned analytical model identifier, `x` is a strict mapping
of numeric model inputs whose names encode units, and optional context `c`
contains one or more geometry, material, and load-case bindings.

The evaluator returns either an explicit error or a result receipt

\[
Y=(m_v, x, y, A, B, H_R, H_x),
\]

where `m_v` is the executed model version, `y` contains analytical outputs,
`A` contains disclosed assumptions, `B` is the claim boundary, and `H_R` and
`H_x` are canonical SHA-256 hashes of the request and input mapping.

## 2. Canonical serialization

For a JSON value `z`, canonical serialization is UTF-8 JSON with lexicographic
object-key order, compact separators, and no NaN or infinity. The receipt hash is

\[
H(z)=\operatorname{SHA256}(\operatorname{canonical\_json}(z)).
\]

This is content identity, not a cryptographic signature or authority proof.

## 3. Geometry binding

An agent component is reduced to the geometry-relevant tuple

\[
G=(id, part, operation, shape, parameters, translation, rotation).
\]

Display labels and project revision counters are excluded. The geometry receipt
stores `H(G)`, project/component identity, revision observed at evaluation, and
primitive-level derived metrics. Re-verification reloads the named component and
returns `current` iff the observed `H(G)` equals the stored value, `stale` if it
differs, and `unavailable` if the dependency cannot be resolved.

## 4. Primitive metrics

The implementation supports the primitives already admitted by the NeuroCAD
agent plan: box, planar-rounded extruded box, sphere, cylinder, cone/frustum,
and ring torus. It computes closed-form isolated-primitive volume, surface area,
centroid, and transformed axis-aligned bounds. Centroidal section properties
are reported only where the reference section is unambiguous. Material mass is

\[
M=\rho V 10^{-9}
\]

for an additive primitive with `density_kg_m3`, because `V` is in mm3.
Subtractive primitives are reported as isolated voids and receive no mass.

These are not Boolean-evaluated part or assembly properties.

## 5. Material card

A material card is

\[
C_M=(version, material\_id, revision, source, temperature, properties).
\]

The source is mandatory. Properties are explicit finite numeric values. The
system does not select materials, interpolate temperature curves, or fill absent
values. If a material property name equals a model input name, their numeric
values must agree within relative tolerance `1e-12`; otherwise evaluation fails.

## 6. Load case

A load case is

\[
C_L=(version, case\_id, coordinate\_system, source, values).
\]

Load values remain explicit model inputs. Repeated names must agree within
relative tolerance `1e-12`; the binding does not infer direction, combination,
or safety factor.

## 7. Exact geometry/model checks

Only unambiguous mappings are checked:

| Model | Required primitive | Exact checks |
|---|---|---|
| circular shaft torsion | additive cylinder | outer diameter = 2 radius; length = cylinder height |
| hydrostatic buoyancy | additive supported primitive | displaced volume = isolated primitive volume |
| lumped thermal transient | additive supported primitive | volume and total isolated surface area |

Effective buckling length, convection face area, internal pipe diameter, and
other ambiguous quantities are never guessed.

## 8. Three experimental arms

1. **Full binding:** canonical hashes plus semantic geometry/material/load
   agreement checks and post-result freshness verification.
2. **Hash-only ablation:** component content identity and post-result hash
   verification, but no semantic agreement checks.
3. **Unbound control:** the same analytical inputs and model without any
   machine-verifiable CAD, material, or load dependency.

## 9. Failure behavior

Malformed schemas, unknown fields, non-finite values, invalid identifiers,
missing components, unsupported project versions, stale expected hashes, and
semantic contradictions fail explicitly. No value is invented, coerced from
text, or silently substituted.

## 10. Complexity

For a component JSON representation of length `n`, canonical hashing is `O(n)`
time and `O(n)` serialization space. Primitive metrics and semantic checks are
constant time for the bounded primitive schema. Project lookup is linear in the
number of agent components, bounded by the existing maximum of 256.
