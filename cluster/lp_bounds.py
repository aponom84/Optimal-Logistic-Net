"""Compute the two LP reference bounds for every instance:

  * LP relaxation        (lower bound)  -- Solver.SolveMIP_HIGHS_Relaxed.resultPrice
  * rounded LP           (upper bound)  -- .resultPriceRound  (== GVNS start solution)

These are fast (a single LP each) and reproduce the paper's reference lines.
Writes one CSV row per instance.

    python cluster/lp_bounds.py --sets synthetic real --out Results/lp_bounds.csv
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from NetProductPath import NetProducts
from Solver import SolveMIP_HIGHS_Relaxed

SET_DIRS = {"synthetic": "Generated_Data/Synthetic", "real": "Generated_Data/Real_Graph"}


def storages_of(folder):
    with open(os.path.join(folder, "offices.csv")) as f:
        return sum(1 for _ in f) - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", default=["synthetic", "real"], choices=list(SET_DIRS))
    ap.add_argument("--cap", type=float, default=50)
    ap.add_argument("--out", default="Results/lp_bounds.csv")
    args = ap.parse_args()

    # enumerate instances, smallest first, so the fast ones are captured early
    todo = []
    for grp in args.sets:
        base = SET_DIRS[grp]
        for name in sorted(os.listdir(base)):
            folder = os.path.join(base, name)
            if not os.path.isdir(folder) or not os.path.exists(os.path.join(folder, "offices.csv")):
                continue
            todo.append((storages_of(folder), grp, name, folder))
    todo.sort()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    fields = ["group", "name", "size", "lp_relax", "rounded_lp", "lp_time"]
    n = 0
    # write incrementally so a wall-clock kill never loses completed rows
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        f.flush()
        for size, grp, name, folder in todo:
            t0 = time.time()
            try:
                net = NetProducts(args.cap, folder + "/")
                r = SolveMIP_HIGHS_Relaxed(net)
                row = {"group": grp, "name": name, "size": size,
                       "lp_relax": r.resultPrice, "rounded_lp": r.resultPriceRound,
                       "lp_time": round(time.time() - t0, 2)}
                print(f"{grp}/{name} (|V|={size}): lp={r.resultPrice:.1f} "
                      f"rounded={r.resultPriceRound:.1f} [{time.time()-t0:.1f}s]", flush=True)
            except Exception as e:
                print(f"{grp}/{name}: FAILED {e!r}", flush=True)
                row = {"group": grp, "name": name, "size": size,
                       "lp_relax": "", "rounded_lp": "", "lp_time": ""}
            w.writerow(row)
            f.flush()
            n += 1
    print(f"\nwrote {n} rows -> {args.out}")


if __name__ == "__main__":
    main()
