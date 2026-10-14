# Literature and novelty review

## Verdict

The broad ideas of CAD/CAE associativity, digital-thread traceability,
simulation provenance, content/version identity, and reproducible workflows are
not novel. The paper must not claim otherwise. The potentially useful
contribution is a compact open executable contract and controlled ablation that
combines these ideas for bounded analytical CAD screening.

## Closest foundations

1. Hedberg et al., *Testing the Digital Thread in Support of Model-Based
   Manufacturing and Inspection*, ASME JCISE 16(2), 2016,
   <https://doi.org/10.1115/1.4032697>. Establishes lifecycle traceability and
   reuse as central digital-thread goals.
2. Helu, Hedberg, and Feeney, *Reference architecture to integrate heterogeneous
   manufacturing systems for the digital thread*, 2017,
   <https://www.nist.gov/publications/reference-architecture-integrate-heterogeneous-manufacturing-systems-digital-thread>.
   Addresses contextual integration across heterogeneous lifecycle systems.
3. NIST, *Digital Thread for Manufacturing*,
   <https://www.nist.gov/programs-projects/digital-thread-manufacturing>.
   Explicitly identifies GUID correlation, semantic conformance, trustworthy
   product data, and CAD/CAE interoperability as open implementation needs.
4. W3C, *PROV-DM: The PROV Data Model*, Recommendation, 2013,
   <https://www.w3.org/TR/prov-dm/>. Defines entities, activities, agents, and
   derivations for interoperable provenance.
5. Ruscheinski et al., *SIMPROV: Provenance capturing for simulation studies*,
   PLOS ONE, 2025, <https://doi.org/10.1371/journal.pone.0327607>. Demonstrates
   lightweight capture and validation of simulation-study provenance across
   heterogeneous tools.
6. Olaya, Lofstead, and Taufer, *Building Containerized Environments for
   Reproducibility and Traceability of Scientific Workflows*, 2020,
   <https://arxiv.org/abs/2009.08495>. Evaluates provenance capture and its time
   and space overhead.
7. Horsch et al., *Metadata practices for simulation workflows*, Scientific
   Data, 2025, <https://doi.org/10.1038/s41597-025-05126-1>. Frames metadata and
   provenance throughout simulation setup, execution, analysis, and reuse.
8. NIST, *Integrating Finite Element Analysis With Systems Engineering Models*,
   2017, <https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=922742>.
   Motivates traceability and consistency between system artifacts, simulation
   conditions, FEA models, and results.
9. RO-Crate 1.3 specification,
   <https://www.researchobject.org/ro-crate/specification>. Provides a practical
   packaging model for research data, software, workflows, and provenance.

## Novelty boundary

The study does not introduce provenance, hashes, model identifiers, CAD/CAE
associativity, or digital threads. It evaluates a deliberately small
implementation choice: binding analytical result receipts to canonical CAD
primitive identity plus explicit material/load declarations, and failing closed
when exact dependencies disagree or change.

## Reviewer objections retained

- The primary endpoint is partly contractual: a hash comparison is expected to
  detect a changed hash. This is a conformance result, not discovery of a new
  physical phenomenon.
- Synthetic cases authored by the implementer are not independent external
  evidence.
- Primitive-level metrics do not equal full Boolean-part or assembly metrics.
- Commercial CAD/PLM/CAE systems may already provide stronger associativity and
  lifecycle management; they are not directly compared here.
- Low overhead on small JSON primitives cannot be generalized to meshing, FEA,
  CFD, or enterprise product-lifecycle systems.
- Correct provenance cannot make an incorrect analytical model physically valid.
