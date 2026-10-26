"""Render the project banner (README header, GitHub social preview, LinkedIn).

Draws the real GVNS solution on the Germany network of the benchmark corpus:
the road graph underneath, the vehicle flows of the solution as arcs whose
width and colour follow the number of vehicles, and the storages sized by
transshipment capacity and coloured by congestion. A strip of other real
networks from the corpus runs under the title.

Needs the instance corpus in Generated_Data/ (see README, Section 3) and the
stored solutions in Results/Real_Graph/.

    python assets/make_banner.py

Writes assets/banner.png (2560x1280, README header), assets/social_preview.png
(1280x640, GitHub social preview, under its 1 MB limit) and
assets/banner_linkedin.png (1200x627, LinkedIn link/post image).
"""
import ast
import glob
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "Generated_Data", "Real_Graph")
SOL = os.path.join(REPO, "Results", "Real_Graph")
OUT = os.path.join(REPO, "assets")

# Fira Sans if available (ships with TeX Live), otherwise matplotlib's default.
for f in glob.glob("/usr/local/texlive/*/texmf-dist/fonts/opentype/public/fira/FiraSans-*.otf"):
    font_manager.fontManager.addfont(f)
FONT = "Fira Sans" if any("Fira Sans" == f.name for f in font_manager.fontManager.ttflist) \
    else "DejaVu Sans"

BG_TOP, BG_BOTTOM = "#0A1224", "#13254A"
ROAD = "#2C4470"
INK = "#EAF0FA"
MUTED = "#8FA3C7"
ACCENT = "#FFB547"
FLOW = LinearSegmentedColormap.from_list("flow", ["#2FB5C9", "#7BD3B0", "#FFD166", "#FF8A3D"])
HEAT = LinearSegmentedColormap.from_list("heat", ["#3B6FB6", "#9B5DE5", "#F15BB5", "#FF5D3A", "#FFD23F"])


def load(name):
    d, s = os.path.join(DATA, name), os.path.join(SOL, name)
    pos = pd.read_csv(os.path.join(d, "pos_pop.csv"))
    off = pd.read_csv(os.path.join(d, "offices.csv"))
    g = nx.read_graphml(os.path.join(d, "graph.graphml"))
    veh = pd.read_csv(os.path.join(s, "EdgeVehicleCount.csv"))
    res = pd.read_csv(os.path.join(s, "result.csv"))
    x, y = pos["x"].to_numpy(float), pos["y"].to_numpy(float)
    n = len(x)
    cap = off.set_index("office_id")["transfer_max"].reindex(range(n)).fillna(0).to_numpy(float)
    transit = np.zeros(n)
    for r in res.itertuples():
        path = ast.literal_eval(r.path_nodes) if isinstance(r.path_nodes, str) else r.path_nodes
        for v in path[1:-1]:
            transit[int(v)] += float(r.volume)
    overload = np.divide(transit, cap, out=np.zeros(n), where=cap > 0)
    roads = [(int(a), int(b)) for a, b in g.edges()]
    return dict(x=x, y=y, cap=cap, overload=overload, roads=roads, veh=veh)


def arc(p, q, bend=0.12, k=24):
    """Quadratic Bezier from p to q, bowed to one side by `bend` x length."""
    p, q = np.asarray(p), np.asarray(q)
    m = (p + q) / 2
    d = q - p
    c = m + bend * np.array([-d[1], d[0]])
    t = np.linspace(0, 1, k)[:, None]
    return (1 - t) ** 2 * p + 2 * (1 - t) * t * c + t ** 2 * q


def normalise(net, box):
    """Map the network into box = (x0, y0, w, h) in axes coordinates, keeping aspect."""
    x, y = net["x"], net["y"]
    x0, y0, w, h = box
    sx = w / (x.max() - x.min())
    sy = h / (y.max() - y.min())
    s = min(sx, sy)
    ox = x0 + (w - s * (x.max() - x.min())) / 2
    oy = y0 + (h - s * (y.max() - y.min())) / 2
    return ox + s * (x - x.min()), oy + s * (y - y.min()), s


def draw_network(ax, net, box, hero=True, aspect=1.0):
    X, Y, _ = normalise(net, box)
    pts = np.c_[X, Y]
    # roads of the underlying graph
    segs = [[pts[a], pts[b]] for a, b in net["roads"]]
    ax.add_collection(LineCollection(segs, colors="#4A6A9E" if hero else ROAD,
                                     linewidths=1.0 if hero else 0.6,
                                     alpha=0.75 if hero else 0.8, zorder=2.5 if hero else 1))
    veh = net["veh"][net["veh"]["vehicle"] > 0]
    vmax = np.quantile(veh["vehicle"], 0.995)
    order = veh.sort_values("vehicle")
    flows, widths, colours, vals = [], [], [], []
    for e in order.itertuples():
        a, b, v = int(e.edge_src), int(e.edge_dst), float(e.vehicle)
        if not hero and v < 3:
            continue
        flows.append(arc(pts[a], pts[b], bend=0.07 if hero else 0.06))
        level = min(v / vmax, 1.0)
        widths.append((0.3 + 3.6 * level ** 0.8) if hero else (0.2 + 1.2 * level))
        colours.append(FLOW(level ** 0.6))
        vals.append(v)
    vals = np.array(vals)
    # one- and two-truck shipments are the bulk of the edges: keep them as haze
    alphas = np.where(vals <= 1, 0.035, np.where(vals == 2, 0.12, 0.85))
    rgba = np.array(colours)
    rgba[:, 3] = alphas if hero else 0.6
    # glow: a wide, faint copy underneath the bright core
    if hero:
        glow = rgba.copy(); glow[:, 3] *= np.where(vals >= 3, 0.22, 0.0)
        ax.add_collection(LineCollection(flows, colors=glow, linewidths=np.array(widths) * 4.0,
                                         capstyle="round", zorder=2))
    ax.add_collection(LineCollection(flows, colors=rgba, linewidths=widths,
                                     capstyle="round", zorder=3))
    # storages: area ~ capacity, colour ~ congestion
    cap = net["cap"] / net["cap"].max()
    ov = np.clip(net["overload"], 0, 1)
    size = (25 + 420 * cap) if hero else (3 + 30 * cap)
    if hero:
        ax.scatter(X, Y, s=size * 3.2, c=ov, cmap=HEAT, vmin=0, vmax=1, alpha=0.18,
                   linewidths=0, zorder=4)
    ax.scatter(X, Y, s=size, c=ov, cmap=HEAT, vmin=0, vmax=1,
               edgecolors="#0A1224", linewidths=0.8 if hero else 0.3, zorder=5)
    return X, Y


def render(path, w_px, h_px, dpi):
    W, H = w_px / dpi, h_px / dpi
    fig = plt.figure(figsize=(W, H), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W / H)  # x in units of the height, so circles stay round
    ax.set_ylim(0, 1)
    ax.axis("off")
    r = W / H
    # vertical gradient background
    grad = np.linspace(0, 1, 256)[:, None]
    bg = LinearSegmentedColormap.from_list("bg", [BG_BOTTOM, BG_TOP])
    ax.imshow(grad, extent=[0, r, 0, 1], origin="lower", cmap=bg, aspect="auto", zorder=0)

    # hero: Germany on the right
    de = load("Germany")
    draw_network(ax, de, (r * 0.555, 0.07, r * 0.40, 0.86), hero=True)
    ax.text(r * 0.965, 0.045, "Germany · 49 storages · GVNS solution", ha="right", va="bottom",
            color=MUTED, fontsize=8.6, family=FONT, zorder=6)

    # title block
    x0 = r * 0.045
    tag = ax.text(x0, 0.865, "OPTIMAL LOGISTIC NETWORK FLOWS", color=ACCENT, fontsize=11,
                  family=FONT, weight="bold", va="bottom")
    fig.canvas.draw()
    bb = tag.get_window_extent().transformed(ax.transData.inverted())
    ax.text(bb.x1 + r * 0.012, 0.865, "·   OPTIMA 2026   ·   arXiv:2610.30139", color=MUTED,
            fontsize=11, family=FONT, va="bottom")
    ax.text(x0, 0.835, "General Variable\nNeighborhood Search", color=INK, fontsize=34,
            family=FONT, weight="bold", va="top", linespacing=1.05)
    ax.text(x0, 0.625, "for multi-commodity freight routing with integer truck loads\n"
            "and hard transshipment capacities at every storage",
            color=MUTED, fontsize=12.2, family=FONT, va="top", linespacing=1.35)

    stats = [("≈ 1 %", "from the branch-and-bound\nlower bound on small networks"),
             ("1.55 ×", "cost of a time-limited exact\nMILP solver's solution at |V| = 50"),
             ("50", "open instances, incl. 15 real\nroad networks (EU · US · RU)")]
    for i, (big, small) in enumerate(stats):
        sx = x0 + i * r * 0.165
        ax.text(sx, 0.445, big, color=INK, fontsize=21, family=FONT, weight="bold", va="bottom")
        ax.text(sx, 0.425, small, color=MUTED, fontsize=8.4, family=FONT, va="top",
                linespacing=1.3)

    # strip of other real networks from the corpus
    strip = ["United Kingdom", "Spain", "Italy", "Sweden", "Texas_USA", "California_USA"]
    labels = ["UK", "Spain", "Italy", "Sweden", "Texas", "California"]
    tile_w, gap, y_t, h_t = r * 0.072, r * 0.0105, 0.085, 0.19
    for i, (name, lab) in enumerate(zip(strip, labels)):
        bx = x0 + i * (tile_w + gap)
        draw_network(ax, load(name), (bx, y_t, tile_w, h_t), hero=False)
        ax.text(bx + tile_w / 2, y_t - 0.035, lab, ha="center", color=MUTED,
                fontsize=7.6, family=FONT)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=dpi, facecolor=BG_TOP)
    plt.close(fig)
    print("wrote", path)


if __name__ == "__main__":
    render(os.path.join(OUT, "banner.png"), 2560, 1280, 200)            # README
    render(os.path.join(OUT, "social_preview.png"), 1280, 640, 100)     # GitHub (< 1 MB)
    render(os.path.join(OUT, "banner_linkedin.png"), 1200, 627, 94)     # LinkedIn
