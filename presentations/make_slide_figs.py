"""Regenerate the slide figures of the OPTIMA 2026 talk from Results/*.csv.

    python presentations/make_slide_figs.py

Writes presentations/figs/{ratios_synthetic,ratios_real,ablation,seed_spread}.pdf.
The numbers are the same as in papers/GVNS (Table 2 / Table 3); only the
styling differs (larger fonts, 16:9-friendly aspect ratio).
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(REPO, "Results")
OUT = os.path.join(REPO, "presentations", "figs")

plt.rcParams.update({
    "font.size": 13, "axes.titlesize": 14, "axes.labelsize": 13,
    "legend.fontsize": 11, "xtick.labelsize": 12, "ytick.labelsize": 12,
    "font.family": "sans-serif",
    "font.sans-serif": ["Fira Sans", "DejaVu Sans", "Helvetica", "Arial"],
    "axes.spines.top": False,
})

C_LP, C_RND, C_MIP, C_GAP, C_GVNS = "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#4d4d4d"


def short(name):
    """Instance name as it appears on the slides."""
    return (name.replace("_USA", "").replace("_", " ")
            .replace("United Kingdom", "UK").replace("Europe Russia", "European Russia"))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def rows(name):
    with open(os.path.join(RES, name)) as f:
        return list(csv.DictReader(f))


def agg_by_size(recs):
    keys = ["ratio_lp_relax", "ratio_rounded", "ratio_milp", "gvns_gap_to_LB"]
    by = {}
    for r in recs:
        by.setdefault(int(r["size"]), []).append(r)
    out = []
    for s in sorted(by):
        rec = {"size": s, "label": str(s)}
        for k in keys:
            vals = [v for v in (num(r[k]) for r in by[s]) if v is not None]
            rec[k] = sum(vals) / len(vals) if vals else None
        out.append(rec)
    return out


def ratio_plot(recs, title, path, categorical=False):
    xs = list(range(len(recs))) if categorical else [r["size"] for r in recs]
    fig, ax = plt.subplots(figsize=(7.2, 4.9 if categorical else 4.6))
    ax.axhline(1.0, color=C_GVNS, lw=1.5, ls="--", label="GVNS (= 1.0)")
    series = [("ratio_lp_relax", "LP relaxation (lower bound)", "o", C_LP),
              ("ratio_rounded", "Rounded LP (start solution)", "s", C_RND),
              ("ratio_milp", "Exact solver, comparable time budget", "^", C_MIP)]
    for key, lab, mk, col in series:
        pts = [(x, num(r[key])) for x, r in zip(xs, recs) if num(r[key]) is not None]
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], marker=mk, color=col,
                    lw=2, ms=7, label=lab)
    ax2 = ax.twinx()
    gp = [(x, 100 * num(r["gvns_gap_to_LB"])) for x, r in zip(xs, recs)
          if num(r["gvns_gap_to_LB"]) is not None]
    ax2.plot([p[0] for p in gp], [p[1] for p in gp], color=C_GAP, marker="D",
             ls=":", lw=2, ms=6, label="GVNS gap to dual bound (right axis)")
    ax2.set_ylabel("gap to dual bound (%)", color=C_GAP)
    ax2.tick_params(axis="y", labelcolor=C_GAP)
    ax2.spines["top"].set_visible(False)
    ax2.set_ylim(bottom=0)
    ax.set_ylabel("objective ratio to GVNS")
    ax.set_ylim(0.3, 3.3)
    if categorical:
        ax.set_xticks(xs)
        ax.set_xticklabels([f'{short(r["name"])}\n{r["size"]}' for r in recs],
                           rotation=60, ha="right", fontsize=10.5)
        ax.set_xlabel("")
    else:
        ax.set_xlabel("number of storages |V|")
        ax.set_xticks([r["size"] for r in recs])
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper center", bbox_to_anchor=(0.5, -0.40 if categorical else -0.18),
              ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def ablation_plot(path):
    comp = rows("components_A.csv")
    order = [("N1", "without $N_1$\n(reload-aware\nshortest paths)"),
             ("N2", "without $N_2$\n(partially\nloaded edges)"),
             ("N3", "without $N_3$\n(congestion\ndetours)"),
             ("bvns", "Basic VNS\n(local search\nonly on $N_1$)")]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    w = 0.36
    for j, (grp, col, lab) in enumerate([("synthetic", C_LP, "synthetic"), ("real", C_RND, "real-geometry")]):
        med, mx = [], []
        for key, _ in order:
            r = next(r for r in comp if r["variant"] == key and r["group"] == grp)
            med.append(100 * num(r["median_increase"]))
            mx.append(100 * num(r["max_increase"]))
        xs = [i + (j - 0.5) * w for i in range(len(order))]
        ax.bar(xs, med, width=w, color=col, label=f"median increase, {lab}")
        for x, m, M in zip(xs, med, mx):
            ax.annotate(f"+{m:.1f}%", (x, m), ha="center", va="bottom", fontsize=12,
                        xytext=(0, 2), textcoords="offset points")
            ax.annotate(f"max\n+{M:.1f}%", (x, m), ha="center", va="bottom", fontsize=10,
                        color="0.35", xytext=(0, 18), textcoords="offset points")
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([l for _, l in order], fontsize=10)
    ax.set_ylim(0, 5.6)
    ax.set_ylabel("objective increase vs. full GVNS (%)")
    ax.set_title("What each component is worth (best of 5 seeds, same budget)")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def seed_spread_plot(path):
    per = rows("final_per_instance.csv")
    syn = agg_by_size([r for r in per if r["group"] == "synthetic"])
    real = sorted([r for r in per if r["group"] == "real"], key=lambda r: int(r["size"]))
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    # synthetic: mean std% per size; real: per instance
    by = {}
    for r in per:
        if r["group"] == "synthetic":
            by.setdefault(int(r["size"]), []).append(100 * num(r["gvns_std_pct"]))
    ax.plot(sorted(by), [sum(by[s]) / len(by[s]) for s in sorted(by)], marker="o", color=C_LP,
            lw=2, ms=7, label="synthetic (mean per size)")
    ax.scatter([int(r["size"]) for r in real], [100 * num(r["gvns_std_pct"]) for r in real],
               marker="s", color=C_RND, s=50, zorder=3, label="real-geometry (per network)")
    offsets = {"Italy": (-8, 0, "right"), "Germany": (8, -4, "left"), "Europe Russia": (-8, 0, "right")}
    for r in real:
        if r["name"] in offsets:
            dx, dy, ha = offsets[r["name"]]
            ax.annotate(short(r["name"]), (int(r["size"]), 100 * num(r["gvns_std_pct"])),
                        xytext=(dx, dy), textcoords="offset points", fontsize=10, va="center", ha=ha)
    ax.set_ylim(-0.1, 3.0)
    ax.set_xlabel("number of storages |V|")
    ax.set_ylabel("across-seed std. dev. (% of mean)")
    ax.set_title("Across-seed spread of the GVNS objective (10 seeds)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path)


def main():
    os.makedirs(OUT, exist_ok=True)
    per = rows("final_per_instance.csv")
    syn = [r for r in per if r["group"] == "synthetic"]
    real = sorted([r for r in per if r["group"] == "real"], key=lambda r: int(r["size"]))
    ratio_plot(agg_by_size(syn), "Synthetic instances (mean per size)",
               os.path.join(OUT, "ratios_synthetic.pdf"))
    ratio_plot(real, "Real-geometry regional networks",
               os.path.join(OUT, "ratios_real.pdf"), categorical=True)
    ablation_plot(os.path.join(OUT, "ablation.pdf"))
    seed_spread_plot(os.path.join(OUT, "seed_spread.pdf"))


if __name__ == "__main__":
    main()
