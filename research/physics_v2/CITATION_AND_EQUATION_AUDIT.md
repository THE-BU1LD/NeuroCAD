# Citation and equation audit

**Status:** `PASS_WITH_DECLARED_SCOPE`  
**Date:** 2026-10-11

## Equation and definition audit

| Item | Audit result | Evidence or check |
|---|---|---|
| Request definition `R=(m,x,c)` | Consistent | `MODEL_SPEC.md` and `core/physics_context.py` use a versioned model, strict numeric inputs, and optional explicit context. |
| Receipt definition `Y=(m_v,x,y,A,B,H_R,H_x)` | Consistent | All named fields are emitted or represented by the strict report schema; no signature or authority claim is made. |
| Canonical hash `H(z)=SHA256(canonical_json(z))` | Consistent | Sorted keys, compact separators, UTF-8, and non-finite rejection are implemented and tested. |
| Geometry tuple `G=(id,part,operation,shape,parameters,translation,rotation)` | Consistent | The implementation excludes display label and project revision and includes every tuple field. |
| Mass `M=rho V 10^-9` | Dimensionally correct | `rho` is kg/m3 and `V` is mm3; `1 mm3 = 10^-9 m3`. Mass is emitted only for additive primitives with explicit density. |
| Numeric agreement tolerance `1e-12` relative | Consistent | Applied only to repeated, unambiguously mapped material/load/geometry quantities; it is a contract tolerance, not measurement uncertainty. |
| Wilson 95% intervals | Recomputed by retained analysis | Values in generated Table 3 match `metrics.json`; they are explicitly descriptive. |
| Exact two-sided McNemar value | Recomputed by retained analysis | For discordance `(48,0)`, the exact value is `2 * (1/2)^48 = 2^-47 = 7.105427357601002e-15`. |
| Complexity | Correct within schema | Canonical serialization/hash is `O(n)` in component JSON length; primitive equations are constant time; component lookup is linear up to the existing 256-component bound. |

No training objective, learned parameter, gradient, or probabilistic inference
is present. Those generic pipeline items are therefore not hidden omissions;
they are inapplicable to this deterministic software contract.

## Citation audit

| Reference | Statement it supports | Scope decision |
|---|---|---|
| Hedberg et al. (2016) | digital-thread lifecycle traceability and authoritative product-data reuse | Supports motivation, not novelty or the study result. |
| Helu, Hedberg, and Feeney (2017) | integration of heterogeneous manufacturing systems | Supports the heterogeneous-system context only. |
| NIST Digital Thread for Manufacturing | semantic conformance, persistent correlation, trustworthy product data, and CAD/CAE interoperability needs | Supports the broad engineering context; does not validate this implementation. |
| W3C PROV-DM | entities, activities, agents, and derivations in a general provenance model | Supports the claim that provenance is established prior art. |
| SIMPROV (2025) | provenance capture for multi-tool simulation studies | Supports the simulation-provenance comparison. |
| Olaya, Lofstead, and Taufer (2020) | reproducibility, traceability, and provenance overhead in scientific workflows | Supports workflow provenance context, not a direct benchmark comparison. |
| Horsch et al. (2025) | metadata practices across simulation workflow stages | Supports simulation metadata context. |
| NIST FEA/systems-engineering report (2017) | traceability between systems-engineering and finite-element artifacts | Supports the traceability motivation, not physical validation. |
| RO-Crate 1.3 | research-object metadata and packaging | Supports artifact-packaging context. |

## Unsupported-claim audit

- No source is used to claim that hashing, provenance, associativity, or the
  digital thread is novel.
- No citation is treated as evidence for the observed 216-case outcomes; those
  numbers come only from the locked raw artifacts.
- No citation or unit test is used as evidence of physical accuracy, safety,
  solver validation, enterprise generalization, or independent reproduction.
- Bibliographic links and identifiers are retained in the paper so submitters
  and reviewers can resolve the primary or official sources.

