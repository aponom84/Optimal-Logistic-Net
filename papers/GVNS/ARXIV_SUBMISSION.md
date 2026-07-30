# arXiv submission — GVNS paper

Everything needed to submit *A General Variable Neighborhood Search for Logistic
Network Flow Design with Nonlinear Edge Costs and Transshipment Capacities* to
arXiv (<https://arxiv.org/submit>).

## 1. What to upload

**`logistics_gvns_arxiv.zip`** (70 KB) — built from `arxiv/`. Contents:

```
logistics_gvns.tex          main source (arXiv version)
figs/germany_solution.pdf
figs/real_ratios.pdf
figs/synthetic_ratios.pdf
```

**`llncs.cls` is deliberately *not* bundled.** arXiv's TeX Live provides the
`llncs` package — verified against
<https://info.arxiv.org/help/texlive_package_list.html>, which lists both
`llncs` and `llncsconf` under `collection-publishers` — so the class comes from
their system tree. The paper was proofed against stock llncs **v2.24
(29-Jan-2024)**, unmodified.

Consequence to check at submission time: arXiv lets you pick TeX Live 2023 or
2025, and their `llncs` version may not be v2.24. A publisher class version bump
can shift line breaks, and the paper sits at exactly 15 pages with no slack —
so **confirm the arXiv-generated PDF is still 15 pages** (Section 4, step 3).
If it is not, add `llncs.cls` back to the archive to pin the version:

```bash
cp papers/GVNS/llncs.cls papers/GVNS/arxiv/ && cd papers/GVNS/arxiv && zip -r -X ../logistics_gvns_arxiv.zip llncs.cls
```

No `.pdf` of the article, no `.bib`, no build artefacts, no `.DS_Store`.
The bibliography is a manual `thebibliography` environment, so **no BibTeX run and
no `.bbl` are needed** (`cHARISMa2026.bib` is unused and deliberately excluded).

Verified: unzips into an empty directory and compiles with
`pdflatex ×2` against the system `llncs` class → 15 pages, no errors, no
undefined references or citations, no rerun warnings; output text-identical to
the conference PDF.

## 2. Differences from the conference source (`../logistics_gvns.tex`)

The text, tables, figures, numbers and bibliography are **identical** — a
`pdftotext` diff of the two PDFs is empty. The two additions are invisible in
the rendered output:

1. `\pdfoutput=1` on line 1 — tells arXiv's AutoTeX to use pdfLaTeX (the figures
   are PDF). The original was built with XeLaTeX, which arXiv does not support;
   the source compiles unchanged under pdfLaTeX.
2. `\hypersetup{pdftitle=…, pdfauthor=…, pdfkeywords=…}` — PDF metadata.

No preprint/venue note is printed on the title page; the preprint status is
conveyed by the arXiv `Comments` field (Section 3).

## 3. Metadata to paste into the submission form

**Title**

```
A General Variable Neighborhood Search for Logistic Network Flow Design with Nonlinear Edge Costs and Transshipment Capacities
```

**Authors**

```
Varvara Kovaleva, Alexander Ponomarenko
```

**Abstract** (plain text, ~1.7 k chars — arXiv limit is 1920)

```
We study the problem of routing multiple commodities through a logistic transport
network so as to minimise the joint cost of vehicle movements and of transshipment
(reload) operations at intermediate storages. The problem combines two features that
are common in practice but rarely treated together: edge costs that are nonlinear in
the transported volume, because freight is carried by vehicles of fixed capacity, and
hard upper bounds on the volume that can be reloaded at each node. We formulate the
problem as a mixed integer linear program in both an arc-based and a path-based form,
derive its linear relaxation, and propose a metaheuristic solver based on General
Variable Neighborhood Search (GVNS). The method works in the path space and relies on
three problem-specific neighborhoods that generate new candidate paths by (i) shortest
paths under a reload-aware metric, (ii) edges carrying partially loaded vehicles, and
(iii) detours around congested storages. We evaluate the method on our open benchmark
for this problem (arXiv:2606.20653): a corpus of realistic logistic networks calibrated
on real road graphs of nine European countries, five U.S. states and the European part
of Russia, with near-planar topology (Zipf city sizes, a spatial-network budget model,
and a doubly constrained gravity demand model). On 35 synthetic and 15 real-geometry
instances with up to 150 storages, GVNS returns solutions within about one percent of
the best dual bound on small networks -- a branch-and-bound lower bound substantially
tighter than the LP relaxation -- is stable across random seeds, and for a comparable
wall-clock budget is up to 55% better than a time-limited exact solver on the medium
instances.
```

**Comments**

```
15 pages, 2 figures, 4 tables, 2 algorithms. Preprint of a paper submitted to a Springer LNCS conference volume. Benchmark instances: arXiv:2606.20653; dataset: https://doi.org/10.5281/zenodo.20372456
```

**Categories**

| | |
|---|---|
| Primary | `math.OC` — Optimization and Control |
| Cross-list | `cs.DS` — Data Structures and Algorithms |
| Optional 2nd cross-list | `cs.DM` — Discrete Mathematics |

Use the same primary category as the companion benchmark paper
(arXiv:2606.20653) so the two stay together in listings.

**MSC class**: `90B06, 90B10, 90C11, 90C59`
**ACM class**: `G.1.6, G.2.2`

**Journal ref / DOI**: leave empty now; fill in after acceptance (Section 6).

**License**: choose the default **arXiv.org perpetual, non-exclusive license**.
Do *not* pick CC BY here — a Creative Commons licence can conflict with the
copyright transfer / licence-to-publish agreement Springer asks for on
acceptance. (The *dataset* on Zenodo stays CC BY 4.0; that is independent.)

## 4. Submission checklist

1. Start a new submission, pick *Article*, then the licence above.
2. Upload `logistics_gvns_arxiv.zip` as the source package.
3. Let arXiv compile it; check the generated PDF has 15 pages, both figures, all
   four tables, and both algorithms.
4. Paste the metadata from Section 3.
5. Add the ORCID / author-identifier links if the authors have them.
6. Submit. arXiv announces on the next business-day cycle.

## 5. Rebuilding the archive

```bash
cd papers/GVNS/arxiv && rm -f ../logistics_gvns_arxiv.zip && zip -r -X ../logistics_gvns_arxiv.zip logistics_gvns.tex figs -x '*.DS_Store'
```

Local test build (same engine arXiv uses):

```bash
cd papers/GVNS/arxiv && pdflatex logistics_gvns.tex && pdflatex logistics_gvns.tex
```

## 6. After acceptance

Fill the `Journal ref` and `DOI` fields in the arXiv metadata and update the
`Comments` field. If Springer's licence-to-publish requires the accepted
manuscript to carry their attribution notice, add it as an unnumbered footnote
after `\maketitle` in `arxiv/logistics_gvns.tex`, rebuild the zip (Section 5)
and upload it as a **new version** of the same arXiv entry. Springer's standard
wording is:

> This version of the contribution has been accepted for publication, after peer
> review, but is not the Version of Record and does not reflect post-acceptance
> improvements, or any corrections. The Version of Record is available online at
> `<DOI>`. Use of this Accepted Version is subject to the publisher's Accepted
> Manuscript terms of use,
> <https://www.springernature.com/gp/open-research/policies/accepted-manuscript-terms>.
