"""Build a manifest of GVNS jobs (one row per instance x seed).

Default per-instance time budget follows the paper: "twice the number of
storages, in minutes" => 2 * size * 60 seconds.

    python cluster/make_gvns_manifest.py --sets synthetic real --seeds 5 \
        --out cluster/gvns_manifest.csv

``--n3`` selects the N3 configuration.  ``single`` (the default) is what the paper
reports: only the most congested storage is avoided.  ``sweep`` avoids a whole
prefix of |V|/5..|V|/4 congested storages; it was measured over the full benchmark
and is not better (see cluster/compare_configs.py).  Send the two configurations to
*different* output directories -- the tags are identical.
"""
import argparse
import csv
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SET_DIRS = {"synthetic": "Generated_Data/Synthetic", "real": "Generated_Data/Real_Graph"}


def storages_of(folder):
    with open(os.path.join(folder, "offices.csv")) as f:
        return sum(1 for _ in f) - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", nargs="+", default=["synthetic", "real"], choices=list(SET_DIRS))
    ap.add_argument("--seeds", type=int, default=5, help="number of seeds per instance")
    ap.add_argument("--seed0", type=int, default=1, help="first seed value")
    ap.add_argument("--sizes", type=int, nargs="*", default=None)
    ap.add_argument("--cap", type=float, default=50)
    ap.add_argument("--minutes-per-size", type=float, default=2.0,
                    help="wall budget = minutes_per_size * size (paper: 2)")
    ap.add_argument("--n3", default="single", choices=["single", "sweep"],
                    help="N3 configuration (see module docstring)")
    ap.add_argument("--variant", default="gvns",
                    choices=["gvns", "bvns", "vnd", "rvns"],
                    help="search scheme; see VARIANTS in cluster/run_gvns.py")
    ap.add_argument("--out", default="cluster/gvns_manifest.csv")
    args = ap.parse_args()

    rows = []
    for grp in args.sets:
        base = os.path.join(REPO, SET_DIRS[grp])
        for name in sorted(os.listdir(base)):
            folder = os.path.join(base, name)
            if not os.path.isdir(folder) or not os.path.exists(os.path.join(folder, "offices.csv")):
                continue
            size = storages_of(folder)
            if args.sizes and size not in args.sizes:
                continue
            tl = args.minutes_per_size * size * 60
            for s in range(args.seed0, args.seed0 + args.seeds):
                rows.append({
                    "tag": f"{grp}__{name}__seed{s}", "group": grp, "name": name,
                    "size": size, "instance_path": os.path.join(SET_DIRS[grp], name),
                    "seed": s, "cap": args.cap, "time_limit": tl,
                    "variant": args.variant, "n3": args.n3,
                })

    rows.sort(key=lambda r: (r["size"], r["group"], r["name"], r["seed"]))
    fields = ["tag", "group", "name", "size", "instance_path", "seed", "cap",
              "time_limit", "variant", "n3"]
    out = os.path.join(REPO, args.out) if not os.path.isabs(args.out) else args.out
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    total_h = sum(r["time_limit"] for r in rows) / 3600.0
    print(f"wrote {len(rows)} GVNS jobs ({args.variant}, n3={args.n3}) -> {out}")
    print(f"worst-case wall if all hit their limit: {total_h:.1f} job-hours")


if __name__ == "__main__":
    main()
