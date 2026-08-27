"""Run one exact-solve job from a manifest row and write a JSON result.

Designed to be the body of a SLURM array task: the array index selects the
manifest row.  Idempotent -- if the output JSON already exists it is skipped,
so a crashed/partial array can simply be resubmitted.

    python cluster/run_one.py --manifest cluster/manifest.csv --idx $SLURM_ARRAY_TASK_ID
"""
import argparse
import csv
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import exact_solver


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--idx", type=int, required=True, help="1-based row index (SLURM array id)")
    ap.add_argument("--out-dir", default="Results/Exact")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    with open(args.manifest) as f:
        rows = list(csv.DictReader(f))
    if not (1 <= args.idx <= len(rows)):
        print(f"idx {args.idx} out of range 1..{len(rows)}", file=sys.stderr)
        sys.exit(2)
    row = rows[args.idx - 1]

    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, row["tag"] + ".json")
    if os.path.exists(out) and not args.force:
        print(f"[skip] {out} exists")
        return

    preset = (row.get("preset", "") or "default").strip()
    print(f"[run] idx={args.idx} tag={row['tag']} backend={row['backend']} preset={preset} "
          f"time={row['time_limit']}s gap={row['gap']} threads={row['threads']}")
    t0 = time.time()
    try:
        r = exact_solver.solve_instance(
            row["instance_path"], cap=float(row["cap"]), backend=row["backend"],
            time_limit=float(row["time_limit"]), gap=float(row["gap"]),
            threads=int(row["threads"]), keep_solution=False, preset=preset)
        rec = r.to_row()
        rec["ok"] = True
        rec["group"] = row.get("group", "")
        rec["size"] = int(row.get("size", r.storages))
    except Exception as e:  # keep failures visible in the aggregate
        rec = {"instance": row.get("name", ""), "group": row.get("group", ""),
               "size": int(row.get("size", 0)), "backend": row["backend"],
               "preset": preset, "ok": False, "error": repr(e), "traceback": traceback.format_exc(),
               "time_limit": float(row["time_limit"])}
    rec["wall_time"] = round(time.time() - t0, 2)
    rec["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=2)
    os.replace(tmp, out)
    print(f"[done] {out}  ok={rec['ok']}  wall={rec['wall_time']}s")


if __name__ == "__main__":
    main()
