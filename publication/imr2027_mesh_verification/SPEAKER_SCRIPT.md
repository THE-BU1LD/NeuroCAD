# IMR27 ten-minute research-note presentation script

Prepared speaking material, not an accepted/delivered presentation. The official research-note format provides a further five minutes for questions. Use the one-page handout and the actual retained mesh image.

**0:00-1:30 - Why inspect the published file?** Explain the original adapter issue: above 200,000 elements it skipped all quality queries, despite permitting up to two million. The repair queries all elements in bounded batches, rejects invalid later batches and weights means by actual element counts. Fault-injection tests cover that boundary; the six native examples are small and do not establish large-mesh performance.

**1:30-3:30 - The reference parts and retained campaign.** Introduce the 20 x 10 x 5 mm box and the 20 x 12 x 4 mm plate with a radius-2 mm through-hole. Their exact volumes are 1000 and 960 - 16*pi cubic millimetres. Three fixed maximum sizes, 4/2/1 mm, produce six retained Gmsh 4.15.2 meshes. The new work first verifies all 16 original artifact hashes and then reads those same files. It does not regenerate a more favorable campaign.

**3:30-5:00 - Independent volume.** Describe the ASCII MSH 4.1 reader, its explicit supported subset and its rejection of inconsistent tags, counts and coordinates. Each tetrahedron's signed determinant gives oriented volume. Summing those values reproduces the retained results without asking Gmsh for mass or quality. Native sampled SICN values are reported separately as retained values, not independently recomputed quality.

**5:00-6:30 - Incidence and topology diagnostics.** Sort face-node triples to identify shared faces while tracking orientation parity. Interior faces must appear twice in opposite directions. Derive the boundary and match it exactly to serialized surface triangles. Check opposite boundary-edge incidences and connected components. Compute V-E+F-T for the volume and V-E+F for the boundary. The box values are 1/2; the through-hole plate values are 0/0.

**6:30-8:00 - Six-case result table.** The box's mesh volume is 1000 at every size. Plate errors range from 0.526629% at 4 mm to 0.154483% at 1 mm; 4 and 2 mm are close. All six have one volume and one boundary component. Minimum retained SICN varies nonmonotonically. Do not infer a convergence rate, improvement over another mesher or solver accuracy from three settings.

**8:00-9:00 - Reuse.** The independent analysis requires only Python's standard library, takes an explicit bundle and writes a new output directory with source and input hashes. The provided figure renders actual serialized boundary triangles. The nine new tests include invalid orientation, duplicate tetrahedra, missing nodes, inconsistent surfaces, shared-face overlap and disconnected valid components.

**9:00-10:00 - Limit.** Euler values and edge incidences do not prove embeddedness, correct vertex links, nonintersection or exact CAD equivalence. Two constructed parts do not establish industrial coverage, safety or learned-generation quality. This is a small inspectable verification note whose inputs and computations can be reused. A regular SMI journal contribution needs a distinct method/question, stronger coverage and independent scientific validation.

## Prepared Q&A

- **Does the checker certify manifoldness?** No. It checks stated incidences, components and Euler counts; it does not check all vertex links or geometric intersections.
- **Why can plate volume be too large?** Straight-sided triangles approximate the circular hole boundary. The observed volume excess is consistent with that approximation; exact attribution or convergence theory is not claimed.
- **Was the mesher run again for the new table?** No. The new table parses the six original files and verifies their existing hashes.
- **Does this change the closed parser/VCG study?** No. No learning campaign, split or protected endpoint changes.
- **Is this a ready SMI paper?** No. It is a bounded IMR research-note draft. The regular SMI novelty, evidence and overlap requirements remain unresolved.
