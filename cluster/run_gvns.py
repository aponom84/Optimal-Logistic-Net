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
    print(f"[run] tag={row['tag']} seed={seed} time_limit={time_limit}s")

    t0 = time.time()
    try:
        net = NetProducts(float(row["cap"]), row["instance_path"] + "/")
        vns = VNS(net)
        vns.Solve(time_limit)
        rec = {
            "instance": row["name"], "group": row.get("group", ""),
            "size": int(row.get("size", net.storageCount)), "seed": seed,
            "result_price": vns.result.resultPrice,
            "init_price": vns.initRes,
            "solving_time": vns.result.solvingTime,
            "time_limit": time_limit, "ok": True,
        }
    except Exception as e:
        rec = {"instance": row.get("name", ""), "group": row.get("group", ""),
               "size": int(row.get("size", 0)), "seed": seed, "ok": False,
               "error": repr(e), "traceback": traceback.format_exc(),
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
