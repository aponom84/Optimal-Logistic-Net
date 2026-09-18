#!/usr/bin/env bash
# Build the OPTIMA 2026 talk.
#   1. regenerate the slide plots from Results/*.csv (make_slide_figs.py)
#   2. compile optima2026_gvns.pdf            -- the slides
#   3. compile optima2026_gvns_notes.pdf      -- slides + speaker notes side by side
# metropolis needs two passes for the progress bar / total frame count.
#
#     ./presentations/build.sh
set -euo pipefail
cd "$(dirname "$0")"
python3 make_slide_figs.py
for pass in 1 2; do
  pdflatex -interaction=nonstopmode -halt-on-error optima2026_gvns.tex > /dev/null
done
for pass in 1 2; do
  pdflatex -interaction=nonstopmode -halt-on-error -jobname=optima2026_gvns_notes \
    "\def\shownotes{1}\input{optima2026_gvns.tex}" > /dev/null
done
grep -E "Overfull|Undefined|multiply defined" optima2026_gvns.log || true
echo "slides: $(pdfinfo optima2026_gvns.pdf | awk '/^Pages/{print $2}') pages"
echo "notes : $(pdfinfo optima2026_gvns_notes.pdf | awk '/^Pages/{print $2}') pages"
