# OPTIMA 2026 talk

Slides for the 20–30 minute talk *A General Variable Neighborhood Search for
Logistic Network Flow Design with Nonlinear Edge Costs and Transshipment
Capacities* (paper: `../papers/GVNS/logistics_gvns.tex`).

| file | what |
|---|---|
| `optima2026_gvns.tex` | Beamer source (16:9, metropolis theme, Fira fonts from CTAN — no system fonts needed) |
| `optima2026_gvns.pdf` | the slides: 22 main-line frames + 4 backup frames |
| `optima2026_gvns_notes.pdf` | the same deck with the speaker notes on a second screen (for a two-screen presenter such as `pdfpc` or Skim; or simply read the notes) |
| `make_slide_figs.py` | regenerates `figs/ratios_synthetic.pdf`, `figs/ratios_real.pdf`, `figs/ablation.pdf`, `figs/seed_spread.pdf` from `../Results/*.csv` |
| `figs/germany_solution.pdf` | copied from the paper (`cluster/plot_solution.py`) |
| `build.sh` | regenerates the plots and compiles both PDFs |

```bash
./presentations/build.sh
```

## Structure and timing

About 25 minutes spoken for the full main line. Four frames are marked
`[optional]` in the source (Why not simply run a published network-design
code?; Path form and the LP relaxation; Preprocessing and the starting
solution; How many seeds do you need?); skipping them gives a ~21-minute
version for a strict 20-minute slot. The appendix (no progress bar) holds
backup slides for questions: parameter table (Table 1), exact-solver
behaviour and tuning grid, per-instance numbers at |V| = 50, literature map.
The speaker notes on the closing slide say which backup answers which
question; detail the speaker says but the audience need not read lives in
the notes rather than on the slides.

1. The problem (4 frames): freight picture with the Germany map as hook, the
   two features (per-vehicle step cost, reload ceiling), why published MCND
   codes are not comparable.
2. Model (2 frames): arc MILP; path form and LP relaxation.
3. The GVNS (6 frames): loop, preprocessing/start, move primitive, N1, N2, N3.
4. Experiments (6 frames): benchmark, yardsticks, synthetic results, real
   results, seeds, component study.
5. Closing (3 frames): limitations paired with next steps, takeaways, links
   with QR codes.

Every number on the slides comes from the paper (Tables 1–3 and the text) or
from `../Results/final_by_size.csv`, `final_per_instance.csv`,
`components_A.csv`, `exact_tuning.csv`; the deck was fact-checked claim by
claim against those sources.
