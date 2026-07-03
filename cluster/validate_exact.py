"""Validate exact_solver.py against the paper's existing arc model.

Checks, all fast (LP-level) except two short MILP smoke solves:

  1. model equivalence -- the LP relaxation of the new pyscipopt arc model must
     equal the paper's own LP relaxation (Solver.SolveMIP_HIGHS_Relaxed);
  2. no MPS integer-bound trap -- HiGHS, reading the SCIP-exported MPS, must find
     a *finite feasible* incumbent (if vehicle vars were wrongly capped at [0,1]
     the model would be infeasible), and must report a dual bound;
  3. SCIP reports a dual bound and gap.

NOTE on ordering: the paper's SolveMIP_HIGHS_Relaxed uses PuLP's HiGHS wrapper,
which mutates process-global highspy state; a *native* highspy solve afterward in
the same process can silently no-op.  Irrelevant to the batch study (each solve is
its own process), but here we deliberately run the native-HiGHS check FIRST and the
PuLP-based equivalence check LAST so this script is self-contained and reliable.

Run from repo root:  python cluster/validate_exact.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from NetProductPath import NetProducts
import exact_solver

INSTANCE = "Generated_Data/Synthetic/10_nodes_1/"
CAP = 50
SMOKE_TIME = 30


def lp_relax_scip(net):
    """LP relaxation of the new arc model: relax the integer vehicle vars."""
    m, veh = exact_solver.build_scip_model(net)
    for v in veh.values():
        m.chgVarType(v, "CONTINUOUS")
    m.setParam("limits/gap", 0.0)
    m.hideOutput()
    m.optimize()
    return m.getObjVal()


def main():
    net = NetProducts(CAP, INSTANCE)
    print(f"instance {INSTANCE}  |V|={net.storageCount} |E|={net.edgeCount} |K|={net.productCount}")

    # --- native highspy FIRST (before any PuLP-HiGHS call) ---
    print(f"\n[1] HiGHS MILP smoke via SCIP-MPS ({SMOKE_TIME}s)")
    rh = exact_solver.solve_arc(net, backend="highs", time_limit=SMOKE_TIME, gap=0.0,
                                instance="10_nodes_1", keep_solution=False)
    print(f"    status={rh.status} primal={rh.primal_bound:.3f} dual={rh.dual_bound:.3f} "
          f"gap={rh.gap:.4%} nodes={rh.nodes} t={rh.solve_time:.1f}s")

    print(f"\n[2] SCIP MILP smoke ({SMOKE_TIME}s)")
    rs = exact_solver.solve_arc(net, backend="scip", time_limit=SMOKE_TIME, gap=0.0,
                                instance="10_nodes_1", keep_solution=False)
    print(f"    status={rs.status} primal={rs.primal_bound:.3f} dual={rs.dual_bound:.3f} "
          f"gap={rs.gap:.4%} nodes={rs.nodes} t={rs.solve_time:.1f}s")

    # --- PuLP-HiGHS LP relax LAST (pollutes global highspy state) ---
    from Solver import SolveMIP_HIGHS_Relaxed
    print("\n[3] LP-relaxation equivalence")
    lp_old = SolveMIP_HIGHS_Relaxed(net).resultPrice
    lp_new = lp_relax_scip(net)
    rel = abs(lp_old - lp_new) / max(1.0, abs(lp_old))
    print(f"    paper LP relax  (SolveMIP_HIGHS_Relaxed) = {lp_old:.6f}")
    print(f"    new   LP relax  (build_scip_model)       = {lp_new:.6f}")
    print(f"    relative difference = {rel:.2e}")

    print("\n[checks]")
    ok_equiv = rel < 1e-4
    ok_highs_feasible = math.isfinite(rh.primal_bound)
    ok_bounds = (rs.dual_bound > 0) and (rh.dual_bound > 0)
    ok_consistent = (rs.dual_bound >= lp_old - 1.0) and (rh.dual_bound >= lp_old - 1.0)
    print(f"    model equivalence (LP)        : {'PASS' if ok_equiv else 'FAIL'}")
    print(f"    HiGHS finite incumbent        : {'PASS' if ok_highs_feasible else 'FAIL'} (no [0,1] MPS trap)")
    print(f"    both dual bounds reported     : {'PASS' if ok_bounds else 'FAIL'}")
    print(f"    dual bounds >= LP relaxation  : {'PASS' if ok_consistent else 'FAIL'}")
    print("\nALL PASS" if all([ok_equiv, ok_highs_feasible, ok_bounds, ok_consistent]) else "\nSOME CHECKS FAILED")


if __name__ == "__main__":
    main()
