"""Build a manifest for the search-scheme baselines (review 3, point 3).

The comparison stays *in family*: every baseline is the same code with part of
the search scheme switched off, so it needs no separate description and no
separate tuning.  The one reported in the paper is

    bvns -- "pure" / basic VNS: the same shake over N1..N3, but the local search
            is a single neighborhood (N1) instead of the full VND sweep.

``vnd`` (no shake) and ``rvns`` (no local search) are accepted too; see VARIANTS
in cluster/run_gvns.py.  The full-GVNS reference column costs nothing -- it is
the matching seeds of the main run (Results/GVNS or Results/GVNS_n3sweep).

    python cluster/make_baseline_manifest.py --group synthetic --sizes 20 30 50 \
        --per-size 3 --variants bvns --seeds 5 --n3 sweep \
        --out cluster/baseline_syn.csv
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
    ap.add_argument("--names", nargs="*", default=None,
                    help="restrict to these instance names (default: all in --sizes)")
    ap.add_argument("--variants", nargs="+", default=["bvns"],
                    choices=["bvns", "vnd", "rvns"])
    ap.add_argument("--n3", nargs="+", default=["single"], choices=["single", "sweep"],
                    help="N3 configuration(s); each must match a full-GVNS run")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--seed0", type=int, default=1)
    ap.add_argument("--cap", type=float, default=50)
    ap.add_argument("--minutes-per-size", type=float, default=2.0)
    ap.add_argument("--out", default="cluster/baseline_manifest.csv")
    args = ap.parse_args()

    base = os.path.join(REPO, SET_DIRS[args.group])
    by_size = {}
    for name in sorted(os.listdir(base)):
        folder = os.path.join(base, name)
        if not os.path.isdir(folder) or not os.path.exists(os.path.join(folder, "offices.csv")):
            continue
        if args.names and name not in args.names:
            continue
        s = storages_of(folder)
        if s in args.sizes:
            by_size.setdefault(s, []).append(name)

    rows = []
    for s in args.sizes:
        names = sorted(by_size.get(s, []))[: args.per_size]
        tl = args.minutes_per_size * s * 60
        for name in names:
            for variant in args.variants:
                for n3 in args.n3:
                    for seed in range(args.seed0, args.seed0 + args.seeds):
                        rows.append({
                            "tag": f"{args.group}__{name}__{variant}__{n3}__seed{seed}",
                            "group": args.group, "name": name, "size": s,
                            "instance_path": os.path.join(SET_DIRS[args.group], name),
                            "seed": seed, "cap": args.cap, "time_limit": tl,
                            "disable": "", "variant": variant, "n3": n3,
                        })

    rows.sort(key=lambda r: (r["size"], r["name"], r["variant"], r["n3"], r["seed"]))
    fields = ["tag", "group", "name", "size", "instance_path", "seed", "cap",
              "time_limit", "disable", "variant", "n3"]
    out = os.path.join(REPO, args.out) if not os.path.isabs(args.out) else args.out
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    total_h = sum(r["time_limit"] for r in rows) / 3600.0
    print(f"wrote {len(rows)} baseline jobs "
          f"({'+'.join(args.variants)}, n3={'+'.join(args.n3)}) -> {out}")
    print(f"worst-case wall if all hit their limit: {total_h:.1f} job-hours")
    for s in args.sizes:
        n = len([r for r in rows if r["size"] == s])
        print(f"  size {s}: {n} jobs ({len(sorted(by_size.get(s, []))[:args.per_size])} instances)")


if __name__ == "__main__":
    main()
