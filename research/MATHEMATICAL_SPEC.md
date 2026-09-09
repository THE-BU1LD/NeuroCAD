# Mathematical specification

## Compiler contract

Let `L` be the finite declared prompt language and `P` the set of canonical
`neurocad-ir-v1` programs. The frontend is a partial deterministic function

\[
C:L^* \rightharpoonup P, \qquad C(x)=p \;\text{or}\; C(x)=\bot_e,
\]

where `e` is an explicit error. Unsupported or ambiguous input must map to an
error, never a guessed design.

A program is a rooted DAG `p=(N,R,K,U,M)` with nodes `N`, roots `R`, constraints
`K`, unit `U=mm`, and metadata `M`. A primitive node has parameters `theta_i` and
an affine transform

\[
T_i(q)=t_i + R_z(\gamma_i)R_y(\beta_i)R_x(\alpha_i)
\operatorname{diag}(s_i)q,
\]

with finite translation/rotation and strictly positive finite scale. Composite
nodes implement set union, difference, or intersection over child solids.

## Semantics and validation

The denotation `[[p]]` is the CSG solid obtained recursively from primitive sets
and Boolean operators after transforms. Static validity is the conjunction

\[
V(p)=V_{schema}\land V_{types}\land V_{refs}\land V_{acyclic}\land
V_{bounds}\land V_{parameters}\land V_{constraints}.
\]

Dimension constraints check declared scalar or axis-aligned bounds against a
tolerance; coincident/offset constraints compare node-derived positions;
child-count constraints check arity. They validate declarations but do not infer
intent or solve for unknowns.

Serialization `S:P->JSON` and parsing `D:JSON->P` are required to satisfy
`D(S(p))=p`. Export `E:P->OpenSCAD` is deterministic. Kernel execution and mesh
verification are separate:

\[
m=K_{scad}(E(p)),\quad Q(m)=I[finite\land volume>0\land watertight\land
winding\land connected\land extents\_match].
\]

`Q=1` is bounded mesh evidence, not exact BREP equivalence or manufacturability.

## Objective and inference

There is no learned objective, latent variable, optimizer, regularizer, gradient,
checkpoint, or model-selection stage. For task signature `y`, semantic exactness is

\[
A(p,y)=\prod_{j\in F(y)} I[d_j(\sigma_j(p),y_j)\le 10^{-6}],
\]

with exact equality for categorical/count fields. Compiler inference is one
deterministic parse/validate/lower pass.

## Complexity and stability

For prompt length `n`, node count `|N|`, and edge count `|E|`, bounded parsing is
approximately `O(n)` and graph validation/export is `O(|N|+|E|)`, apart from
external kernel cost. The implementation caps input size, nodes at 1,024, and
hierarchy depth at 128. Finite-number and positive-domain checks prevent NaN/Inf
and degenerate primitive parameters from reaching export. CSG numerical stability
ultimately depends on OpenSCAD and is empirically checked only on executed cases.

## Simplest competing explanations

Perfect controlled accuracy can be explained by rules matching their own generated
grammar. Retrieval, raw-number, and fixed controls reject trivial memorization and
number copying, but they do not establish natural-language generalization. The
strongest remaining control is a frozen, independently authored prompt set scored
blindly against reviewed geometry signatures and kernel artifacts.

The normalized-dimensions control computes the same primitive dimensions after
explicit unit conversion but sets all feature counts to zero and has no enclosure
wall semantics. Comparing it with the raw-number control isolates unit conversion;
comparing it with the compiler measures the combined residual contribution of
structured feature/domain rules, not any single parser component.
