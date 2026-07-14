# Optimal-Logistic-Net

A benchmark generator and instance corpus for **logistic transport network flow
problems with nonlinear (vehicle-induced) edge costs and hard storage
transshipment capacities**, together with the code used to generate, solve and
visualise the instances.

This repository accompanies the paper:

> V. Kovaleva and A. Ponomarenko. *A Benchmark Generator of Realistic Logistic
> Transport Networks with Nonlinear Edge Costs and Transshipment Capacities.*
> HSE University, Laboratory of Algorithms and Technologies for Network
> Analysis, Nizhny Novgorod, 2026.

---

## 1. The problem

Multiple commodities must be routed through a network of storages so as to
minimise the joint cost of (a) moving vehicles along roads and (b) reloading
(transshipping) goods at intermediate storages. Two features make instances
realistic and hard:

* **Nonlinear edge cost** — freight travels in fixed-capacity vehicles, so the
  billed quantity on an edge is the *integer number of vehicles*, i.e. the
  carried volume rounded up to the vehicle capacity `C`.
* **Storage transshipment capacity** — each storage `v` has a hard upper bound
  `W_v` on the volume that may be unloaded/stored/reloaded there, and a per-unit
  reload cost `f_v`.

The resulting model is a mixed-integer linear program (MILP); it is NP-hard.

---

## 2. The benchmark corpus

| Set | # instances | Sizes (`|V|`) | Source of geometry |
|-----|-------------|---------------|--------------------|
| `Generated_Data/Synthetic`  | 35 | 10, 20, 30, 50, 100, 150 | fully generated |
| `Generated_Data/Real_Graph` | 15 | 11 – 90 | real road graphs (OpenStreetMap) |

Synthetic counts by size: 10×`|V|=10`, 7×20, 7×30, 5×50, 3×100, 3×150.
Real-geometry networks: 9 European countries, 5 U.S. states and European Russia.
Commodity counts range from 67 to over 16,000.

The empirical analysis in the paper (degree, diameter, edge-length, rank–size
and demand statistics, plus two-sample Kolmogorov–Smirnov tests) shows the
synthetic instances are structurally consistent with the real-geometry ones.

---

## 3. Instance file format

Each instance is a self-describing directory:

| File | Contents |
|------|----------|
| `graph.graphml`        | undirected weighted graph; node attributes `x`, `y`; edge attribute `weight` (road length) |
| `offices.csv`          | per storage: `office_id`, `transfer_price` (reload cost `f_v`), `transfer_max` (capacity `W_v`) |
| `pos_pop.csv`          | city/storage `x`, `y`, `population` |
| `reqs.csv`             | demand requests `src`, `dst`, `volume`  (origin `s_k`, destination `t_k`, demand `d_k`) |
| `distance_matrix.csv`  | all-pairs shortest road distances |
| `data.txt`             | random seed and every generation parameter (incl. `vehicle_capacity` = `C`) |

`Results/` mirrors the instance layout and stores the computational results.

### Loading an instance (Python)

```python
import networkx as nx
import pandas as pd

inst = "Generated_Data/Synthetic/50_nodes_1"
G        = nx.read_graphml(f"{inst}/graph.graphml")   # nodes carry x, y; edges carry weight
offices  = pd.read_csv(f"{inst}/offices.csv")          # f_v = transfer_price, W_v = transfer_max
requests = pd.read_csv(f"{inst}/reqs.csv")             # s_k, t_k, d_k
params   = dict(line.split(" = ", 1) for line in open(f"{inst}/data.txt") if " = " in line)
C        = float(params["vehicle_capacity"])           # vehicle capacity
```

---

## 4. Generating new instances

`Generator.py` builds an instance from a target number of storages `k` using a
five-stage pipeline: (1) Zipf-distributed city sizes, (2) clustered spatial
layout and greedy storage selection, (3) topology via a spatial-network budget
model (minimum spanning tree + simulated-annealing edge addition under a
budget), (4) capacities from population and betweenness centrality with reload
costs reflecting economies of scale, and (5) demand from a doubly constrained
gravity model. Every parameter and the random seed are written to `data.txt`, so
each instance regenerates exactly. See `main.py` for entry points.

---

## 5. Solving and visualising

* Solvers: `Solver.py` (exact MILP via HiGHS, plus the LP relaxation) and
  `VNS.py` (a metaheuristic). `ShortestPaths.py`, `NetProductPath.py`, etc. are
  supporting modules.
* Interactive viewer: `viz_tool/` is a Streamlit/Plotly application that draws
  any instance on its geographic layout (node size = capacity, edge width =
  vehicle load, node colour = congestion) and supports per-commodity path
  inspection.

```bash
pip install -r viz_tool/requirements.txt
streamlit run viz_tool/app.py
```

---

## 6. Reproducibility

Every instance directory contains the random seed and the full parameter set in
`data.txt`; re-running the generator with those values reproduces the instance
(up to the documented random perturbations, which are themselves seeded).

---

## 7. Citation

```bibtex
@inproceedings{kovaleva2026benchmark,
  author    = {Kovaleva, Varvara and Ponomarenko, Alexander},
  title     = {A Benchmark Generator of Realistic Logistic Transport Networks
               with Nonlinear Edge Costs and Transshipment Capacities},
  year      = {2026},
  note      = {Data set archived at <DOI to be assigned>}
}
```

When the corpus is deposited (e.g. on Zenodo), replace `<DOI to be assigned>`
with the minted DOI here and in `LICENSE-DATA.txt`.

---

## 8. License

* **Source code** (`*.py`, `viz_tool/`): MIT License — see [`LICENSE`](LICENSE).
* **Data** (`Generated_Data/`, `Results/` and their archives): Creative Commons
  Attribution 4.0 International (CC BY 4.0) — see
  [`LICENSE-DATA.txt`](LICENSE-DATA.txt).
