"""Head-to-head comparison of two GVNS result directories on the same instances.

Used for the pre-registered choice between the two N3 configurations (the
corrected sweep vs. the configuration of arXiv v1), and for any other
paired comparison of two full runs.

    python cluster/compare_configs.py --a Results/GVNS --b Results/GVNS_n3sweep \
        --label-a "N3 single" --label-b "N3 sweep" --max-seed 10

For every instance present in both directories it reports the ratio of B's
best-of-seeds objective to A's (below 1 means B is cheaper), the paired
win/loss/tie counts, and the same broken down by network size.  A tie is a
difference smaller than the pooled across-seed spread of the two runs, so
differences inside the method's own noise are not read as wins.
"""
import argparse
import collections
import glob
import json
import os
import statistics as st

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(d, max_seed=None):
    d = d if os.path.isabs(d) else os.path.join(REPO, d)
    out = collections.defaultdict(list)
    for p in sorted(glob.glob(os.path.join(d, "*.json"))):
        with open(p) as f:
            r = json.load(f)
        if not r.get("ok"):
            continue
        if (r.get("disable") or "").strip() or (r.get("variant") or "gvns") != "gvns":
            continue
        if max_seed and int(r["seed"]) > max_seed:
            continue
        out[(r.get("group", ""), r["instance"], r["size"])].append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="Results/GVNS")
    ap.add_argument("--b", default="Results/GVNS_n3sweep")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--max-seed", type=int, default=None)
    ap.add_argument("--out", default="Results/config_comparison.csv")
    args = ap.parse_args()

    A, B = load(args.a, args.max_seed), load(args.b, args.max_seed)
    shared = sorted(set(A) & set(B), key=lambda k: (k[2], k[0], k[1]))
    if not shared:
        print("no instances present in both directories yet")
        return
    only_a, only_b = sorted(set(A) - set(B)), sorted(set(B) - set(A))
    if only_a or only_b:
        print(f"[note] {len(only_a)} instance(s) only in {args.label_a}, "
              f"{len(only_b)} only in {args.label_b}; comparing the {len(shared)} shared ones\n")

    rows = []
    for key in shared:
        grp, inst, size = key
        pa = [r["result_price"] for r in A[key]]
        pb = [r["result_price"] for r in B[key]]
        best_a, best_b = min(pa), min(pb)
        # pooled noise: the larger of the two across-seed spreads, relative
        noise = max(st.pstdev(pa) / st.mean(pa) if len(pa) > 1 else 0.0,
                    st.pstdev(pb) / st.mean(pb) if len(pb) > 1 else 0.0)
        ratio = best_b / best_a
        if abs(ratio - 1.0) <= noise:
            verdict = "tie"
        else:
            verdict = args.label_b if ratio < 1.0 else args.label_a
        rows.append({"group": grp, "name": inst, "size": size,
                     "n_seeds_a": len(pa), "n_seeds_b": len(pb),
                     "best_a": best_a, "best_b": best_b,
                     "mean_a": st.mean(pa), "mean_b": st.mean(pb),
                     "ratio_b_over_a": ratio, "noise": noise, "better": verdict})

    out = args.out if os.path.isabs(args.out) else os.path.join(REPO, args.out)
    import csv as _csv
    with open(out, "w", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"{args.label_b} relative to {args.label_a}  (ratio < 1 => {args.label_b} cheaper)")
    print(f"{'size':>5} {'n':>3} {'mean ratio':>11} {'best':>11} {'worst':>11}   win/loss/tie")
    for size in sorted({r["size"] for r in rows}):
        sub = [r for r in rows if r["size"] == size]
        rs = [r["ratio_b_over_a"] for r in sub]
        w_ = sum(1 for r in sub if r["better"] == args.label_b)
        l_ = sum(1 for r in sub if r["better"] == args.label_a)
        t_ = sum(1 for r in sub if r["better"] == "tie")
        print(f"{size:>5} {len(sub):>3} {st.mean(rs):>11.5f} {min(rs):>11.5f} {max(rs):>11.5f}"
              f"   {w_}/{l_}/{t_}")

    rs = [r["ratio_b_over_a"] for r in rows]
    w_ = sum(1 for r in rows if r["better"] == args.label_b)
    l_ = sum(1 for r in rows if r["better"] == args.label_a)
    t_ = sum(1 for r in rows if r["better"] == "tie")
    mean_ratio = st.mean(rs)
    print(f"\nOVERALL  n={len(rows)}  mean ratio {mean_ratio:.5f} "
          f"({(mean_ratio - 1) * 100:+.2f}%)  win/loss/tie {w_}/{l_}/{t_}")
    print(f"         median ratio {st.median(rs):.5f}")

    # pre-registered rule: keep A unless B is better by more than 0.5% on average
    if mean_ratio < 0.995:
        print(f"\n=> pre-registered rule: {args.label_b} is more than 0.5% better on average; "
              f"it becomes the headline configuration.")
    elif mean_ratio > 1.005:
        print(f"\n=> pre-registered rule: {args.label_b} is more than 0.5% worse on average; "
              f"{args.label_a} stays the headline configuration.")
    else:
        print(f"\n=> pre-registered rule: the two are within 0.5% of each other; "
              f"{args.label_a} stays the headline configuration for continuity.")
    print(f"   -> {out}")


if __name__ == "__main__":
    main()
