import math
import os

import networkx as nx
import numpy as np
import pandas as pd
from scipy.spatial import KDTree
from scipy.spatial.distance import cdist
from scipy.stats import truncnorm
from sklearn.datasets import make_blobs
from typing import Optional


class GenerateData:
    def __init__(self, storage_count, random_seed=42):
        self.storage_count = storage_count
        self.random_seed = random_seed
        np.random.seed(random_seed)

        self.cities_count = storage_count * np.random.randint(8, 12)
        self.cities_alpha = np.random.normal(0.97, 0.06)
        self.max_population = np.random.randint(9e4, 11e4) * self.storage_count

        self.dist_between_cites = np.random.uniform(80, 100)
        size = self.dist_between_cites * storage_count ** 0.8
        self.map_size = (0, size + np.random.uniform(-size / 10, size / 10))
        self.cluster_std = self.map_size[1] / 15

        self.lam = min(max(0.05, np.random.normal(0.263, 0.15)), 0.6)
        self.budget = np.random.normal(2.56, 0.6)

        self.pop_gamma = 0.5
        self.between_alpha = 1.2
        self.min_capacity = 100
        self.capacity_scale = 1
        self.capacity_delta = 1
        self.cost_scale = 5e2

        self.od_betta = 1
        std = 2
        mean = 3 + (12 - 3) * (self.storage_count - 10) / (150 - 10)
        a = (3 - mean) / std
        b = (12 - mean) / std
        self.total_flow = truncnorm.rvs(a, b, loc=mean, scale=std)
        self.pop_coeff = 1
        self.count_coeff = 0.75

        self.km_cost = 5
        self.vehicle_capacity = 50


def generate_cities_zipf(M: int, alpha: float = 0.97, max_pop: float = 1e7, sigma: float = 0.1):
    ranks = np.arange(1, M + 1)
    pops = max_pop / (ranks ** alpha)
    pops = pops * np.random.lognormal(mean=0, sigma=sigma, size=M)
    return np.sort(pops)[::-1]


def generate_coord(cities_count, storage_count, cluster_std, map_size, pops):
    coords, cluster = make_blobs(n_samples=cities_count, centers=storage_count, cluster_std=cluster_std, center_box=map_size)
    pops_small = list(pops[storage_count:].copy())
    new_coords = []
    for cluster_i in range(storage_count):
        clust = coords[cluster == cluster_i]
        new_coords.append({"x": clust[0][0], "y": clust[0][1], "population": pops[cluster_i]})
        for coord in clust[1:]:
            rand = np.random.randint(0, len(pops_small))
            new_pop = pops_small[rand]
            pops_small[rand] = pops_small[-1]
            pops_small.pop()
            new_coords.append({"x": coord[0], "y": coord[1], "population": new_pop})
    new_coordsDF = pd.DataFrame(new_coords)
    return new_coordsDF.sort_values(by="population", ascending=False)


def nearest_node(nodes, x, y):
    min_node = nodes[0]
    min_dist = math.dist((nodes[0]["x"], nodes[0]["y"]), (x, y))
    for node in nodes:
        d = math.dist((node["x"], node["y"]), (x, y))
        if min_dist > d:
            min_dist = d
            min_node = node
    return min_node


def cluster_cities_into_storages(new_coords, storage_count, dist_between_cites):
    selected = []
    for _, node in new_coords.iterrows():
        if not selected:
            selected.append(node.copy())
            selected[-1]["population"] = 0
            continue
        dists = [math.dist((node["x"], node["y"]), (sel["x"], sel["y"])) for sel in selected]
        if all(d >= dist_between_cites for d in dists):
            selected.append(node.copy())
            selected[-1]["population"] = 0
        if len(selected) == storage_count:
            break

    for _, node in new_coords.iterrows():
        nearest_node(selected, node["x"], node["y"])["population"] += node["population"]

    final_nodes = pd.DataFrame(selected)
    return final_nodes.sort_values(by="population", ascending=False)


def _is_connected_fast(edges: set, num_nodes: int) -> bool:
    parent = list(range(num_nodes))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i, j in edges:
        union(i, j)
    root = find(0)
    return all(find(v) == root for v in range(num_nodes))


def build_gastner_newman_network(
    coords: np.ndarray,
    lam: float = 0.5,
    budget_factor: Optional[float] = None,
    T_start: float = 1.0,
    T_end: float = 1e-4,
    cooling_rate: float = 0.997,
    max_iter: int = 50_000,
    seed: Optional[int] = None,
) -> nx.Graph:
    rng = np.random.default_rng(seed)
    coords = np.asarray(coords, dtype=float)
    n = len(coords)

    dist_matrix = cdist(coords, coords)
    eff_matrix = lam * np.sqrt(n) * dist_matrix + (1.0 - lam)
    np.fill_diagonal(dist_matrix, np.inf)
    np.fill_diagonal(eff_matrix, np.inf)

    G_full = nx.Graph()
    for i in range(n):
        for j in range(i + 1, n):
            G_full.add_edge(i, j, weight=float(dist_matrix[i, j]))
    mst = nx.minimum_spanning_tree(G_full, weight="weight")
    mst_cost = sum(dist_matrix[u, v] for u, v in mst.edges())

    if budget_factor is None:
        budget_factor = 1.5 + 2.5 * (1.0 - lam)
    budget = budget_factor * mst_cost

    if lam >= 0.5:
        k = max(2, min(4, n - 1))
        tree = KDTree(coords)
        init_edges = set()
        for i in range(n):
            _, idxs = tree.query(coords[i], k=k + 1)
            for j in idxs[1:]:
                init_edges.add(tuple(sorted((i, int(j)))))
        for u, v in mst.edges():
            init_edges.add(tuple(sorted((u, v))))
    else:
        init_edges = set(tuple(sorted(e)) for e in mst.edges())

    def trim_to_budget(edges: set) -> set:
        cost = sum(dist_matrix[i, j] for i, j in edges)
        if cost <= budget:
            return edges
        result = set(edges)
        for e in sorted(edges, key=lambda e: dist_matrix[e[0], e[1]], reverse=True):
            if cost <= budget:
                break
            tmp = result - {e}
            if _is_connected_fast(tmp, n):
                result = tmp
                cost -= dist_matrix[e[0], e[1]]
        return result

    current_edges = trim_to_budget(set(init_edges))

    def network_cost(edges: set) -> float:
        return sum(dist_matrix[i, j] for i, j in edges)

    def mean_vertex_distance(edges: set) -> float:
        G_tmp = nx.Graph()
        G_tmp.add_nodes_from(range(n))
        for i, j in edges:
            G_tmp.add_edge(i, j, weight=eff_matrix[i, j])
        total, count = 0.0, 0
        for src in range(n):
            for tgt, d in nx.single_source_dijkstra_path_length(G_tmp, src, weight="weight").items():
                if tgt > src:
                    total += d
                    count += 1
        return total / count if count > 0 else np.inf

    all_edges = sorted([(i, j) for i in range(n) for j in range(i + 1, n)], key=lambda e: dist_matrix[e[0], e[1]])
    all_dists = np.array([dist_matrix[i, j] for i, j in all_edges])
    add_weights = (all_dists.max() - all_dists + 1e-9) ** (3.0 * lam)
    add_weights /= add_weights.sum()

    current_cost = network_cost(current_edges)
    current_obj = mean_vertex_distance(current_edges)
    best_edges = set(current_edges)
    best_obj = current_obj
    T = T_start

    for _ in range(max_iter):
        p_add = 0.4 + 0.1 * (1.0 - lam)
        p_remove = 0.4 + 0.1 * lam
        action = rng.choice(["add", "remove", "swap"], p=[p_add, p_remove, 1 - p_add - p_remove])

        if action == "add":
            candidates_mask = np.array([e not in current_edges for e in all_edges])
            if not candidates_mask.any():
                continue
            masked_w = add_weights * candidates_mask
            masked_w /= masked_w.sum()
            edge = all_edges[rng.choice(len(all_edges), p=masked_w)]
            new_edges = current_edges | {edge}
            new_cost = current_cost + dist_matrix[edge[0], edge[1]]
            if new_cost > budget:
                T *= cooling_rate
                continue
            new_obj = mean_vertex_distance(new_edges)
            delta = new_obj - current_obj
            if delta < 0 or rng.random() < np.exp(-delta / T):
                current_edges, current_cost, current_obj = new_edges, new_cost, new_obj

        elif action == "remove":
            if not current_edges:
                continue
            cur_list = list(current_edges)
            cur_dists = np.array([dist_matrix[i, j] for i, j in cur_list])
            rem_w = (cur_dists - cur_dists.min() + 1e-9) ** 2 if lam > 0.5 else np.ones(len(cur_list))
            rem_w /= rem_w.sum()
            edge = cur_list[rng.choice(len(cur_list), p=rem_w)]
            new_edges = current_edges - {edge}
            if not _is_connected_fast(new_edges, n):
                T *= cooling_rate
                continue
            new_cost = current_cost - dist_matrix[edge[0], edge[1]]
            new_obj = mean_vertex_distance(new_edges)
            delta = new_obj - current_obj
            if delta < 0 or rng.random() < np.exp(-delta / T):
                current_edges, current_cost, current_obj = new_edges, new_cost, new_obj

        else:
            if not current_edges:
                continue
            cur_list = list(current_edges)
            cur_dists_swap = np.array([dist_matrix[i, j] for i, j in cur_list])
            rem_w = (cur_dists_swap - cur_dists_swap.min() + 1e-9) ** 2
            rem_w /= rem_w.sum()
            rem_edge = cur_list[rng.choice(len(cur_list), p=rem_w)]
            cand_mask = np.array([e not in current_edges and e != rem_edge for e in all_edges])
            if not cand_mask.any():
                continue
            add_w = add_weights * cand_mask
            add_w /= add_w.sum()
            add_edge = all_edges[rng.choice(len(all_edges), p=add_w)]
            new_edges = (current_edges - {rem_edge}) | {add_edge}
            new_cost = current_cost - dist_matrix[rem_edge[0], rem_edge[1]] + dist_matrix[add_edge[0], add_edge[1]]
            if new_cost > budget or not _is_connected_fast(new_edges, n):
                T *= cooling_rate
                continue
            new_obj = mean_vertex_distance(new_edges)
            delta = new_obj - current_obj
            if delta < 0 or rng.random() < np.exp(-delta / T):
                current_edges, current_cost, current_obj = new_edges, new_cost, new_obj

        if current_obj < best_obj:
            best_obj = current_obj
            best_edges = set(current_edges)

        T *= cooling_rate
        if T < T_end:
            break

    G = nx.Graph()
    for i in range(n):
        G.add_node(i, x=coords[i, 0], y=coords[i, 1])
    for i, j in best_edges:
        G.add_edge(i, j, weight=float(dist_matrix[i, j]))
    return G


def compute_vertex_capacity(pops: np.ndarray, G: nx.Graph, gamma: float = 1.0, alpha: float = 1.2, min_capacity: float = 100.0, scale: float = 0.0002):
    N = len(pops)
    betweenness = nx.betweenness_centrality(G, weight='weight', normalized=True)
    b_values = np.array([betweenness[i] for i in range(N)])
    b_norm = (b_values - b_values.min()) / (b_values.max() - b_values.min() + 1e-8)
    capacity = scale * (pops ** gamma) * (1.0 + alpha * b_norm)
    capacity.sort()
    ind = round(N * 0.1) - 1
    if min_capacity < capacity[ind]:
        scale = min_capacity / capacity[ind]
        capacity *= scale
    return np.maximum(capacity, min_capacity), scale


def compute_vertex_costs(capacities: np.ndarray, delta: float = 1.2, scale: float = 10e5):
    return scale / (capacities ** delta)


def get_correct_graph(G, random_seed=42):
    G_full = nx.DiGraph()
    np.random.seed(random_seed)
    for u, v, data in G.edges(data=True):
        G_full.add_edge(u, v, weight=data["weight"] * np.random.uniform(0.99, 1.01))
        G_full.add_edge(v, u, weight=data["weight"] * np.random.uniform(0.99, 1.01))
    dist_matrix = [[0] * len(G.nodes()) for _ in range(len(G.nodes()))]
    for u in G_full.nodes():
        for v in G_full.nodes():
            if u != v:
                dist = nx.shortest_path_length(G_full, u, v, weight="weight")
                G_full.add_edge(u, v, weight=dist)
                dist_matrix[u][v] = dist
    return G_full, np.array(dist_matrix)


def generate_od_matrix_gravity(pops: np.ndarray, dist_matrix: np.ndarray, beta: float = 1.5, total_flow: float = None, pop_coeff: float = 0.7, count_coeff: float = 0.75, random_seed: int = 42):
    np.random.seed(random_seed)
    N = len(pops)
    O = (pops.copy() * np.random.uniform(0.8, 1.2, N)) ** pop_coeff
    D = (pops.copy() * np.random.uniform(0.8, 1.2, N)) ** pop_coeff
    OD_raw = np.outer(O, D) * (1.0 / (dist_matrix ** beta + 1e-6))
    np.fill_diagonal(OD_raw, 0)
    for _ in range(50):
        row_sums = OD_raw.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        OD_raw *= O.reshape(-1, 1) / row_sums
        col_sums = OD_raw.sum(axis=0, keepdims=True)
        col_sums[col_sums == 0] = 1
        OD_raw *= D.reshape(1, -1) / col_sums
        if np.max(np.abs(OD_raw.sum(axis=1) - O)) < 1e-6 and np.max(np.abs(OD_raw.sum(axis=0) - D)) < 1e-6:
            break
    if total_flow is not None and OD_raw.sum() > 0:
        OD_raw *= total_flow / OD_raw.sum()
    rows, cols = np.where(~np.eye(N, dtype=bool))
    res = pd.DataFrame({"src": rows, "dst": cols, "volume": np.round(OD_raw[rows, cols], 2)})
    n_keep = int(len(res) * count_coeff)
    weights = res["volume"].values
    weights = weights.sum() - weights
    weights /= weights.sum()
    return res.iloc[np.random.choice(len(res), size=n_keep, replace=False, p=weights)].reset_index(drop=True)


def generate(data: GenerateData, folder):
    pops_zipf = generate_cities_zipf(data.cities_count, data.cities_alpha, data.max_population)
    cities_coords = generate_coord(data.cities_count, data.storage_count, data.cluster_std, data.map_size, pops_zipf)
    final_nodes = cluster_cities_into_storages(cities_coords, data.storage_count, data.dist_between_cites)
    positions = final_nodes[["x", "y"]].to_numpy()
    population = final_nodes["population"].to_numpy()
    G = build_gastner_newman_network(positions, data.lam, data.budget, seed=data.random_seed)
    capacities, data.capacity_scale = compute_vertex_capacity(population, G, data.pop_gamma, data.between_alpha, data.min_capacity, data.capacity_scale)
    costs = compute_vertex_costs(capacities, data.capacity_delta, data.cost_scale)
    G_full, dist_matrix = get_correct_graph(G, data.random_seed)
    data.total_flow *= np.sum(capacities)
    od_matrix = generate_od_matrix_gravity(population, dist_matrix, data.od_betta, data.total_flow, data.pop_coeff, data.count_coeff, data.random_seed)

    os.makedirs(folder, exist_ok=True)
    offices_df = pd.DataFrame([{"office_id": s, "transfer_price": round(costs[s], 3), "transfer_max": round(capacities[s])} for s in range(data.storage_count)])
    offices_df.to_csv(folder + "/offices.csv", index=False)
    od_matrix.to_csv(folder + "/reqs.csv", index=False)
    dists_df = pd.DataFrame([{"src": u, "dst": v, "price": round(dist_matrix[u][v] * data.km_cost, 3)} for u in range(data.storage_count) for v in range(data.storage_count) if u != v])
    dists_df.to_csv(folder + "/distance_matrix.csv", index=False)
    with open(folder + "/data.txt", "w", encoding="utf-8") as f:
        for key, value in vars(data).items():
            f.write(f"{key} = {value}\n")
    nx.write_graphml(G, folder + "/graph.graphml")
    final_nodes.to_csv(folder + "/pos_pop.csv", index=False)