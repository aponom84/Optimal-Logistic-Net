"""Collect per-job JSON results from the exact study into a tidy CSV + summary.

    python cluster/aggregate.py --in Results/Exact --out Results/exact_results.csv

Produces one row per (instance, backend) and prints a per-size summary: how many
instances were solved to proven optimality, and the mean remaining MIP gap.
"""
import argparse
import csv
import glob
import json
import math
import os

COLS = ["group", "size", "instance", "backend", "preset", "status", "proven_optimal",
        "primal_bound", "dual_bound", "gap", "solve_time", "wall_time",
        "nodes", "n_int_vars", "n_cont_vars", "n_constraints",
        "time_limit", "gap_tol", "threads", "ok", "error"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", default="Results/Exact")
    ap.add_argument("--out", default="Results/exact_results.csv")
    args = ap.parse_args()

    recs = []
    for path in sorted(glob.glob(os.path.join(args.indir, "*.json"))):
        with open(path) as f:
            recs.append(json.load(f))
    if not recs:
        print(f"no JSON results under {args.indir}")
        return

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        for r in recs:
            w.writerow({c: r.get(c, "") for c in COLS})
    print(f"wrote {len(recs)} rows -> {args.out}\n")

    # per-size, per-backend summary
    backends = sorted({r.get("backend", "") for r in recs})
    sizes = sorted({int(r.get("size", 0)) for r in recs})
    print(f"{'size':>5} {'backend':>7} {'n':>3} {'proven':>7} {'mean gap':>9} "
          f"{'mean dual':>12} {'mean primal':>12} {'mean t(s)':>9}")
    for s in sizes:
        for b in backends:
            sub = [r for r in recs if int(r.get("size", 0)) == s
                   and r.get("backend") == b and r.get("ok", False)]
            if not sub:
                continue
            n = len(sub)
            proven = sum(1 for r in sub if r.get("proven_optimal"))
            gaps = [r["gap"] for r in sub if isinstance(r.get("gap"), (int, float))
                    and math.isfinite(r["gap"])]
            duals = [r["dual_bound"] for r in sub if isinstance(r.get("dual_bound"), (int, float))
                     and math.isfinite(r["dual_bound"])]
            prims = [r["primal_bound"] for r in sub if isinstance(r.get("primal_bound"), (int, float))
                     and math.isfinite(r["primal_bound"])]
            times = [r.get("solve_time", 0) for r in sub]
            mg = f"{sum(gaps)/len(gaps):.3%}" if gaps else "-"
            md = f"{sum(duals)/len(duals):.1f}" if duals else "-"
            mp = f"{sum(prims)/len(prims):.1f}" if prims else "-"
            mt = f"{sum(times)/len(times):.0f}"
            print(f"{s:>5} {b:>7} {n:>3} {proven:>3}/{n:<3} {mg:>9} {md:>12} {mp:>12} {mt:>9}")

    fails = [r for r in recs if not r.get("ok", False)]
    if fails:
        print(f"\n{len(fails)} FAILED job(s):")
        for r in fails:
            print(f"  {r.get('instance')}/{r.get('backend')}: {r.get('error','')[:120]}")


if __name__ == "__main__":
    main()
