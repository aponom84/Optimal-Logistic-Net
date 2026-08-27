"""Run one GVNS job (instance x seed) from a manifest row; write a JSON result.

GVNS is stochastic (random path choices in ShortestPaths), so the paper needs
several seeds per instance to report mean/std/best.  This is the per-task body
for a SLURM array, mirroring run_one.py.  The in-loop redistribution solver stays
HiGHS (the published algorithm is unchanged); only the seed is controlled.

    python cluster/run_gvns.py --manifest cluster/gvns_manifest.csv --idx $SLURM_ARRAY_TASK_ID
"""
import argparse
import csv
import json
import os
import random
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from NetProductPath import NetProducts
from VNS import VNS

# Search-scheme variants, expressed as flags on the VNS object.  ``gvns`` is the
# published method; ``bvns`` is the "pure VNS" baseline asked for by review 3 --
# the same shake, but the local search is a single neighborhood instead of the
# full VND sweep.  ``vnd`` and ``rvns`` are available but not used in the paper.
VARIANTS = {
    "gvns": dict(shakeNeighborhoods={1, 2, 3}, lsNeighborhoods={1, 2, 3}),
    "bvns": dict(shakeNeighborhoods={1, 2, 3}, lsNeighborhoods={1}),
    "vnd":  dict(shakeNeighborhoods=set(),     lsNeighborhoods={1, 2, 3}),
    "rvns": dict(shakeNeighborhoods={1, 2, 3}, lsNeighborhoods=set()),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--idx", type=int, required=True)
    ap.add_argument("--out-dir", default="Results/GVNS")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    with open(args.manifest) as f:
        rows = list(csv.DictReader(f))
    row = rows[args.idx - 1]

    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, row["tag"] + ".json")
    if os.path.exists(out) and not args.force:
        print(f"[skip] {out} exists")
        return

    seed = int(row["seed"])
    random.seed(seed)
    time_limit = float(row["time_limit"])
    disable = row.get("disable", "").strip()  # e.g. "" (full), "1", "2", "3"
    disabled = {int(x) for x in disable.split("+") if x}
    variant = (row.get("variant", "") or "gvns").strip()
    if variant not in VARIANTS:
        raise SystemExit(f"unknown variant {variant!r}; expected one of {sorted(VARIANTS)}")
    n3 = (row.get("n3", "") or "sweep").strip()
    if n3 not in ("sweep", "single"):
        raise SystemExit(f"unknown n3 mode {n3!r}; expected 'sweep' or 'single'")
    print(f"[run] tag={row['tag']} seed={seed} time_limit={time_limit}s "
          f"variant={variant} n3={n3} disable={disable or 'none'}")

    t0 = time.time()
    try:
        net = NetProducts(float(row["cap"]), row["instance_path"] + "/")
        vns = VNS(net)
        vns.disabled = disabled
        vns.n3sweep = (n3 == "sweep")
        for attr, value in VARIANTS[variant].items():
            setattr(vns, attr, value)
        vns.Solve(time_limit)
        rec = {
            "instance": row["name"], "group": row.get("group", ""),
            "size": int(row.get("size", net.storageCount)), "seed": seed,
            "disable": disable, "variant": variant, "n3": n3,
            "result_price": vns.result.resultPrice,
            "init_price": vns.initRes,
            "solving_time": vns.result.solvingTime,
            "time_limit": time_limit, "ok": True,
        }
    except Exception as e:
        rec = {"instance": row.get("name", ""), "group": row.get("group", ""),
               "size": int(row.get("size", 0)), "seed": seed, "disable": disable,
               "variant": variant, "n3": n3,
               "ok": False, "error": repr(e), "traceback": traceback.format_exc(),
               "time_limit": time_limit}
    rec["wall_time"] = round(time.time() - t0, 2)
    rec["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=2)
    os.replace(tmp, out)
    print(f"[done] {out} ok={rec['ok']} price={rec.get('result_price')} wall={rec['wall_time']}s")


if __name__ == "__main__":
    main()
