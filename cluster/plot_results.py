"""Regenerate the Section-6 ratio figures from the final results.

Produces papers/GVNS/figs/synthetic_ratios.pdf and papers/GVNS/figs/real_ratios.pdf:
the objective ratio of each reference method to GVNS vs network size, plus the
GVNS optimality gap to the best lower bound.

    python cluster/plot_results.py
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PER = os.path.join(REPO, "Results/final_per_instance.csv")
OUT = os.path.join(REPO, "papers/GVNS/figs")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load():
    with open(PER) as f:
        return list(csv.DictReader(f))


def agg_by_size(rows):
    """mean of each ratio + gap per size (for the synthetic set)."""
    keys = ["ratio_lp_relax", "ratio_rounded", "ratio_milp", "gvns_gap_to_LB"]
    by = {}
    for r in rows:
        by.setdefault(int(r["size"]), []).append(r)
    out = []
    for s in sorted(by):
        rec = {"size": s}
        for k in keys:
            vals = [num(r[k]) for r in by[s]]
            vals = [v for v in vals if v is not None]
            rec[k] = sum(vals) / len(vals) if vals else None
        out.append(rec)
    return out


def plot(records, title, path, x_is_size=True):
    xs = [r["size"] for r in records]
    series = [
        ("ratio_lp_relax", "LP relaxation (lower bound)", "o", "-"),
        ("ratio_rounded", "Rounded LP (start / upper bound)", "s", "-"),
        ("ratio_milp", "Time-limited MIP incumbent", "^", "-"),
    ]
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    ax.axhline(1.0, color="0.4", lw=1, ls="--", label="GVNS reference (1.0)")
    for key, lab, mk, ls in series:
        pts = [(x, num(r[key])) for x, r in zip(xs, records) if num(r[key]) is not None]
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], marker=mk, ls=ls, label=lab, ms=5)
    # secondary axis: GVNS gap to lower bound (%)
    ax2 = ax.twinx()
    gp = [(x, 100 * num(r["gvns_gap_to_LB"])) for x, r in zip(xs, records)
          if num(r["gvns_gap_to_LB"]) is not None]
    if gp:
        ax2.plot([p[0] for p in gp], [p[1] for p in gp], color="crimson",
                 marker="D", ls=":", ms=4, label="GVNS gap to LB (right)")
        ax2.set_ylabel("GVNS gap to lower bound (%)", color="crimson", fontsize=9)
        ax2.tick_params(axis="y", labelcolor="crimson")
    ax.set_xlabel("number of storages |V|")
    ax.set_ylabel("objective ratio to GVNS")
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.3)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"wrote {path}")


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = load()
    syn = [r for r in rows if r["group"] == "synthetic"]
    real = sorted([r for r in rows if r["group"] == "real"], key=lambda r: int(r["size"]))
    plot(agg_by_size(syn), "Synthetic instances (mean per size)",
         os.path.join(OUT, "synthetic_ratios.pdf"))
    plot(real, "Real-geometry regional networks",
         os.path.join(OUT, "real_ratios.pdf"))


if __name__ == "__main__":
    main()
