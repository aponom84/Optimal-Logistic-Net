"""Exact arc-based MILP solver with dual-bound and MIP-gap reporting.

This mirrors the arc-based formulation of ``Solver.SolveMIP_HIGHS_Edge`` -- the
"exact" baseline in the GVNS paper -- but is built for a rigorous exact study:

  * choose the backend: SCIP (via ``pyscipopt``) or HiGHS (via ``highspy``);
  * choose a parameter ``preset``: ``default`` leaves every solver option at its
    factory setting (only the time limit, gap target and thread count are set),
    which is what the paper's main tables use; the other presets exist for the
    parameter-sensitivity study of Sec. 5.1;
  * run to *proven* optimality (``gap=0``) or under a wall-clock budget;
  * return the primal bound, the **dual (lower) bound**, the MIP gap, the
    solver status, node count and solve time.

The single source of truth for the model is :func:`build_scip_model`.  For the
HiGHS backend the same model is exported to MPS -- SCIP's writer emits explicit
variable bounds, which avoids the classic MPS integer-default pitfall -- and
re-read by HiGHS, so both solvers see an identical problem.

CLI::

    python exact_solver.py --instance Generated_Data/Synthetic/10_nodes_1 \
        --backend scip --cap 50 --time 600 --gap 0.0
"""
from __future__ import annotations

import argparse
import math
import os
import tempfile
import time as _time
from dataclasses import dataclass, field

from NetProductPath import NetProducts

ROW_FIELDS = [
    "instance", "backend", "preset", "storages", "edges", "commodities",
    "n_int_vars", "n_cont_vars", "n_constraints",
    "status", "proven_optimal", "primal_bound", "dual_bound", "gap",
    "solve_time", "nodes", "time_limit", "gap_tol", "threads",
]

# Parameter presets for the sensitivity study.  ``default`` is deliberately
# empty: the main results use factory settings apart from the limits set below.
SCIP_PRESETS = ("default", "heur", "emph_feas", "sepa_aggr")
HIGHS_PRESETS = {
    "default": {},
    "heur": {"mip_heuristic_effort": 0.5},          # factory default is 0.05
    "presolve_off": {"presolve": "off"},
    "aggressive": {"mip_heuristic_effort": 0.5, "presolve": "on", "parallel": "on"},
}


def _apply_scip_preset(m, preset):
    """Apply a SCIP parameter preset. Called *after* the limits, never before."""
    if preset in ("", "default"):
        return
    from pyscipopt import SCIP_PARAMSETTING, SCIP_PARAMEMPHASIS
    if preset == "heur":
        m.setHeuristics(SCIP_PARAMSETTING.AGGRESSIVE)
    elif preset == "emph_feas":
        m.setEmphasis(SCIP_PARAMEMPHASIS.FEASIBILITY)
    elif preset == "sepa_aggr":
        m.setSeparating(SCIP_PARAMSETTING.AGGRESSIVE)
    else:
        raise ValueError(f"unknown SCIP preset {preset!r}; expected {SCIP_PRESETS}")


def _apply_highs_preset(h, preset):
    """Apply a HiGHS parameter preset. Called *after* the limits, never before."""
    if preset in ("", "default"):
        return
    if preset not in HIGHS_PRESETS:
        raise ValueError(f"unknown HiGHS preset {preset!r}; expected {sorted(HIGHS_PRESETS)}")
    for option, value in HIGHS_PRESETS[preset].items():
        h.setOptionValue(option, value)


@dataclass
class ExactResult:
    instance: str = ""
    backend: str = ""
    preset: str = "default"
    storages: int = 0
    edges: int = 0
    commodities: int = 0
    status: str = "unknown"
    proven_optimal: bool = False
    primal_bound: float = math.inf     # best incumbent objective
    dual_bound: float = -math.inf      # best lower (dual) bound
    gap: float = math.inf              # relative MIP gap (primal-dual)/|primal|
    solve_time: float = 0.0            # solver run time (s)
    nodes: int = 0
    n_int_vars: int = 0
    n_cont_vars: int = 0
    n_constraints: int = 0
    time_limit: float = 0.0
    gap_tol: float = 0.0
    threads: int = 0
    edge_vehicle_count: dict = field(default_factory=dict)

    def to_row(self):
        return {k: getattr(self, k) for k in ROW_FIELDS}


def build_scip_model(net: NetProducts):
    """Build the arc-based MILP in pyscipopt. Returns ``(model, veh_vars)``.

    Faithful to ``Solver.SolveMIP_HIGHS_Edge``:
      * continuous flow ``f[edge, k] in [0, demand_k]`` per commodity/edge;
      * integer vehicle count ``v[edge] >= 0`` per edge;
      * flow conservation per (node, commodity);
      * edge capacity ``sum_k f[edge, k] <= C * v[edge]``;
      * storage transshipment ``sum transit-inflow <= W_v``.
    """
    from pyscipopt import Model

    m = Model("arc_exact")

    flow = {}
    for edge in net.edges:
        for pid, info in net.products.items():
            flow[(edge, pid)] = m.addVar(
                vtype="C", lb=0.0, ub=float(info["demand"]),
                name=f"f_{edge[0]}_{edge[1]}_{pid}")
    veh = {edge: m.addVar(vtype="I", lb=0.0, name=f"v_{edge[0]}_{edge[1]}")
           for edge in net.edges}

    demandExpr = {sid: {pid: 0 for pid in net.productId} for sid in net.storageId}
    edgeExpr = {edge: 0 for edge in net.edges}
    storageExpr = {sid: 0 for sid in net.storageId}
    obj = 0

    for edge in net.edges:
        for pid, info in net.products.items():
            fv = flow[(edge, pid)]
            demandExpr[edge[0]][pid] += fv
            demandExpr[edge[1]][pid] -= fv
            edgeExpr[edge] += fv
            if edge[1] != info["source"] and edge[1] != info["destination"]:
                storageExpr[edge[1]] += fv
                obj += float(net.storages[edge[1]]["overloadPrice"]) * fv

    for edge in net.edges:
        edgeExpr[edge] += -float(net.vehicleCapacity) * veh[edge]
        obj += float(net.edgesPrices[edge]) * veh[edge]

    # (1) demand / flow conservation
    for sid, dExprs in demandExpr.items():
        for pid, dExpr in dExprs.items():
            if isinstance(dExpr, (int, float)):
                continue  # node has no incident edge for this commodity (complete graph: never)
            dem = 0.0
            if sid == net.products[pid]["source"]:
                dem = float(net.products[pid]["demand"])
            if sid == net.products[pid]["destination"]:
                dem = -float(net.products[pid]["demand"])
            m.addCons(dExpr == dem)
    # (2) vehicle capacity on edges
    for edge, eExpr in edgeExpr.items():
        m.addCons(eExpr <= 0)
    # (3) storage transshipment capacity
    for sid, sExpr in storageExpr.items():
        if not isinstance(sExpr, (int, float)):  # some transit flow reaches sid
            m.addCons(sExpr <= float(net.storages[sid]["maxOverload"]))

    m.setObjective(obj, "minimize")
    return m, veh


def _fill_dims(res: ExactResult, net: NetProducts):
    res.storages = net.storageCount
    res.edges = net.edgeCount
    res.commodities = net.productCount
    res.n_cont_vars = net.edgeCount * net.productCount
    res.n_int_vars = net.edgeCount


def _solve_scip(net, time_limit, gap, threads, keep_solution, preset="default"):
    m, veh = build_scip_model(net)
    m.setParam("limits/time", float(time_limit))
    m.setParam("limits/gap", float(gap))
    if threads and threads > 1:
        m.setParam("lp/threads", int(threads))  # B&B is sequential; parallel LP only
    _apply_scip_preset(m, preset)
    m.hideOutput()
    m.optimize()

    r = ExactResult(backend="scip", preset=preset)
    r.status = m.getStatus()
    r.proven_optimal = (r.status == "optimal")
    r.solve_time = m.getSolvingTime()
    r.nodes = m.getNNodes()
    r.dual_bound = m.getDualbound()
    r.n_constraints = m.getNConss()
    if m.getNSols() > 0:
        r.primal_bound = m.getPrimalbound()
        r.gap = m.getGap()
        if keep_solution:
            r.edge_vehicle_count = {e: int(round(m.getVal(v))) for e, v in veh.items()}
    return r


def _solve_highs(net, time_limit, gap, threads, keep_solution, preset="default"):
    import highspy

    m, _ = build_scip_model(net)
    with tempfile.TemporaryDirectory() as td:
        mps = os.path.join(td, "model.mps")
        m.writeProblem(mps)  # SCIP MPS writer emits explicit bounds
        del m

        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("time_limit", float(time_limit))
        h.setOptionValue("mip_rel_gap", float(gap))
        if threads:
            h.setOptionValue("threads", int(threads))
        _apply_highs_preset(h, preset)
        h.readModel(mps)
        h.run()

        info = h.getInfo()
        r = ExactResult(backend="highs", preset=preset)
        try:
            r.status = h.modelStatusToString(h.getModelStatus())
        except Exception:
            r.status = str(h.getModelStatus())
        r.solve_time = h.getRunTime()
        r.nodes = int(getattr(info, "mip_node_count", 0) or 0)
        r.dual_bound = float(getattr(info, "mip_dual_bound", -math.inf))
        r.gap = float(getattr(info, "mip_gap", math.inf))
        r.n_constraints = h.getNumRow()
        # a valid incumbent exists only if the primal solution is feasible
        primal_status = getattr(info, "primal_solution_status", 0)
        if primal_status == 2:  # kSolutionStatusFeasible
            r.primal_bound = h.getObjectiveValue()
        r.proven_optimal = (r.status.lower().startswith("optimal")
                            and float(gap) == 0.0)
    return r


def solve_arc(net: NetProducts, backend="scip", time_limit=3600, gap=0.0,
              threads=1, instance="", keep_solution=True,
              preset="default") -> ExactResult:
    """Solve the arc-based MILP with the chosen backend and report bounds."""
    backend = backend.lower()
    if backend == "scip":
        r = _solve_scip(net, time_limit, gap, threads, keep_solution, preset)
    elif backend in ("highs", "highspy"):
        r = _solve_highs(net, time_limit, gap, threads, keep_solution, preset)
    else:
        raise ValueError(f"unknown backend {backend!r}")
    _fill_dims(r, net)
    r.instance = instance
    r.time_limit = float(time_limit)
    r.gap_tol = float(gap)
    r.threads = int(threads)
    return r


def solve_instance(path, cap, backend="scip", time_limit=3600, gap=0.0,
                   threads=1, keep_solution=True, preset="default") -> ExactResult:
    folder = path if path.endswith("/") else path + "/"
    net = NetProducts(cap, folder)
    name = os.path.basename(os.path.normpath(path))
    return solve_arc(net, backend=backend, time_limit=time_limit, gap=gap,
                     threads=threads, instance=name, keep_solution=keep_solution,
                     preset=preset)


def main():
    ap = argparse.ArgumentParser(description="Exact arc-based MILP solve with dual bounds")
    ap.add_argument("--instance", required=True, help="instance folder")
    ap.add_argument("--backend", default="scip", choices=["scip", "highs"])
    ap.add_argument("--cap", type=float, default=50, help="vehicle capacity")
    ap.add_argument("--time", type=float, default=600, help="time limit (s)")
    ap.add_argument("--gap", type=float, default=0.0, help="relative MIP gap tolerance")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--preset", default="default",
                    help="parameter preset: default | heur | emph_feas | sepa_aggr "
                         "(SCIP) / default | heur | presolve_off | aggressive (HiGHS)")
    args = ap.parse_args()

    t0 = _time.time()
    r = solve_instance(args.instance, args.cap, backend=args.backend,
                       time_limit=args.time, gap=args.gap, threads=args.threads,
                       keep_solution=False, preset=args.preset)
    print(f"instance     {r.instance}")
    print(f"backend      {r.backend}  (preset {r.preset})")
    print(f"size         |V|={r.storages}  |E|={r.edges}  |K|={r.commodities}"
          f"  vars(int/cont)={r.n_int_vars}/{r.n_cont_vars}  cons={r.n_constraints}")
    print(f"status       {r.status}  proven_optimal={r.proven_optimal}")
    print(f"primal       {r.primal_bound}")
    print(f"dual bound   {r.dual_bound}")
    print(f"MIP gap      {r.gap:.4%}" if math.isfinite(r.gap) else "MIP gap      inf")
    print(f"nodes        {r.nodes}")
    print(f"solve time   {r.solve_time:.2f}s   (wall {(_time.time()-t0):.2f}s)")


if __name__ == "__main__":
    main()
