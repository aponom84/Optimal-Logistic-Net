"""Phase-0 smoke test: confirm the exact-solve pipeline and SCIP both work on the cluster.

Run from the repo root:  python cluster/smoke_test.py
"""
import os
import sys
import time

# make repo-root modules importable regardless of launch directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from NetProductPath import NetProducts
from Solver import SolveMIP_HIGHS_Edge

INSTANCE = "Generated_Data/Synthetic/10_nodes_1/"
CAP = 50

print("=== loading instance", INSTANCE, "===")
net = NetProducts(CAP, INSTANCE)
print(f"storages={net.storageCount} edges={net.edgeCount} products={net.productCount}")

print("=== HiGHS arc-based MILP solve (time limit 60s) ===")
t0 = time.time()
res = SolveMIP_HIGHS_Edge(net, 60)
print(f"objective={res.resultPrice}  solverTime={res.solvingTime:.2f}s  wall={time.time()-t0:.2f}s")

print("=== SCIP availability check (PySCIPOpt) ===")
import pyscipopt

m = pyscipopt.Model()
print("PySCIPOpt / SCIP version:", m.version())
x = m.addVar("x", lb=0, ub=10)
y = m.addVar("y", vtype="I", lb=0)
m.addCons(x + y >= 3.5)
m.setObjective(x + 2 * y, "minimize")
m.hideOutput()
m.optimize()
print("trivial SCIP -> status:", m.getStatus(),
      "obj:", m.getObjVal(), "dualbound:", m.getDualbound())

print("=== SMOKE TEST OK ===")
