# Research Audit Checklist — MLInvention

Source path: `/Volumes/PRO-BLADE/GitHub-Every-Repo/MLInvention`

Audit date: 2026-09-13

Repository type: **git repo**

Executive verdict: **partial**. Good foundry engineering, but promoted deeper results are negative/inconclusive.

Prior portfolio audit used: **yes**

## Fresh Scan Summary

- Files scanned, excluding common vendored/build/cache folders: **1200**
- Top extensions: .md:747, .py:136, .csv:133, .json:85, <none>:49, .pyi:19, .so:9, .txt:7
- Marker counts: todo=22, placeholder=7, stub=21, hardcoded=1, claim-language=268
- README excerpt: # MLInvention  MLInvention is an evidence-gated research foundry for 64 machine-learning mechanism proposals. It is designed to make weak ideas fail cheaply, preserve negative results, and promote only mechanisms that survive matched baselines, removal ablations, distribution shifts, and deterministic reruns.  This repository is publication-ready as a transparent research artifact. It does **not** claim that all 64 names are novel inventions or validated contributions. The canonical registry distinguishes specification, implementation, smoke testing, baselining, ablation, robustness, reproduction, falsification, and paper status.  ## What is here  - 64 validated project records in [`data/registry/projects.json`](data/registry/projects.json), with one human-readable card per proposal in [`projects/`](projects/). - A primary-source literature catalog and bounded family-level novelty triage...

## Component Classification

| Classification | Evidence |
| --- | --- |
| partial | Good foundry engineering, but promoted deeper results are negative/inconclusive. |
| complete/real | Only applicable where retained code, tests, configs, and results match the claimed contribution; this scan requires manual promotion from the current classification. |
| partial | Real implementation or evidence appears present, but at least one conference-grade requirement remains incomplete. |
| pseudocode | Flag if marker examples below contain algorithm prose without executable implementation. |
| scaffold | Flag if repository is a landing page, generated foundry lane, template, duplicate tree, or explicitly scaffolded research. |
| placeholder/stub/mock | placeholder=7, stub=21 |
| hardcoded shortcut | hardcoded/toy markers=1 |
| unused/dead | Flag if prior audit classifies as duplicate, legacy, archive, or output-only. |
| untested | Flag if code exists without detected test paths. |
| broken | Flag if prior audit or fresh evidence shows NaNs, failing gates, missing core path, or execution mismatch. |
| missing | Applied to absent README, tests, retained results, dependency manifests, datasets, baselines, or paper-result linkage. |


## Critical Findings

| Severity | File/component | Problem | Evidence | Scientific impact | Exact fix |
| --- | --- | --- | --- | --- | --- |
| P1 | MLInvention | Unresolved placeholder/stub markers require manual triage. | `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/numpy/__init__.py:118` - your python interpreter from there."""; `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/numpy/_distributor_init.py:9` - can safely replace this file with your own version.; `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/numpy/matlib.py:9` - "Please adjust your code to use regular ndarray. ",; `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/charset_normalizer/md.py:284` - Compute the chaos ratio based on what your feed() has seen.; `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/charset_normalizer/legacy.py:25` - This function is deprecated and should be used to migrate your project easily, consult the documentation for | Reviewers cannot tell intentional baselines from unfinished science. | Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work. |


## Marker Evidence

### todo
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/numpy/conftest.py:119` - # FIXME when yield tests are gone.
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/PIL/MpoImagePlugin.py:129` - self._fp = self.fp  # FIXME: hack
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/PIL/PcxImagePlugin.py:96` - # FIXME: hey, this doesn't work with the incremental loader !!!
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/PIL/ImageFile.py:363` - # FIXME: This is a hack to handle TIFF's JpegTables tag.
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/PIL/SpiderImagePlugin.py:162` - self._fp = self.fp  # FIXME: hack
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/PIL/PixarImagePlugin.py:61` - # FIXME: to be continued...
### placeholder
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/numpy/__init__.py:118` - your python interpreter from there."""
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/numpy/_distributor_init.py:9` - can safely replace this file with your own version.
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/numpy/matlib.py:9` - "Please adjust your code to use regular ndarray. ",
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/charset_normalizer/md.py:284` - Compute the chaos ratio based on what your feed() has seen.
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/charset_normalizer/legacy.py:25` - This function is deprecated and should be used to migrate your project easily, consult the documentation for
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/charset_normalizer/api.py:71` - You may want to focus your attention to some code page or/and not others, use cp_isolation and cp_exclusion for that
### stub
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/numpy/_distributor_init.py:15` - pass
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/numpy/exceptions.py:246` - pass
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/charset_normalizer/md.py:273` - raise NotImplementedError  # Defensive:
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/PIL/GribStubImagePlugin.py:5` - # GRIB stub adapter
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/PIL/ContainerIO.py:142` - raise NotImplementedError()
- `tmp-foundry-release-smoke.ba6eDq/py311/lib/python3.11/site-packages/PIL/PdfParser.py:339` - raise NotImplementedError(msg)
### hardcoded
- `DEFINITION_OF_DONE.md:25` - | Robustness | covariate, noise, and low-sample shifts | PASS, synthetic only |
### claim
- `PROJECT_STATUS.md:124` - python3 -m pip install -e '.[research,test,publication]'
- `pyproject.toml:18` - publication = ["reportlab>=4.0", "pdfplumber>=0.11", "pypdf>=6.0", "Pillow>=10.0"]
- `README.md:26` - python -m pip install -e '.[research,test,publication]'
- `RESEARCH_COMPLETION_REPORT.md:89` - ## Strongest publication candidate
- `PROJECT_TRUTH.md:11` - - Working state: material uncommitted research and publication changes are present and preserved.
- `research/projects/mlinvent-032/NOVELTY_AUDIT.md:15` - ## Potentially novel


## Missing Research

- Literature/prior work: verify closest related methods against current literature before claiming novelty.
- Mathematics/theory: independently check objectives, assumptions, gradients, dimensions, stability, and statistical tests for the specific method.
- Data: require licenses, raw-data hashes, preprocessing code, split manifests, leakage checks, and held-out-test discipline.
- Experiments: require competitive baselines, ablations, sensitivity studies, multiple seeds where stochastic, confidence intervals, and failure cases.
- Evaluation: verify metrics programmatically and ensure aggregation supports the stated hypothesis.
- Paper linkage: every abstract/result/table/figure claim must point to a generated artifact, seed/config, and code path.
- Reproducibility: require raw data to preprocessing to training/inference to evaluation to paper artifacts as a single scripted path.


## P0 Checklist
_No items assigned at this severity by this pass._
## P1 Checklist
- **WHAT:** Unresolved placeholder/stub markers require manual triage.
  **WHY:** Reviewers cannot tell intentional baselines from unfinished science.
  **HOW:** Replace, remove, or label each marker as deliberate interface, fixture, or unfinished work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/MLInvention` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P2 Checklist
- **WHAT:** Strengthen scientific comparison set.
  **WHY:** Weak baselines can make a rediscovery look novel.
  **HOW:** Add strongest related approaches, compute/parameter matching, confidence intervals, and citation-backed related work.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/MLInvention` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
- **WHAT:** Harden data provenance and leakage controls.
  **WHY:** Leakage or undocumented preprocessing can invalidate conclusions.
  **HOW:** Add dataset cards, split manifests, licenses, hashes, and leakage tests.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/MLInvention` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.
## P3 Checklist
- **WHAT:** Improve reviewer ergonomics.
  **WHY:** Reviewers lose trust when the claim path is hard to trace.
  **HOW:** Add one command, one manifest, and generated paper-table provenance.
  **WHERE:** `/Volumes/PRO-BLADE/GitHub-Every-Repo/MLInvention` and cited files/components above.
  **VERIFY:** rerun the repository's clean setup/tests/reproduction script; compare generated artifacts to retained manifests and paper claims.

