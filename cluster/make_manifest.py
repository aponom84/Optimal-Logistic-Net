"""Build a manifest of exact-solve jobs (one row per instance x backend).

Each row becomes one SLURM array task via run_one.py.  Size is read from the
instance's offices.csv (number of storages).  Per-size wall-clock budgets and
which backends to run are policy knobs.

    python cluster/make_manifest.py --sets synthetic real \
        --backends scip highs --highs-max-size 50 \
        --budget 10:600,20:1200,30:1800,50:3600,100:7200,150:10800 \
        --out cluster/manifest.csv
"""
import argparse
import csv
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SET_DIRS = {
    "synthetic": "Generated_Data/Synthetic",
    "real": "Generated_Data/Real_Graph",
}
DEFAULT_BUDGET = {10: 600, 20: 1200, 30: 1800, 50: 3600, 100: 7200, 150: 10800}


def storages_of(folder):
    with open(os.path.join(folder, "offices.csv")) as f:
        return sum(1 for _ in f) - 1  # minus header


def budget_for(size, budget):
    # exact tier if present, else the budget of the nearest tier at or above size
    if size in budget:
        return budget[size]
    above = [s for s in sorted(budget) if s >= size]
    return budget[above[0]] if above else budget[max(budget)]


def parse_budget(s):
    if not s:
        return dict(DEFAULT_BUDGET)
    out = {}
    for part in s.split(","):
        k, v = part.split(":")
        out[int(k)] = int(v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", default=["synthetic", "real"],
                    choices=list(SET_DIRS))
    ap.add_argument("--backends", nargs="+", default=["scip", "highs"])
    ap.add_argument("--highs-max-size", type=int, default=50,
                    help="run HiGHS only on instances up to this size")
    ap.add_argument("--sizes", type=int, nargs="*", default=None,
                    help="restrict to these sizes (e.g. 10 20)")
    ap.add_argument("--budget", type=str, default="",
                    help="comma list size:seconds, e.g. 10:600,20:1200")
    ap.add_argument("--cap", type=float, default=50)
    ap.add_argument("--gap", type=float, default=0.0)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--out", default="cluster/manifest.csv")
    args = ap.parse_args()

    budget = parse_budget(args.budget)
    rows = []
    for grp in args.sets:
        base = os.path.join(REPO, SET_DIRS[grp])
        for name in sorted(os.listdir(base)):
            folder = os.path.join(base, name)
            if not os.path.isdir(folder):
                continue
            if not os.path.exists(os.path.join(folder, "offices.csv")):
                continue
            size = storages_of(folder)
            if args.sizes and size not in args.sizes:
                continue
            tl = budget_for(size, budget)
            for backend in args.backends:
                if backend == "highs" and size > args.highs_max_size:
                    continue
                rows.append({
                    "tag": f"{grp}__{name}__{backend}",
                    "group": grp, "name": name, "size": size,
                    "instance_path": os.path.join(SET_DIRS[grp], name),
                    "backend": backend, "cap": args.cap, "gap": args.gap,
                    "threads": args.threads, "time_limit": tl,
                })

    rows.sort(key=lambda r: (r["size"], r["group"], r["name"], r["backend"]))
    fields = ["tag", "group", "name", "size", "instance_path", "backend",
              "cap", "gap", "threads", "time_limit"]
    out = os.path.join(REPO, args.out) if not os.path.isabs(args.out) else args.out
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    total_h = sum(r["time_limit"] for r in rows) / 3600.0
    print(f"wrote {len(rows)} jobs -> {out}")
    print(f"worst-case core-time if all hit their limit: {total_h:.1f} solver-hours "
          f"(x {args.threads} threads)")
    by_size = {}
    for r in rows:
        by_size.setdefault(r["size"], []).append(r["backend"])
    for s in sorted(by_size):
        print(f"  size {s:>4}: {len(by_size[s])} jobs  ({budget_for(s, budget)}s each)")


if __name__ == "__main__":
    main()
