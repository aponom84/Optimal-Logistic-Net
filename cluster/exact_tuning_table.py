"""Summarise the exact-solver parameter-sensitivity study (review 3, point 4).

The paper's main tables run both solvers at their factory settings apart from
the time limit, the gap target and the thread count.  This script quantifies
what non-default parameters would buy, by comparing each preset against the
``default`` run of the same (instance, backend).

    python cluster/exact_tuning_table.py --tuning Results/Exact_tuning \
        --default Results/Exact

It prints, per backend and preset, the mean and best relative change of the dual
bound and of the incumbent, and how many instances gained a feasible solution
that the default run did not find -- the three numbers the paragraph needs.
"""
import argparse
import collections
import csv
import glob
import json
import math
import os
import statistics as st

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(dirs):
    out = []
    for d in dirs:
        d = d if os.path.isabs(d) else os.path.join(REPO, d)
        for p in sorted(glob.glob(os.path.join(d, "*.json"))):
            with open(p) as f:
                r = json.load(f)
            if r.get("ok"):
                out.append(r)
    return out


def finite(x):
    try:
        v = float(x)
        return v if math.isfinite(v) and v > 0 else None
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuning", nargs="*", default=["Results/Exact_tuning"])
    ap.add_argument("--default", nargs="*", default=["Results/Exact"])
    ap.add_argument("--out", default="Results/exact_tuning.csv")
    args = ap.parse_args()

    recs = load(args.default) + load(args.tuning)
    by = {}
    for r in recs:
        key = (r.get("group", ""), r["instance"], r["backend"],
               (r.get("preset") or "default"))
        by[key] = r

    baseline = {k[:3]: v for k, v in by.items() if k[3] == "default"}
    rows = []
    agg = collections.defaultdict(lambda: {"dual": [], "primal": [], "new_feas": 0, "n": 0})

    for (grp, inst, backend, preset), r in sorted(by.items()):
        if preset == "default":
            continue
        base = baseline.get((grp, inst, backend))
        if base is None:
            print(f"  [warn] no default run for {grp}/{inst}/{backend}; skipped")
            continue
        d, d0 = finite(r.get("dual_bound")), finite(base.get("dual_bound"))
        p, p0 = finite(r.get("primal_bound")), finite(base.get("primal_bound"))
        # dual bound is a lower bound: higher is better. Incumbent: lower is better.
        d_gain = (d / d0 - 1.0) if (d and d0) else None
        p_gain = (1.0 - p / p0) if (p and p0) else None
        new_feas = bool(p) and not bool(p0)
        rows.append({"group": grp, "instance": inst, "backend": backend, "preset": preset,
                     "dual_bound": d, "dual_bound_default": d0,
                     "primal_bound": p, "primal_bound_default": p0,
                     "dual_gain": d_gain, "primal_gain": p_gain,
                     "new_feasible": new_feas,
                     "solve_time": r.get("solve_time"), "nodes": r.get("nodes")})
        a = agg[(backend, preset)]
        a["n"] += 1
        if d_gain is not None: a["dual"].append(d_gain)
        if p_gain is not None: a["primal"].append(p_gain)
        a["new_feas"] += int(new_feas)

    out = args.out if os.path.isabs(args.out) else os.path.join(REPO, args.out)
    if rows:
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {len(rows)} preset runs -> {out}\n")
    else:
        print("no non-default runs found\n")
        return

    print(f"{'backend':8s} {'preset':13s} {'n':>3s} "
          f"{'dual mean':>10s} {'dual best':>10s} {'inc. mean':>10s} {'inc. best':>10s} {'new feas':>9s}")
    for (backend, preset), a in sorted(agg.items()):
        dm = f"{st.mean(a['dual']):+.2%}" if a["dual"] else "--"
        db = f"{max(a['dual']):+.2%}" if a["dual"] else "--"
        pm = f"{st.mean(a['primal']):+.2%}" if a["primal"] else "--"
        pb = f"{max(a['primal']):+.2%}" if a["primal"] else "--"
        print(f"{backend:8s} {preset:13s} {a['n']:>3d} {dm:>10s} {db:>10s} "
              f"{pm:>10s} {pb:>10s} {a['new_feas']:>4d}/{a['n']:<4d}")
    print("\n(dual: positive = tighter lower bound than default;"
          " inc.: positive = cheaper incumbent than default)")


if __name__ == "__main__":
    main()
