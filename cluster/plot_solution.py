"""Render a static figure of a GVNS solution on a real-geometry network.

Mirrors the interactive viewer of Section 5.3: nodes are placed on the network's
geographic layout (size = transshipment capacity, colour = congestion
overload$_v$), and used edges are drawn with width proportional to the number of
vehicles. Produces a PDF for the paper.

    python cluster/plot_solution.py --instance Generated_Data/Real_Graph/Germany \
        --solution Results/Real_Graph/Germany --out doc/figs/germany_solution.pdf
"""
import argparse
import ast
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True)
    ap.add_argument("--solution", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--flip-y", action="store_true", help="flip y to match a north-up map")
    ap.add_argument("--min-veh", type=int, default=3,
                    help="only draw edges carrying at least this many vehicles (backbone)")
    args = ap.parse_args()

    pos = pd.read_csv(os.path.join(args.instance, "pos_pop.csv"))
    off = pd.read_csv(os.path.join(args.instance, "offices.csv"))
    veh = pd.read_csv(os.path.join(args.solution, "EdgeVehicleCount.csv"))
    res = pd.read_csv(os.path.join(args.solution, "result.csv"))

    x = pos["x"].to_numpy(dtype=float)
    y = pos["y"].to_numpy(dtype=float)
    if args.flip_y:
        y = -y
    n = len(x)
    cap = off.set_index("office_id")["transfer_max"].reindex(range(n)).fillna(0).to_numpy()

    # per-node transit volume (intermediate nodes of each commodity path) -> overload_v
    transit = np.zeros(n)
    for _, r in res.iterrows():
        path = r["path_nodes"]
        path = ast.literal_eval(path) if isinstance(path, str) else path
        for node in path[1:-1]:
            transit[int(node)] += float(r["volume"])
    overload = np.divide(transit, cap, out=np.zeros_like(transit), where=cap > 0)

    fig, ax = plt.subplots(figsize=(5.4, 5.0))

    # faint background: every used edge, so no node looks isolated
    used_any = veh[veh["vehicle"] > 0]
    all_used = len(used_any)
    bg = [[(x[int(e.edge_src)], y[int(e.edge_src)]),
           (x[int(e.edge_dst)], y[int(e.edge_dst)])] for e in used_any.itertuples()]
    ax.add_collection(LineCollection(bg, linewidths=0.2, colors="0.72",
                                     alpha=0.18, zorder=0))

    # backbone on top: edges carrying >= min_veh vehicles, width prop. to count
    used = veh[veh["vehicle"] >= args.min_veh]
    segs, widths = [], []
    for _, e in used.iterrows():
        s, d = int(e["edge_src"]), int(e["edge_dst"])
        segs.append([(x[s], y[s]), (x[d], y[d])])
        widths.append(0.4 * float(e["vehicle"]))
    lc = LineCollection(segs, linewidths=np.clip(widths, 0.4, 6.0),
                        colors="0.4", alpha=0.7, zorder=1)
    ax.add_collection(lc)

    # nodes: size = capacity, colour = congestion (overload_v)
    sizes = 30 + 340 * (cap / max(cap.max(), 1e-9))
    sc = ax.scatter(x, y, s=sizes, c=overload, cmap="YlOrRd",
                    vmin=0, vmax=max(1.0, float(np.quantile(overload, 0.98))),
                    edgecolors="0.25", linewidths=0.4, zorder=2)
    cb = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label(r"node congestion $overload_v$", fontsize=9)
    cb.ax.tick_params(labelsize=8)

    # legend proxy for edge width (vehicles)
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], color="0.45", lw=max(0.4 * v, 0.4), label=f"{v} veh.")
               for v in (3, 6, 10)]
    ax.legend(handles=handles, title="edge width", fontsize=8, title_fontsize=8,
              loc="lower left", frameon=False)

    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    fig.savefig(args.out, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {args.out}  (nodes={n}, used edges={all_used}, "
          f"backbone drawn (>={args.min_veh} veh)={len(used)}, "
          f"max overload={overload.max():.2f})")


if __name__ == "__main__":
    main()
