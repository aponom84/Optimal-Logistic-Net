"""Build the paper's components table: neighborhood ablation + search-scheme baselines.

Every variant is compared against the *full* GVNS run on the same instances,
same seeds and same budget, using the paper's measure

    increase = min_over_seeds(variant) / min_over_seeds(full GVNS) - 1

averaged (unweighted) over the instances of a group.  The maximum over instances
is reported too, because the prose quotes it.

    python cluster/build_ablation_table.py --full Results/GVNS \
        --ablation Results/Ablation Results/Ablation_real \
        --baselines Results/Baselines --n3 single --max-seed 3

Older result files predate the ``variant``/``n3`` fields; they were all produced
by the published configuration, so a missing field reads as ``gvns`` / ``single``.
"""
import argparse
import collections
import glob
import json
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


def variant_of(r):
    """Label of the algorithmic variant a record belongs to."""
    if (r.get("disable") or "").strip():
        return "N" + r["disable"].strip()          # leave-one-out ablation
    return (r.get("variant") or "gvns").strip()    # search-scheme baseline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", default="Results/GVNS", help="full-GVNS reference dir")
    ap.add_argument("--ablation", nargs="*", default=["Results/Ablation", "Results/Ablation_real"])
    ap.add_argument("--baselines", nargs="*", default=["Results/Baselines"])
    ap.add_argument("--n3", default="single", choices=["sweep", "single"],
                    help="N3 configuration to report (must match --full)")
    ap.add_argument("--max-seed", type=int, default=None,
                    help="use only seeds <= this, so every variant sees the same seeds")
    ap.add_argument("--out", default="Results/components.csv")
    args = ap.parse_args()

    recs = load([args.full]) + load(args.ablation) + load(args.baselines)
    recs = [r for r in recs if (r.get("n3") or "single") == args.n3]
    if args.max_seed:
        recs = [r for r in recs if int(r["seed"]) <= args.max_seed]

    # (group, instance, variant) -> list of records
    by = collections.defaultdict(list)
    for r in recs:
        by[(r.get("group", ""), r["instance"], variant_of(r))].append(r)

    best = {k: min(r["result_price"] for r in v) for k, v in by.items()}
    wall = {k: st.mean(r["wall_time"] for r in v) for k, v in by.items()}
    seeds = {k: len(v) for k, v in by.items()}
    # across-seed spread, used so that differences inside the method's own noise
    # are counted as ties rather than as wins for either side
    noise = {k: (st.pstdev([r["result_price"] for r in v]) /
                 st.mean([r["result_price"] for r in v])) if len(v) > 1 else 0.0
             for k, v in by.items()}

    variants = sorted({k[2] for k in by} - {"gvns"})
    rows = []
    for variant in variants:
        for group in ("synthetic", "real"):
            incs, tratios, n = [], [], 0
            wins = losses = ties = 0   # wins = variant beats the full method
            worst = (None, 0.0)
            for (g, inst, v), b in best.items():
                if v != variant or g != group:
                    continue
                ref = best.get((g, inst, "gvns"))
                if not ref:
                    print(f"  [warn] no full-GVNS reference for {g}/{inst}; skipped")
                    continue
                inc = b / ref - 1.0
                incs.append(inc)
                tratios.append(wall[(g, inst, v)] / wall[(g, inst, "gvns")])
                n += 1
                tol = max(noise[(g, inst, v)], noise[(g, inst, "gvns")])
                if abs(inc) <= tol:
                    ties += 1
                elif inc < 0:
                    wins += 1
                else:
                    losses += 1
                if inc > worst[1]:
                    worst = (inst, inc)
            if not incs:
                continue
            rows.append({"variant": variant, "group": group, "n_instances": n,
                         "n_seeds": min(seeds[k] for k in by if k[2] == variant and k[0] == group),
                         "mean_increase": st.mean(incs), "median_increase": st.median(incs),
                         "max_increase": max(incs), "min_increase": min(incs),
                         "argmax_instance": worst[0],
                         "variant_wins": wins, "variant_losses": losses, "ties": ties,
                         "time_ratio": st.mean(tratios)})

    out = args.out if os.path.isabs(args.out) else os.path.join(REPO, args.out)
    import csv as _csv
    with open(out, "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["variant"])
        w.writeheader()
        w.writerows(rows)

    print(f"\nn3={args.n3}   seeds<= {args.max_seed or 'all'}   -> {out}\n")
    print(f"{'variant':10s} {'group':10s} {'inst':>4s} {'seeds':>5s} "
          f"{'mean':>8s} {'median':>8s} {'min':>8s} {'max':>8s} {'w/l/t':>9s} {'t/t_GVNS':>9s}")
    for r in rows:
        wlt = f"{r['variant_wins']}/{r['variant_losses']}/{r['ties']}"
        print(f"{r['variant']:10s} {r['group']:10s} {r['n_instances']:>4d} {r['n_seeds']:>5d} "
              f"{r['mean_increase']:>+7.2%} {r['median_increase']:>+7.2%} "
              f"{r['min_increase']:>+7.2%} {r['max_increase']:>+7.2%} {wlt:>9s} "
              f"{r['time_ratio']:>9.2f}")
    print("\n  mean/median/min/max: objective increase of the variant over the full GVNS")
    print("  w/l/t: instances where the VARIANT is better / worse / within across-seed noise")

    # LaTeX rows: variant & synthetic & real & time ratio
    print("\n% --- LaTeX rows: variant & synthetic & real & t/t_GVNS ---")
    pct, endrow = "\\%", " \\\\"
    for variant in variants:
        cell = {r["group"]: r for r in rows if r["variant"] == variant}
        def f(g):
            return (f"${cell[g]['mean_increase']:+.1%}$".replace("%", pct)) if g in cell else "--"
        tr = st.mean([cell[g]["time_ratio"] for g in cell]) if cell else 0.0
        print(f"{variant} & {f('synthetic')} & {f('real')} & {tr:.2f}{endrow}")


if __name__ == "__main__":
    main()
