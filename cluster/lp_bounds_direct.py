"""Closed-form LP-relaxation and rounded-LP bounds for every instance.

On the completed graph the direct edge $(s_k,t_k)$ has the shortest, transit-free
cost, so (Sections 2.6 and 3.2) routing each commodity along its direct edge is
optimal for the LP relaxation and feasible for the rounded upper bound. Hence
both bounds have a trivial closed form -- no LP solve, valid at every size:

    lp_relax  = sum_e c_e * (flow_e / C)          (continuous vehicles)
    rounded   = sum_e c_e * ceil(flow_e / C)      (== GVNS start solution)

where flow_e is the total demand whose origin-destination pair is edge e.
This matches Solver.SolveMIP_HIGHS_Relaxed to machine precision but works for
|V|=100,150 where building the full LP is intractable.

    python cluster/lp_bounds_direct.py --out Results/lp_bounds.csv
"""
import argparse
import csv
import math
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SET_DIRS = {"synthetic": "Generated_Data/Synthetic", "real": "Generated_Data/Real_Graph"}


def storages_of(folder):
    with open(os.path.join(folder, "offices.csv")) as f:
        return sum(1 for _ in f) - 1


def direct_bounds(folder, cap):
    price = {}
    with open(os.path.join(folder, "distance_matrix.csv")) as f:
        for r in csv.DictReader(f):
            if r["src"] != r["dst"] and float(r["price"]) > 0:
                price[(int(r["src"]), int(r["dst"]))] = float(r["price"])
    flow = {}
    with open(os.path.join(folder, "reqs.csv")) as f:
        for r in csv.DictReader(f):
            e = (int(r["src"]), int(r["dst"]))
            flow[e] = flow.get(e, 0.0) + float(r["volume"])
    lp = sum(price[e] * fl / cap for e, fl in flow.items())
    rounded = sum(price[e] * math.ceil(fl / cap) for e, fl in flow.items())
    return lp, rounded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", default=["synthetic", "real"], choices=list(SET_DIRS))
    ap.add_argument("--cap", type=float, default=50)
    ap.add_argument("--out", default="Results/lp_bounds.csv")
    args = ap.parse_args()

    rows = []
    for grp in args.sets:
        base = os.path.join(REPO, SET_DIRS[grp])
        for name in sorted(os.listdir(base)):
            folder = os.path.join(base, name)
            if not os.path.isdir(folder) or not os.path.exists(os.path.join(folder, "offices.csv")):
                continue
            lp, rounded = direct_bounds(folder, args.cap)
            rows.append({"group": grp, "name": name, "size": storages_of(folder),
                         "lp_relax": lp, "rounded_lp": rounded, "lp_time": 0.0})

    rows.sort(key=lambda r: (r["size"], r["group"], r["name"]))
    out = os.path.join(REPO, args.out) if not os.path.isabs(args.out) else args.out
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["group", "name", "size", "lp_relax", "rounded_lp", "lp_time"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
