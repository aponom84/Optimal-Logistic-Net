"""Data loading and analytics for the logistics-network solution viewer.

The optimization problem (Kovaleva, master's thesis): a capacitated
multi-commodity flow problem on a directed graph of warehouses.

  minimize   sum_e  c_e * y_e            (transport: edge cost x #vehicles)
           + sum_k sum_{v transit} f_v * x      (transfer/overload at transit nodes)

  s.t. demand satisfied per commodity k
       sum of flow on edge e  <=  C * y_e        (vehicle capacity)
       transit flow through v  <=  W_v           (warehouse overload limit)

Inputs (Generated_Data/.../<instance>/):
  offices.csv          office_id, transfer_price (f_v), transfer_max (W_v)
  reqs.csv             src, dst, volume (demand d_k)
  distance_matrix.csv  src, dst, price (edge cost c_e)
  pos_pop.csv          x, y, population  (row index == node id)
  data.txt            generation parameters incl. vehicle_capacity (C)

Solution (Results/.../<instance>/):
  result.csv           src, dst, volume, path_nodes  (path-flow decomposition)
  EdgeVehicleCount.csv  edge_src, edge_dst, vehicle (y_e)
  data.txt            result/optimal/init price, solving time
"""

from __future__ import annotations

import ast
import math
import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Real_Graph node coordinates are stored as Web Mercator (EPSG:3857) in
# kilometers. Synthetic coordinates are arbitrary planar numbers of a similar
# magnitude and have no geographic meaning.
_EARTH_R_KM = 6378.137


def webmerc_km_to_lonlat(x_km, y_km):
    """Invert Web-Mercator-in-km back to (lon, lat) degrees."""
    x = np.asarray(x_km, dtype=float)
    y = np.asarray(y_km, dtype=float)
    lon = x / _EARTH_R_KM * 180.0 / math.pi
    lat = (2.0 * np.arctan(np.exp(y / _EARTH_R_KM)) - math.pi / 2.0) * 180.0 / math.pi
    return lon, lat


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------
@dataclass
class InstanceRef:
    category: str        # "Synthetic" | "Real_Graph"
    name: str            # e.g. "10_nodes_1" or "Belgium"
    results_dir: str
    data_dir: str

    @property
    def label(self) -> str:
        return f"{self.category} / {self.name}"


def discover_instances(root: str) -> list[InstanceRef]:
    """Find every instance that has both a result and its generated data."""
    results_root = os.path.join(root, "Results")
    data_root = os.path.join(root, "Generated_Data")
    found: list[InstanceRef] = []
    if not os.path.isdir(results_root):
        return found
    for category in sorted(os.listdir(results_root)):
        cat_dir = os.path.join(results_root, category)
        if not os.path.isdir(cat_dir):
            continue
        for name in sorted(os.listdir(cat_dir)):
            res_dir = os.path.join(cat_dir, name)
            data_dir = os.path.join(data_root, category, name)
            if not os.path.isdir(res_dir):
                continue
            if not os.path.isfile(os.path.join(res_dir, "result.csv")):
                continue
            if not os.path.isdir(data_dir):
                continue
            found.append(InstanceRef(category, name, res_dir, data_dir))
    return found


def _parse_data_txt(path: str) -> dict:
    out: dict = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            try:
                out[key] = ast.literal_eval(val)
            except (ValueError, SyntaxError):
                # Handle things like "(0, np.float64(1.0))" or plain strings.
                try:
                    out[key] = float(val)
                except ValueError:
                    out[key] = val
    return out


# --------------------------------------------------------------------------
# Loaded instance + analytics
# --------------------------------------------------------------------------
@dataclass
class Solution:
    ref: InstanceRef

    # raw tables
    offices: pd.DataFrame          # node, transfer_price, transfer_max
    reqs: pd.DataFrame             # src, dst, demand
    coords: pd.DataFrame           # node, x, y, population
    edges: pd.DataFrame            # src, dst, price
    result: pd.DataFrame           # src, dst, volume, path, n_transfers, n_hops, distance
    edge_vehicles: pd.DataFrame    # src, dst, vehicle

    vehicle_capacity: float          # capacity used for utilization (effective)
    gen_capacity: float              # capacity recorded in generation data.txt
    gen_params: dict
    result_meta: dict
    is_geographic: bool = False      # True for Real_Graph (coords are geo)
    capacity_inferred: bool = False  # True if effective capacity was auto-detected

    # derived tables (filled in __post_init__)
    edge_flow: pd.DataFrame = field(default=None)        # src,dst,flow,vehicle,capacity,utilization,price
    node_stats: pd.DataFrame = field(default=None)       # per-node throughput / overload
    commodities: pd.DataFrame = field(default=None)      # per (src,dst) aggregate
    cost: dict = field(default_factory=dict)

    # fast lookups
    _edge_price: dict = field(default_factory=dict)
    _coord: dict = field(default_factory=dict)

    def __post_init__(self):
        self._edge_price = {
            (int(r.src), int(r.dst)): float(r.price)
            for r in self.edges.itertuples(index=False)
        }
        self._coord = {
            int(r.node): (float(r.x), float(r.y))
            for r in self.coords.itertuples(index=False)
        }
        if self.is_geographic:
            lon, lat = webmerc_km_to_lonlat(self.coords["x"], self.coords["y"])
            self.coords = self.coords.assign(lon=lon, lat=lat)
            self._lonlat = {
                int(n): (float(lo), float(la))
                for n, lo, la in zip(self.coords["node"], lon, lat)
            }
        else:
            self._lonlat = {}
        self._compute_paths()
        if self.vehicle_capacity is None:
            self.vehicle_capacity = self._infer_capacity()
            self.capacity_inferred = True
        self._compute_capacity_dependent()

    def set_effective_capacity(self, capacity: float):
        """Recompute capacity-dependent metrics for a user-chosen capacity."""
        self.vehicle_capacity = float(capacity)
        self._compute_capacity_dependent()

    def _infer_capacity(self) -> float:
        """The stored vehicle counts satisfy vehicle ~= floor(flow / C), so on
        loaded edges flow/vehicle clusters at the true capacity C. We take a high
        percentile (robust to floored, near-empty edges) and round to a nice value.
        """
        ef = self._edge_flow_base
        loaded = ef[ef["vehicle"] > 0]
        if len(loaded) == 0:
            return float(self.gen_capacity or 1.0)
        ratio = (loaded["flow"] / loaded["vehicle"]).to_numpy()
        # 99th percentile sits at the true capacity: full edges hit flow/veh == C
        # exactly, while the few floored edges (vehicle truncated to int) form a
        # thin tail above it that p99 trims off.
        est = float(np.percentile(ratio, 99))
        if est >= 20:
            return float(round(est / 5.0) * 5)
        return float(max(1, round(est)))

    # ------------------------------------------------------------------
    @property
    def n_nodes(self) -> int:
        return len(self.offices)

    def path_distance(self, path: list[int]) -> float:
        return float(sum(
            self._edge_price.get((path[i], path[i + 1]), np.nan)
            for i in range(len(path) - 1)
        ))

    # ------------------------------------------------------------------
    def _compute_paths(self):
        """Capacity-independent analytics: per-path enrichment, edge flow base,
        node throughput, per-commodity aggregates, transfer cost."""
        off = self.offices.set_index("node")
        f = off["transfer_price"].to_dict()
        w = off["transfer_max"].to_dict()

        # ---- enrich per-path result rows --------------------------------
        n_transfers, n_hops, dist, transfer_cost_row = [], [], [], []
        edge_flow: dict = {}
        node_transit: dict = {n: 0.0 for n in off.index}
        for row in self.result.itertuples(index=False):
            path = row.path
            vol = float(row.volume)
            hops = len(path) - 1
            transit = path[1:-1]
            n_transfers.append(len(transit))
            n_hops.append(hops)
            dist.append(self.path_distance(path))
            transfer_cost_row.append(vol * sum(f.get(v, 0.0) for v in transit))
            for v in transit:
                node_transit[v] = node_transit.get(v, 0.0) + vol
            for i in range(len(path) - 1):
                e = (path[i], path[i + 1])
                edge_flow[e] = edge_flow.get(e, 0.0) + vol

        self.result = self.result.assign(
            n_transfers=n_transfers,
            n_hops=n_hops,
            distance=dist,
            transfer_cost=transfer_cost_row,
        )

        # ---- edge flow / vehicles (base, no capacity yet) ---------------
        veh = {
            (int(r.src), int(r.dst)): int(r.vehicle)
            for r in self.edge_vehicles.itertuples(index=False)
        }
        all_edges = set(edge_flow) | {e for e, v in veh.items() if v > 0}
        rows = []
        for e in sorted(all_edges):
            v = veh.get(e, 0)
            rows.append({
                "src": e[0], "dst": e[1],
                "flow": edge_flow.get(e, 0.0), "vehicle": v,
                "price": self._edge_price.get(e, np.nan),
                "transport_cost": v * self._edge_price.get(e, 0.0),
            })
        self._edge_flow_base = pd.DataFrame(
            rows, columns=["src", "dst", "flow", "vehicle", "price", "transport_cost"])

        # ---- node throughput / overload ---------------------------------
        out_vol = self.reqs.groupby("src")["demand"].sum().to_dict()
        in_vol = self.reqs.groupby("dst")["demand"].sum().to_dict()
        ef = self._edge_flow_base
        veh_out = ef.groupby("src")["vehicle"].sum().to_dict() if len(ef) else {}
        veh_in = ef.groupby("dst")["vehicle"].sum().to_dict() if len(ef) else {}
        flow_out = ef.groupby("src")["flow"].sum().to_dict() if len(ef) else {}
        flow_in = ef.groupby("dst")["flow"].sum().to_dict() if len(ef) else {}
        nrows = []
        for n in off.index:
            transit = node_transit.get(n, 0.0)
            wmax = w.get(n, np.nan)
            x, y = self._coord.get(n, (np.nan, np.nan))
            lon, lat = self._lonlat.get(n, (np.nan, np.nan))
            pop = self.coords.loc[self.coords.node == n, "population"]
            nrows.append({
                "node": n, "x": x, "y": y, "lon": lon, "lat": lat,
                "population": float(pop.iloc[0]) if len(pop) else np.nan,
                "transfer_price": f.get(n, np.nan),
                "transfer_max": wmax,
                "transit_volume": transit,
                "overload_util": (transit / wmax) if wmax else np.nan,
                "origin_volume": out_vol.get(n, 0.0),
                "dest_volume": in_vol.get(n, 0.0),
                "vehicles_out": int(veh_out.get(n, 0)),
                "vehicles_in": int(veh_in.get(n, 0)),
                "flow_out": flow_out.get(n, 0.0),
                "flow_in": flow_in.get(n, 0.0),
            })
        self.node_stats = pd.DataFrame(nrows)

        # ---- per-commodity aggregate ------------------------------------
        demand = {
            (int(r.src), int(r.dst)): float(r.demand)
            for r in self.reqs.itertuples(index=False)
        }
        crows = []
        for (s, d), g in self.result.groupby(["src", "dst"]):
            vol = g["volume"].sum()
            w_tr = np.average(g["n_transfers"], weights=g["volume"]) if vol > 0 else 0
            w_hop = np.average(g["n_hops"], weights=g["volume"]) if vol > 0 else 0
            w_dist = np.average(g["distance"], weights=g["volume"]) if vol > 0 else 0
            direct_vol = g.loc[g["n_transfers"] == 0, "volume"].sum()
            direct_dist = self._edge_price.get((int(s), int(d)), np.nan)
            crows.append({
                "src": int(s), "dst": int(d),
                "demand": demand.get((int(s), int(d)), vol),
                "delivered": vol,
                "n_paths": len(g),
                "avg_transfers": w_tr,
                "max_transfers": int(g["n_transfers"].max()),
                "avg_hops": w_hop,
                "avg_distance": w_dist,
                "direct_distance": direct_dist,
                "detour": (w_dist / direct_dist) if direct_dist and direct_dist > 0 else np.nan,
                "direct_volume": direct_vol,
                "direct_share": (direct_vol / vol) if vol > 0 else np.nan,
                "transfer_cost": g["transfer_cost"].sum(),
            })
        self.commodities = pd.DataFrame(crows)

        # ---- cost breakdown (capacity-independent) ----------------------
        base = self._edge_flow_base
        transport = float(base["transport_cost"].sum()) if len(base) else 0.0
        transfer = float(self.result["transfer_cost"].sum())
        total = transport + transfer
        self.cost = {
            "transport": transport,
            "transfer": transfer,
            "total": total,
            "transport_share": transport / total if total else np.nan,
            "transfer_share": transfer / total if total else np.nan,
        }

    def _compute_capacity_dependent(self):
        """Build edge_flow with capacity / utilization for current capacity C."""
        C = self.vehicle_capacity
        ef = self._edge_flow_base.copy()
        cap = C * ef["vehicle"]
        ef["capacity"] = cap
        ef["utilization"] = np.where(cap > 0, ef["flow"] / cap, np.nan)
        ef["min_vehicles"] = np.ceil(ef["flow"] / C).astype(int)
        self.edge_flow = ef


def _read_csv_flexible(path: str, **kw) -> pd.DataFrame:
    return pd.read_csv(path, **kw)


def load_solution(ref: InstanceRef) -> Solution:
    d, r = ref.data_dir, ref.results_dir

    offices = _read_csv_flexible(os.path.join(d, "offices.csv"))
    offices = offices.rename(columns={"office_id": "node"})[
        ["node", "transfer_price", "transfer_max"]
    ]
    offices["node"] = offices["node"].astype(int)

    reqs = _read_csv_flexible(os.path.join(d, "reqs.csv"))
    reqs = reqs.rename(columns={"volume": "demand"})
    reqs["src"] = reqs["src"].astype(int)
    reqs["dst"] = reqs["dst"].astype(int)

    pos = _read_csv_flexible(os.path.join(d, "pos_pop.csv"))
    pos = pos.reset_index().rename(columns={"index": "node"})
    coords = pos[["node", "x", "y", "population"]].copy()

    edges = _read_csv_flexible(os.path.join(d, "distance_matrix.csv"),
                               usecols=["src", "dst", "price"])
    edges = edges[(edges["src"] != edges["dst"]) & (edges["price"] > 0)].copy()
    edges["src"] = edges["src"].astype(int)
    edges["dst"] = edges["dst"].astype(int)

    result = _read_csv_flexible(os.path.join(r, "result.csv"))
    result["src"] = result["src"].astype(int)
    result["dst"] = result["dst"].astype(int)
    result["path"] = result["path_nodes"].apply(
        lambda s: [int(x) for x in ast.literal_eval(s)]
    )
    result = result[["src", "dst", "volume", "path"]]

    ev_path = os.path.join(r, "EdgeVehicleCount.csv")
    if os.path.isfile(ev_path):
        ev = _read_csv_flexible(ev_path)
        ev = ev.rename(columns={"edge_src": "src", "edge_dst": "dst"})
        ev["src"] = ev["src"].astype(int)
        ev["dst"] = ev["dst"].astype(int)
    else:
        ev = pd.DataFrame(columns=["src", "dst", "vehicle"])

    gen_params = _parse_data_txt(os.path.join(d, "data.txt"))
    result_meta = _parse_data_txt(os.path.join(r, "data.txt"))

    gen_cap = gen_params.get("vehicle_capacity")
    gen_cap = float(gen_cap) if gen_cap is not None else 20.0

    return Solution(
        ref=ref,
        offices=offices,
        reqs=reqs,
        coords=coords,
        edges=edges,
        result=result,
        edge_vehicles=ev,
        vehicle_capacity=None,        # None -> auto-infer effective capacity
        gen_capacity=gen_cap,
        gen_params=gen_params,
        result_meta=result_meta,
        is_geographic=(ref.category == "Real_Graph"),
    )
