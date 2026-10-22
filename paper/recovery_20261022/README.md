# NeuroCAD current-evidence manuscript, 22 October 2026

This new manuscript consolidates retained compiler and Physics v2 evidence,
archival audit findings, prior failures, and later engineering scope. It does
not replace a frozen paper, create external scientific outcomes, or claim
Kaggle execution. The original compiler disposition remains mixed; Physics v2
is supported within its controlled synthetic software contract. One separately
identified internal Linux/Python 3.12 repetition of the archived Physics v2
source reproduces the same 13 endpoint counts across the same 216 cases. It
does not add independent confirmation or increase the unique-case denominator.

The supplied arxiv.sty is copied byte-for-byte from the user's style reference.
It internally declares the package name arxivrefined. LaTeX warns about the
filename/package-name difference; the style itself is unchanged.

## Rebuild

From the repository root:

```sh
python paper/recovery_20261022/generate_evidence.py
cd paper/recovery_20261022
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

The generator reads retained result artifacts only. It invokes no compiler,
model, CAD kernel, or frozen study. It creates two tables, a scientific figure,
and evidence_sources.json with source hashes and the archive audit. It also
checks the hosted repetition's raw outcome predicates and endpoint counts
against the original records. This
directory's included generated tables and figure allow standalone compilation
even when the full repository is unavailable.

Dependencies: Python with NumPy and Matplotlib; pdfLaTeX/BibTeX and packages
listed in main.tex.

## Interpretation

- Compiler 240/240 cases and 1,000/1,000 static checks describe controlled
  grammar conformance. The 1,000 programs were not all executed in a kernel.
- The separate 240/240 kernel result concerns its historical OpenSCAD/STL
  environment, not every later exact backend.
- Physics v2's 216 cases test receipt identity, numeric agreement and freshness.
  They do not measure physical accuracy.
- The compiler manifest lists 1,212 artifacts; 1,211 present files match and
  the original logs/run.log is missing.
- Frozen timing diagnostics use upper medians for even sample counts. The
  manuscript discloses this and reports conventional medians from retained raw
  records without replacing the original statistics.
- No arXiv submission, independent experiment, or physical/user study is
  implied by this package.
