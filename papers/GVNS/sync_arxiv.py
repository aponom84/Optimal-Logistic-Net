#!/usr/bin/env python3
r"""Regenerate papers/GVNS/arxiv/logistics_gvns.tex from the conference source.

The two files must stay identical in content; the arXiv one only adds
``\pdfoutput=1`` (so AutoTeX picks pdfLaTeX), a note in the header comment and a
``\hypersetup`` block with the PDF metadata.  Keeping the delta in one script
means an edit to the conference file can never silently miss its twin.

    python papers/GVNS/sync_arxiv.py [--check]
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "logistics_gvns.tex")
DST = os.path.join(HERE, "arxiv", "logistics_gvns.tex")

PDFOUTPUT = "\\pdfoutput=1  % arXiv: build with pdfLaTeX (PDF figures)\n"

HEADER_ANCHOR = "% capacity constraints.\n"
HEADER_NOTE = """%
% arXiv version.  Identical in content to the version submitted to a
% Springer LNCS conference; the only additions are \\pdfoutput=1 and the
% hyperref PDF metadata.
% Build:  pdflatex logistics_gvns  (twice, no BibTeX -- the
% bibliography is a manual thebibliography environment).
"""

META_ANCHOR = "\\usepackage{xcolor}\n"
META = """
% PDF metadata (arXiv version)
\\hypersetup{
  pdftitle={A General Variable Neighborhood Search for Logistic Network Flow
            Design with Nonlinear Edge Costs and Transshipment Capacities},
  pdfauthor={Varvara Kovaleva, Alexander Ponomarenko},
  pdfsubject={Multi-commodity network flow design; variable neighborhood search},
  pdfkeywords={multi-commodity flow, network design, variable neighborhood
               search, metaheuristics, mixed integer programming, logistics}
}
"""


def build(src_text):
    for anchor in (HEADER_ANCHOR, META_ANCHOR):
        if src_text.count(anchor) != 1:
            sys.exit(f"anchor not found exactly once in the conference source: {anchor!r}")
    out = PDFOUTPUT + src_text
    out = out.replace(HEADER_ANCHOR, HEADER_ANCHOR + HEADER_NOTE, 1)
    return out.replace(META_ANCHOR, META_ANCHOR + META, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if the twin is out of date, without writing")
    args = ap.parse_args()

    want = build(open(SRC, encoding="utf-8").read())
    have = open(DST, encoding="utf-8").read() if os.path.exists(DST) else None
    if have == want:
        print("arxiv twin is up to date")
        return
    if args.check:
        sys.exit("arxiv twin is OUT OF DATE -- run papers/GVNS/sync_arxiv.py")
    open(DST, "w", encoding="utf-8").write(want)
    print(f"regenerated {os.path.relpath(DST)}")


if __name__ == "__main__":
    main()
