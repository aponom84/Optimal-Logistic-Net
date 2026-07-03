"""Join LP bounds + exact dual bounds + GVNS (over seeds) into the paper tables.

Inputs:
  Results/Exact/*.json     per (instance, backend): primal, dual, gap, proven, status
  Results/GVNS/*.json      per (instance, seed): result_price, init_price, time
  Results/lp_bounds.csv    per instance: lp_relax, rounded_lp

Outputs:
  Results/final_per_instance.csv
  Results/final_by_size.csv
  a LaTeX per-size table on stdout

Key new metric: GVNS optimality gap to the best valid lower bound (the MIP dual
bound), which is far tighter than the LP relaxation.

    python cluster/build_table.py
"""
import argparse
import csv
import glob
import json
import math
import os
import statistics as st

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json_dir(d):
    out = []
    for p in sorted(glob.glob(os.path.join(d, "*.json"))):
        with open(p) as f:
            out.append(json.load(f))
    return out


def key(r):
    return (r.get("group", ""), r.get("instance", r.get("name", "")))


def num(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exact", default="Results/Exact")
    ap.add_argument("--gvns", default="Results/GVNS")
    ap.add_argument("--lp", default="Results/lp_bounds.csv")
    ap.add_argument("--out-instance", default="Results/final_per_instance.csv")
    ap.add_argument("--out-size", default="Results/final_by_size.csv")
    args = ap.parse_args()

    exact = [r for r in load_json_dir(args.exact) if r.get("ok")]
    gvns = [r for r in load_json_dir(args.gvns) if r.get("ok")]
    lp = {}
    if os.path.exists(args.lp):
        with open(args.lp) as f:
            for row in csv.DictReader(f):
                lp[(row["group"], row["name"])] = row

    # index exact by instance -> {backend: rec}
    exact_by = {}
    for r in exact:
        exact_by.setdefault(key(r), {})[r.get("backend", "?")] = r
    # index gvns by instance -> [recs]
    gvns_by = {}
    for r in gvns:
        gvns_by.setdefault(key(r), []).append(r)

    instances = sorted(set(list(exact_by) + list(gvns_by) + list(lp)),
                       key=lambda k: (k[0], k[1]))

    per = []
    for k in instances:
        grp, name = k
        size = None
        row = {"group": grp, "name": name}

        # GVNS over seeds
        gs = gvns_by.get(k, [])
        prices = [num(r.get("result_price")) for r in gs]
        prices = [p for p in prices if p is not None and p > 0]
        gvns_best = min(prices) if prices else None
        gvns_mean = st.mean(prices) if prices else None
        gvns_std = st.pstdev(prices) if len(prices) > 1 else 0.0
        # GVNS start solution == "Rounded LP" (paper's definition); deterministic
        # per instance, so available at every size incl. the huge ones.
        inits = [num(r.get("init_price")) for r in gs]
        inits = [v for v in inits if v is not None and v > 0]
        gvns_init = st.mean(inits) if inits else None
        if gs:
            size = gs[0].get("size")
        row["n_seeds"] = len(prices)
        row["gvns_best"] = gvns_best
        row["gvns_mean"] = gvns_mean
        row["gvns_std"] = gvns_std
        row["gvns_init"] = gvns_init

        # exact: best dual (max), best primal (min), proven, status
        ex = exact_by.get(k, {})
        duals = [num(r.get("dual_bound")) for r in ex.values()]
        duals = [d for d in duals if d is not None and d > 0]
        prims = [num(r.get("primal_bound")) for r in ex.values()]
        prims = [p for p in prims if p is not None and p > 0]
        best_dual = max(duals) if duals else None
        best_primal = min(prims) if prims else None
        proven = any(r.get("proven_optimal") for r in ex.values())
        if size is None and ex:
            size = next(iter(ex.values())).get("size")
        row["backends"] = "+".join(sorted(ex))
        row["best_dual"] = best_dual
        row["milp_primal"] = best_primal
        row["proven_optimal"] = proven
        row["exact_status"] = ";".join(f"{b}:{r.get('status')}" for b, r in sorted(ex.items()))

        # LP reference bounds
        lpr = lp.get(k, {})
        lp_relax = num(lpr.get("lp_relax"))
        rounded = num(lpr.get("rounded_lp"))
        if size is None:
            size = int(lpr.get("size", 0)) if lpr.get("size") else 0
        row["size"] = int(size or 0)
        row["lp_relax"] = lp_relax
        row["rounded_lp"] = rounded

        # metrics vs GVNS
        def ratio(x):
            return x / gvns_best if (x is not None and gvns_best) else None
        row["ratio_lp_relax"] = ratio(lp_relax)
        # prefer the GVNS start solution (== rounded LP) so this column exists at
        # every size; fall back to the LP job's rounded value if init is missing
        row["ratio_rounded"] = ratio(gvns_init if gvns_init is not None else rounded)
        row["ratio_milp"] = ratio(best_primal)
        # headline: GVNS optimality gap vs best valid lower bound (dual bound)
        lb = best_dual if best_dual is not None else lp_relax
        row["gvns_gap_to_LB"] = ((gvns_best - lb) / lb) if (gvns_best and lb) else None
        row["lb_source"] = "dual" if best_dual is not None else ("lp" if lp_relax else "")
        per.append(row)

    fields = ["group", "size", "name", "n_seeds", "gvns_best", "gvns_mean", "gvns_std",
              "best_dual", "milp_primal", "proven_optimal", "backends", "exact_status",
              "lp_relax", "rounded_lp", "ratio_lp_relax", "ratio_rounded", "ratio_milp",
              "gvns_gap_to_LB", "lb_source"]
    os.makedirs(os.path.dirname(args.out_instance) or ".", exist_ok=True)
    with open(args.out_instance, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in sorted(per, key=lambda r: (r["size"], r["group"], r["name"])):
            w.writerow(r)
    print(f"wrote {len(per)} instances -> {args.out_instance}\n")

    # by-size aggregate
    def avg(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    sizes = sorted({r["size"] for r in per})
    agg_rows = []
    print(f"{'size':>4} {'n':>3} {'proven':>7} {'gap→LB':>8} {'r_LP':>6} {'r_round':>7} "
          f"{'r_MILP':>7} {'gvns_best':>11}")
    for s in sizes:
        sub = [r for r in per if r["size"] == s]
        n = len(sub)
        proven = sum(1 for r in sub if r["proven_optimal"])
        g = avg([r["gvns_gap_to_LB"] for r in sub])
        rl = avg([r["ratio_lp_relax"] for r in sub])
        rr = avg([r["ratio_rounded"] for r in sub])
        rm = avg([r["ratio_milp"] for r in sub])
        gb = avg([r["gvns_best"] for r in sub])
        agg_rows.append({"size": s, "n": n, "proven": proven,
                         "gvns_gap_to_LB": g, "ratio_lp_relax": rl,
                         "ratio_rounded": rr, "ratio_milp": rm})
        fmt = lambda x, p="{:.3f}": (p.format(x) if x is not None else "-")
        print(f"{s:>4} {n:>3} {proven:>3}/{n:<3} {fmt(g,'{:.2%}'):>8} {fmt(rl):>6} "
              f"{fmt(rr):>7} {fmt(rm):>7} {fmt(gb,'{:.0f}'):>11}")

    with open(args.out_size, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["size", "n", "proven", "gvns_gap_to_LB",
                                          "ratio_lp_relax", "ratio_rounded", "ratio_milp"])
        w.writeheader()
        w.writerows(agg_rows)

    # LaTeX per-size rows (avoid backslashes inside f-string expressions: py<3.12)
    print("\n% --- LaTeX rows: size & n & proven & gap-to-LB & r_LP & r_round & r_MILP ---")
    pct = "\\%"
    endrow = " \\\\"
    for a in agg_rows:
        def L(x, p="{:.3f}"):
            return p.format(x) if x is not None else "--"
        gap = L(a["gvns_gap_to_LB"], "{:.1%}").replace("%", pct)
        cols = [str(a["size"]), str(a["n"]), f"{a['proven']}/{a['n']}", gap,
                L(a["ratio_lp_relax"]), L(a["ratio_rounded"]), L(a["ratio_milp"])]
        print(" & ".join(cols) + endrow)


if __name__ == "__main__":
    main()
