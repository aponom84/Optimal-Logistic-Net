"""Build a manifest for the neighborhood ablation (leave-one-out).

For a representative subset of instances we run GVNS with each single
neighborhood disabled (N1, N2, or N3) over several seeds; the full-GVNS baseline
is reused from the main run (Results/GVNS). The disabling is done in VNS via
`vns.disabled` (skips the neighborhood in both shake and VND).

    python cluster/make_ablation_manifest.py --sizes 20 30 50 --per-size 3 \
        --seeds 3 --out cluster/ablation_manifest.csv
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
    ap.add_argument("--group", default="synthetic", choices=list(SET_DIRS))
    ap.add_argument("--sizes", type=int, nargs="+", default=[20, 30, 50])
    ap.add_argument("--per-size", type=int, default=3, help="instances per size")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--seed0", type=int, default=1)
    ap.add_argument("--disable", nargs="+", default=["1", "2", "3"],
                    help="neighborhoods to leave out, one variant each")
    ap.add_argument("--cap", type=float, default=50)
    ap.add_argument("--minutes-per-size", type=float, default=2.0)
    ap.add_argument("--out", default="cluster/ablation_manifest.csv")
    args = ap.parse_args()

    base = os.path.join(REPO, SET_DIRS[args.group])
    by_size = {}
    for name in sorted(os.listdir(base)):
        folder = os.path.join(base, name)
        if not os.path.isdir(folder) or not os.path.exists(os.path.join(folder, "offices.csv")):
            continue
        s = storages_of(folder)
        if s in args.sizes:
            by_size.setdefault(s, []).append(name)

    rows = []
    for s in args.sizes:
        names = sorted(by_size.get(s, []))[: args.per_size]
        tl = args.minutes_per_size * s * 60
        for name in names:
            for dis in args.disable:
                for seed in range(args.seed0, args.seed0 + args.seeds):
                    rows.append({
                        "tag": f"{args.group}__{name}__d{dis}__seed{seed}",
                        "group": args.group, "name": name, "size": s,
                        "instance_path": os.path.join(SET_DIRS[args.group], name),
                        "seed": seed, "cap": args.cap, "time_limit": tl, "disable": dis,
                    })

    rows.sort(key=lambda r: (r["size"], r["name"], r["disable"], r["seed"]))
    fields = ["tag", "group", "name", "size", "instance_path", "seed", "cap",
              "time_limit", "disable"]
    out = os.path.join(REPO, args.out) if not os.path.isabs(args.out) else args.out
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    total_h = sum(r["time_limit"] for r in rows) / 3600.0
    print(f"wrote {len(rows)} ablation jobs -> {out}")
    print(f"worst-case wall if all hit their limit: {total_h:.1f} job-hours")
    for s in args.sizes:
        n = len([r for r in rows if r["size"] == s])
        print(f"  size {s}: {n} jobs ({len(sorted(by_size.get(s, []))[:args.per_size])} instances)")


if __name__ == "__main__":
    main()
