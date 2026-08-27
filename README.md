# Optimal-Logistic-Net

Code and data for **logistic transport network flow problems with nonlinear
(vehicle-induced) edge costs and hard storage transshipment capacities**: a
benchmark generator and instance corpus, an exact MILP solver, and a General
Variable Neighborhood Search (GVNS) metaheuristic, plus everything needed to
reproduce the published experiments.

This repository backs two papers:

1. **Benchmark.** V. Kovaleva and A. Ponomarenko. *A Benchmark Generator of
   Realistic Logistic Transport Networks with Nonlinear Edge Costs and
   Transshipment Capacities.* arXiv:2606.20653, 2026. Instance corpus archived
   on Zenodo: [10.5281/zenodo.20372456](https://doi.org/10.5281/zenodo.20372456)
   (CC BY 4.0).
2. **GVNS.** V. Kovaleva and A. Ponomarenko. *A General Variable Neighborhood
   Search for Logistic Network Flow Design with Nonlinear Edge Costs and
   Transshipment Capacities.* Submitted to a Springer LNCS conference volume,
   2026. The `cluster/` pipeline, `exact_solver.py` and `VNS.py` reproduce its
   computational study (Section 6).

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

## 2. Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

The exact-solver study uses **HiGHS 1.14.0** (`highspy`) and, as an independent
cross-check, **SCIP 10.0.2** (`pyscipopt`, which must be built against SCIP
10.0.x — e.g. `conda install -c conda-forge scip=10.0.2 pyscipopt`). See
`requirements.txt` for the full list. The interactive viewer has a lighter
dependency set in `viz_tool/requirements.txt`.

---

## 3. Getting the instance data

The instance corpus is **not stored in this repository** (it is large and lives
on Zenodo). Download it and unpack it into `Generated_Data/`, which every script
expects:

```bash
# from https://doi.org/10.5281/zenodo.20372456
#   -> Generated_Data/Synthetic/<size>_nodes_<i>/
#   -> Generated_Data/Real_Graph/<Country>/
```

| Set | # instances | Sizes (`|V|`) | Source of geometry |
|-----|-------------|---------------|--------------------|
| `Generated_Data/Synthetic`  | 35 | 10, 20, 30, 50, 100, 150 | fully generated |
| `Generated_Data/Real_Graph` | 15 | 11 – 90 | real road graphs (OpenStreetMap) |

Synthetic counts by size: 10×`|V|=10`, 7×20, 7×30, 5×50, 3×100, 3×150.
Real-geometry networks: 9 European countries, 5 U.S. states and European Russia.
Commodity counts range from 67 to over 16,000.

Alternatively, regenerate synthetic instances from scratch (Section 6).

### Instance file format

Each instance is a self-describing directory:

| File | Contents |
|------|----------|
| `graph.graphml`        | undirected weighted graph; node attributes `x`, `y`; edge attribute `weight` (road length) |
| `offices.csv`          | per storage: `office_id`, `transfer_price` (reload cost `f_v`), `transfer_max` (capacity `W_v`) |
| `pos_pop.csv`          | city/storage `x`, `y`, `population` |
| `reqs.csv`             | demand requests `src`, `dst`, `volume`  (origin `s_k`, destination `t_k`, demand `d_k`) |
| `distance_matrix.csv`  | all-pairs shortest road distances |
| `data.txt`             | random seed and every generation parameter (incl. `vehicle_capacity` = `C`) |

```python
import networkx as nx, pandas as pd
inst = "Generated_Data/Synthetic/50_nodes_1"
G        = nx.read_graphml(f"{inst}/graph.graphml")   # nodes carry x, y; edges carry weight
offices  = pd.read_csv(f"{inst}/offices.csv")          # f_v = transfer_price, W_v = transfer_max
requests = pd.read_csv(f"{inst}/reqs.csv")             # s_k, t_k, d_k
params   = dict(line.split(" = ", 1) for line in open(f"{inst}/data.txt") if " = " in line)
C        = float(params["vehicle_capacity"])
```

`Results/` mirrors the instance layout and is committed, so the paper tables can
be regenerated without re-running the cluster (Section 5).

---

## 4. Running the solvers on one instance

**Exact MILP** (arc-based model; reports primal, dual bound, MIP gap, status):

```bash
python exact_solver.py --instance Generated_Data/Synthetic/10_nodes_1 \
    --backend scip --cap 50 --time 600 --gap 0.0     # or --backend highs
```

**GVNS metaheuristic** (stochastic; seed the RNG for reproducibility):

```python
import random
from NetProductPath import NetProducts
from VNS import VNS

random.seed(1)
net = NetProducts(50.0, "Generated_Data/Synthetic/10_nodes_1/")   # cap C = 50
vns = VNS(net)
vns.Solve(20 * 60)                      # time limit in seconds (paper: 2*|V| minutes)
print(vns.result.resultPrice, vns.result.solvingTime)
```

Key modules: `VNS.py` (GVNS + the three neighborhoods), `Solver.py` (HiGHS MILP
and the LP relaxation), `NetProductPath.py` / `ShortestPaths.py` (path model and
reload-aware shortest paths), `exact_solver.py` (the exact study backend).

---

## 5. Reproducing the GVNS paper's tables and figures

`Results/` ships with the committed run outputs, so the **tables regenerate
offline**:

```bash
python cluster/build_table.py            # -> Results/final_per_instance.csv, final_by_size.csv
                                         #    + the LaTeX rows of Table 2 on stdout
python cluster/build_ablation_table.py --n3 single --max-seed 5 \
    --out Results/components_A.csv       # -> Table 3 rows
python cluster/exact_tuning_table.py     # -> Results/exact_tuning.csv (solver-parameter study)
python cluster/plot_results.py           # -> papers/GVNS/figs/{synthetic,real}_ratios.pdf (Fig. 2)
python cluster/plot_solution.py --instance Generated_Data/Real_Graph/Germany \
    --solution Results/Real_Graph/Germany \
    --out papers/GVNS/figs/germany_solution.pdf                              # Fig. 1
```

`build_table.py`, `build_ablation_table.py` and `exact_tuning_table.py` need only
the committed `Results/*.json` and `Results/lp_bounds.csv`; the two plotting
scripts additionally read the instance geometry from `Generated_Data/` (Section 3).
Figures must be copied into `papers/GVNS/arxiv/figs/` by hand, and the arXiv
source is regenerated from the conference one with
`python papers/GVNS/sync_arxiv.py` (`--check` fails if the two have drifted).

---

## 6. Re-running the full study (cluster)

The experiments were run on the HSE *cHARISMa* HPC cluster with SLURM job arrays.
The scripts are repo-root-relative and take the cHARISMa `rocky` partition and
account `proj_1844` — **edit the `#SBATCH --account`/`--partition` lines in
`cluster/*.slurm` for your site**, then:

```bash
# (1) exact dual bounds + incumbents (both backends on every instance)
python cluster/make_manifest.py --sets synthetic real --backends scip highs \
    --highs-max-size 150 \
    --budget 10:1800,20:3600,30:5400,50:7200,100:10800,150:14400 \
    --out cluster/manifest.csv
sbatch --array=1-N%10 cluster/exact_array.slurm cluster/manifest.csv Results/Exact

# (2) multi-seed GVNS (paper uses 10 seeds; budget = 2*|V| minutes)
python cluster/make_gvns_manifest.py --sets synthetic real --seeds 10 \
    --out cluster/gvns_manifest.csv
sbatch --array=1-M%K cluster/gvns_array.slurm cluster/gvns_manifest.csv Results/GVNS

# (3) closed-form LP reference bounds (fast, no cluster needed)
python cluster/lp_bounds_direct.py --sets synthetic real --out Results/lp_bounds.csv

# (4) neighborhood ablation (leave-one-out N1/N2/N3), 5 seeds
python cluster/make_ablation_manifest.py --group synthetic --sizes 20 30 50 \
    --seeds 5 --out cluster/ablation_syn.csv
python cluster/make_ablation_manifest.py --group real --sizes 16 19 24 28 42 49 \
    --per-size 1 --seeds 5 --out cluster/ablation_real.csv
sbatch --array=1-A%K cluster/gvns_array.slurm cluster/ablation_syn.csv  Results/Ablation
sbatch --array=1-B%K cluster/gvns_array.slurm cluster/ablation_real.csv Results/Ablation_real

# (5) search-scheme baseline: basic ("pure") VNS
python cluster/make_baseline_manifest.py --group synthetic --sizes 20 30 50 \
    --variants bvns --seeds 5 --out cluster/baseline_syn.csv
sbatch --array=1-C%K cluster/gvns_array.slurm cluster/baseline_syn.csv Results/Baselines

# (6) exact-solver parameter sensitivity (non-default presets)
python cluster/make_manifest.py --sets synthetic real --backends scip \
    --presets heur emph_feas sepa_aggr --names 30_nodes_1 50_nodes_1 Germany Spain \
    --out cluster/exact_tune_scip.csv
sbatch --array=1-D%12 cluster/exact_array.slurm cluster/exact_tune_scip.csv Results/Exact_tuning
```

`N`, `M`, `A`–`D` are the manifest row counts printed by each `make_*` script;
`%K` caps concurrent array tasks. `run_one.py` / `run_gvns.py` are idempotent — an
existing output JSON is skipped, so a partial array can simply be resubmitted, and
extra seeds are added by re-running with a larger `--seeds`. `cluster/aggregate.py`
gives a per-size summary of the exact solves. Then rebuild the tables and figures
as in Section 5.

**N3 configuration.** `--n3 single` (the default) is the rule the paper reports:
N3 avoids only the most congested storage. `--n3 sweep` avoids a whole prefix of
`|V|/5`–`|V|/4` congested storages; both were run over the full benchmark with ten
seeds and are indistinguishable overall (44 of 50 instances within across-seed
noise, `cluster/compare_configs.py`), but `sweep` loses N3's benefit on the
capacity-tight networks. Send the two configurations to different output
directories — the job tags are identical.

### Generating fresh synthetic instances

`Generator.py` builds an instance from a target storage count via a five-stage
pipeline: (1) Zipf-distributed city sizes, (2) clustered spatial layout and
greedy storage selection, (3) topology from a spatial-network budget model
(minimum spanning tree + simulated-annealing edge addition under a budget),
(4) capacities from population and betweenness centrality with economies-of-scale
reload costs, and (5) demand from a doubly constrained gravity model. Every
parameter and the random seed are written to `data.txt`, so each instance
regenerates exactly. See `main.py` (`GenerateGraphs`) for entry points.

---

## 7. Interactive viewer

`viz_tool/` is a Streamlit/Plotly app that draws any instance on its geographic
layout (node size = capacity, edge width = vehicle load, node colour =
congestion) and supports per-commodity path inspection.

```bash
pip install -r viz_tool/requirements.txt
streamlit run viz_tool/app.py
```

---

## 8. Citation

**Benchmark generator and dataset** (`CITATION.cff` carries the machine-readable
form):

```bibtex
@article{kovaleva2026benchmark,
  author  = {Kovaleva, Varvara and Ponomarenko, Alexander},
  title   = {A Benchmark Generator of Realistic Logistic Transport Networks
             with Nonlinear Edge Costs and Transshipment Capacities},
  journal = {arXiv preprint arXiv:2606.20653},
  year    = {2026},
  note    = {Dataset: \url{https://doi.org/10.5281/zenodo.20372456}}
}
```

**GVNS solver** (this repository's algorithm and experiments):

```bibtex
@inproceedings{kovaleva2026gvns,
  author    = {Kovaleva, Varvara and Ponomarenko, Alexander},
  title     = {A General Variable Neighborhood Search for Logistic Network Flow
               Design with Nonlinear Edge Costs and Transshipment Capacities},
  booktitle = {Lecture Notes in Computer Science},
  publisher = {Springer},
  year      = {2026},
  note      = {To appear}
}
```

---

## 9. License

* **Source code** (`*.py`, `cluster/`, `viz_tool/`): MIT License — see
  [`LICENSE`](LICENSE).
* **Data** (`Generated_Data/`, `Results/` and their archives): Creative Commons
  Attribution 4.0 International (CC BY 4.0) — see
  [`LICENSE-DATA.txt`](LICENSE-DATA.txt).
