# IMR27: retained-mesh verification research-note package

**Stage: complete research-note and analysis draft prepared for human author review. Unsubmitted. The containing pull request is a draft and has not been merged. This is not whole-project completion or an accepted scientific result.**

The package contains a three-page two-column research note, one-page presentation handout, ten-minute speaker script, actual retained-mesh visualization, a standard-library MSH reader and executed topology diagnostics. It adds analysis of the six existing native meshes; it does not replace or rerun their campaign.

## Executed evidence

- All **16 original artifact hashes** verified unchanged before analysis.
- All **6 retained meshes** independently parsed without importing Gmsh; tetrahedron counts and oriented volume sums reproduced.
- Every interior face and boundary edge has the checked opposite incidences; the serialized surface triangles equal the tetrahedral boundary.
- Each mesh has one volume component and one boundary component. Solid/boundary Euler counts are **1/2 for the box** and **0/0 for the through-hole plate**.
- **9 new analyzer tests**, including explicit rejection counterexamples and disconnected-component reporting. These are separate from the prior 195 scoped native/backend tests, not additional scientific replications.

The checker does not prove embeddedness, vertex-link manifoldness, exact CAD equivalence, nonintersection, solver convergence, structural safety or learned-generation quality. The paper reports native `minSICN` as retained upstream values; only coordinates, connectivity, counts, incidences and oriented volumes are independently recomputed here.

## Reproduce from the repository root

Python's standard library is sufficient for the new analysis. The existing native files are read-only and the output directory must be new.

```bash
python -m unittest discover -s publication/imr2027_mesh_verification -p 'test_*.py' -v
python publication/imr2027_mesh_verification/analyze_retained_meshes.py \
  --bundle research/results/native-mesh-reference-v1 \
  --output /tmp/neurocad-retained-topology-new
cmp /tmp/neurocad-retained-topology-new/summary.json \
  publication/imr2027_mesh_verification/evidence/retained-topology-v1/summary.json
python publication/imr2027_mesh_verification/build_figures_handout.py \
  --bundle research/results/native-mesh-reference-v1
```

Figure/handout rendering uses Matplotlib and ReportLab. From this directory, `python build_paper.py` compiles the note twice with pdfLaTeX and no shell escape. Rendered PDF metadata may vary across installations; raw retained mesh and report digests are the evidence bindings.

## Template provenance and current venue call

The note uses the official **prior IMR SIAM two-column `ltexpprt.sty`**, retrieved from the IMR26 website's template ZIP. **The template linked by the current IMR27 call returned a sign-in page; this package has not verified that current template's bytes.** Reconcile the supplied source with the current template before uploading. `FORMAT_AND_VENUE.md` records both links and the exact style hash. The package does not claim verified current-format compliance.

The current IMR27 research-note route accepts up to four pages excluding references; the prepared note is three pages including references. It is checked by the committee but is **not peer reviewed**. The submission deadline is **23 December 2026, end of day AoE**. Accepted notes receive a 10-minute talk plus 5-minute Q&A and appear on the IMR site. At least one author must register and present in person; each participant can present at most one paper or research note. The event is 22-26 February 2027 in Pittsburgh.

Before submission, human authors must review the content and contributor list, reconcile the current template, approve the AI-use disclosure and SIAM's required author-responsibility statement, check overlap, and confirm registration/attendance. No author identity, contribution, consent, submission ID or accountability attestation is invented. No portal submission or registration has occurred.

## SMI 2027 routing

The official SMI27 call has a soft abstract deadline of 1 March and a full-paper deadline of 8 March 2027 at 23:59 UTC. Regular papers require original unpublished shape research, double-blind review, Computers & Graphics formatting and at most 12 pages including references; simultaneous overlapping submission is prohibited.

This six-case verification note is **not labeled a completed SMI journal paper**. It lacks representative CAD coverage, a distinct methodological novelty claim, matched reference methods and independent scientific validation. A future SMI contribution requires that substantive work, plus an explicit overlap decision if this note is presented elsewhere. The current artifact can support that work without changing the closed parser/VCG studies.

Presentation rendering requires the DejaVu Sans regular/bold fonts. The default path is `/usr/share/fonts/truetype/dejavu`; set `PRESENTATION_FONT_DIR` to the folder containing `DejaVuSans.ttf` and `DejaVuSans-Bold.ttf` on another installation. Both fonts are embedded in the handout.
