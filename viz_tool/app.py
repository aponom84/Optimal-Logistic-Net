"""Streamlit viewer for logistics-network optimization solutions.

Run from the repository root:
    streamlit run viz_tool/app.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plots  # noqa: E402
from loader import discover_instances, load_solution  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="Logistics Network Solution Viewer",
                   layout="wide", page_icon="🚚")


@st.cache_resource(show_spinner=False)
def _instances():
    return discover_instances(ROOT)


@st.cache_resource(show_spinner="Loading solution…")
def _solution(label: str):
    ref = next(r for r in _instances() if r.label == label)
    return load_solution(ref)


def fmt(x, nd=0):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    try:
        return f"{float(x):,.{nd}f}"
    except (ValueError, TypeError):
        return "—"


# --------------------------------------------------------------------------
# Sidebar — instance selection & options
# --------------------------------------------------------------------------
instances = _instances()
if not instances:
    st.error("No solved instances found under ./Results with matching ./Generated_Data.")
    st.stop()

st.sidebar.title("🚚 Solution Viewer")
st.sidebar.caption("Capacitated multi-commodity flow with vehicle costs & "
                   "warehouse overload limits.")

categories = sorted({r.category for r in instances})
cat = st.sidebar.selectbox("Dataset", ["All"] + categories)
labels = [r.label for r in instances if cat == "All" or r.category == cat]
label = st.sidebar.selectbox("Instance", labels, key=f"instance_{cat}")

sol = _solution(label)

# capacity override
st.sidebar.markdown("**Vehicle capacity**")
note = "auto-detected" if sol.capacity_inferred else "from data"
cap = st.sidebar.number_input(
    f"Effective capacity ({note}; generation file says {fmt(sol.gen_capacity)})",
    min_value=1.0, value=float(sol.vehicle_capacity), step=1.0)
if cap != sol.vehicle_capacity:
    sol.set_effective_capacity(cap)

st.sidebar.divider()
st.sidebar.markdown("**Map options**")
node_size_metric = st.sidebar.selectbox(
    "Node size by", ["transit_volume", "origin_volume", "dest_volume",
                     "population", "overload_util"], index=0)
edge_color_metric = st.sidebar.selectbox(
    "Edge color by", ["utilization", "vehicle", "flow", "transport_cost"], index=0)
show_unused = st.sidebar.checkbox("Show unused roads", value=False)

# --------------------------------------------------------------------------
# Header + KPIs
# --------------------------------------------------------------------------
st.title(label.replace("/", " · "))

def _num(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return None


meta = sol.result_meta
vns = _num(meta.get("result price"))
opt = _num(meta.get("optimal result price"))
init = _num(meta.get("init price"))
solve_t = _num(meta.get("solving time"))
gap = (vns - opt) / opt * 100 if (vns and opt) else None
improve = (init - vns) / init * 100 if (init and vns) else None

n_used = int((sol.edge_flow["vehicle"] > 0).sum())
total_veh = int(sol.edge_flow["vehicle"].sum())
avg_tr = np.average(sol.result["n_transfers"], weights=sol.result["volume"])
avg_hop = np.average(sol.result["n_hops"], weights=sol.result["volume"])

c = st.columns(6)
c[0].metric("Reconstructed cost", fmt(sol.cost["total"]))
c[1].metric("Transport / Transfer",
            f"{fmt(sol.cost['transport_share']*100,1)}% / {fmt(sol.cost['transfer_share']*100,1)}%")
c[2].metric("Warehouses", fmt(sol.n_nodes))
c[3].metric("Commodities", fmt(len(sol.commodities)))
c[4].metric("Edges used", f"{n_used} / {len(sol.edges)}")
c[5].metric("Total vehicles", fmt(total_veh))

c = st.columns(6)
c[0].metric("Avg transfers / unit", fmt(avg_tr, 2))
c[1].metric("Avg hops / unit", fmt(avg_hop, 2))
c[2].metric("VNS price", fmt(vns))
c[3].metric("Optimal (MILP) price", fmt(opt))
c[4].metric("Gap to optimal", f"{fmt(gap,2)}%" if gap is not None else "—")
c[5].metric("Solving time", f"{fmt(solve_t,1)} s" if solve_t else "—")

# --------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------
tab_map, tab_paths, tab_edges, tab_nodes, tab_commodity, tab_overview, tab_raw = st.tabs(
    ["🗺️ Network map", "🛣️ Paths & transfers", "🔗 Edges", "🏭 Warehouses",
     "🔍 Commodity explorer", "📊 Overview", "📄 Raw data"])

# ---- Network map ---------------------------------------------------------
with tab_map:
    geo_note = ("**Geographic map** (Real_Graph coordinates are Web-Mercator, "
                "shown on OpenStreetMap). " if sol.is_geographic
                else "**Planar layout** (Synthetic coordinates are abstract). ")
    st.caption(geo_note + "Node label = warehouse id. Node size = "
               f"`{node_size_metric}`, node fill = overload utilization. "
               f"Edge marker size = vehicles, color = `{edge_color_metric}`. "
               "Hover for details.")
    fig = plots.network_map(sol, node_size_metric, edge_color_metric, show_unused)
    st.plotly_chart(fig, width='stretch')

# ---- Paths & transfers ---------------------------------------------------
with tab_paths:
    res = sol.result
    com = sol.commodities
    weighted = st.radio("Weight distributions by",
                        ["path count", "shipped volume"], horizontal=True)
    w = res["volume"] if weighted == "shipped volume" else None
    wc = com  # commodity-level

    r1 = st.columns(2)
    with r1[0]:
        st.markdown("**Number of transfer (transshipment) points per path**")
        st.plotly_chart(plots.histogram(res["n_transfers"], "transfer points", w),
                        width='stretch')
    with r1[1]:
        st.markdown("**Path length (hops / edges traversed)**")
        st.plotly_chart(plots.histogram(res["n_hops"], "hops", w, color="#72B7B2"),
                        width='stretch')

    r2 = st.columns(2)
    with r2[0]:
        st.markdown("**Path geographic length (sum of edge costs)**")
        st.plotly_chart(plots.histogram(res["distance"], "path cost / distance", w,
                                        color="#E45756"),
                        width='stretch')
    with r2[1]:
        st.markdown("**Paths used per commodity (flow splitting)**")
        st.plotly_chart(plots.histogram(com["n_paths"], "paths per commodity",
                                        color="#54A24B"),
                        width='stretch')

    r3 = st.columns(2)
    with r3[0]:
        st.markdown("**Detour ratio (path distance ÷ direct edge distance)**")
        det = com["detour"].replace([np.inf, -np.inf], np.nan).dropna()
        st.plotly_chart(plots.histogram(det, "detour ratio", color="#B279A2"),
                        width='stretch')
    with r3[1]:
        st.markdown("**Direct vs. transshipped volume**")
        direct = com["direct_volume"].sum()
        total = com["delivered"].sum()
        share = pd.DataFrame({
            "type": ["direct (0 transfers)", "transshipped (≥1 transfer)"],
            "volume": [direct, total - direct]})
        st.plotly_chart(plots.bar(share, "type", "volume", "", "volume"),
                        width='stretch')

    st.markdown("**Summary statistics**")
    s1 = st.columns(4)
    s1[0].metric("Avg transfers / path", fmt(res["n_transfers"].mean(), 2))
    s1[1].metric("Max transfers", fmt(res["n_transfers"].max()))
    s1[2].metric("Avg hops / path", fmt(res["n_hops"].mean(), 2))
    s1[3].metric("Avg paths / commodity", fmt(com["n_paths"].mean(), 2))
    s2 = st.columns(4)
    s2[0].metric("Single-path commodities", fmt((com["n_paths"] == 1).sum()))
    s2[1].metric("Split commodities (>1 path)", fmt((com["n_paths"] > 1).sum()))
    direct_share = direct / total * 100 if total else np.nan
    s2[2].metric("Direct-shipped volume", f"{fmt(direct_share,1)}%")
    s2[3].metric("Avg detour ratio", fmt(com["detour"].replace([np.inf], np.nan).mean(), 2))

# ---- Edges ---------------------------------------------------------------
with tab_edges:
    ef = sol.edge_flow
    e1 = st.columns(2)
    with e1[0]:
        st.markdown("**Edge utilization (flow ÷ vehicle capacity)**")
        st.plotly_chart(plots.histogram(ef["utilization"].dropna(), "utilization",
                                        color="#F58518"),
                        width='stretch')
        st.caption("Values >1 indicate the stored vehicle count was floored "
                   "(`int()` truncation in the saved solution).")
    with e1[1]:
        st.markdown("**Vehicles per edge**")
        st.plotly_chart(plots.histogram(ef["vehicle"], "vehicles", color="#4C78A8"),
                        width='stretch')

    e2 = st.columns(3)
    e2[0].metric("Mean utilization", fmt(ef["utilization"].mean(), 2))
    e2[1].metric("Underused edges (<50%)", fmt((ef["utilization"] < 0.5).sum()))
    e2[2].metric("Total vehicle-cost", fmt(ef["transport_cost"].sum()))

    st.markdown("**Most loaded edges (by vehicles)**")
    top = ef.sort_values("vehicle", ascending=False).head(20)
    st.dataframe(top.round(2), width='stretch', hide_index=True)

# ---- Warehouses ----------------------------------------------------------
with tab_nodes:
    ns = sol.node_stats.copy()
    st.markdown("**Warehouse overload utilization (transit volume ÷ capacity W)**")
    ns_sorted = ns.sort_values("overload_util", ascending=False)
    st.plotly_chart(
        plots.bar(ns_sorted, x=ns_sorted["node"].astype(str), y="overload_util",
                  x_title="warehouse", y_title="overload utilization",
                  color="overload_util"),
        width='stretch')
    near = (ns["overload_util"] > 0.9).sum()
    n1 = st.columns(3)
    n1[0].metric("Warehouses near capacity (>90%)", fmt(near))
    n1[1].metric("Active transit warehouses", fmt((ns["transit_volume"] > 0).sum()))
    n1[2].metric("Max overload utilization", fmt(ns["overload_util"].max(), 2))

    st.markdown("**Throughput per warehouse (origin / destination / transit)**")
    tp = ns.melt(id_vars="node",
                 value_vars=["origin_volume", "dest_volume", "transit_volume"],
                 var_name="role", value_name="volume")
    import plotly.express as px
    figtp = px.bar(tp, x=tp["node"].astype(str), y="volume", color="role",
                   barmode="group")
    figtp.update_layout(xaxis_title="warehouse", height=380,
                        margin=dict(l=10, r=10, t=10, b=40), plot_bgcolor="white")
    st.plotly_chart(figtp, width='stretch')

    st.markdown("**Warehouse table**")
    st.dataframe(ns.round(2), width='stretch', hide_index=True)

# ---- Commodity explorer --------------------------------------------------
with tab_commodity:
    com = sol.commodities.sort_values("demand", ascending=False)
    opts = [f"{int(r.src)} → {int(r.dst)}  (demand {r.demand:.1f}, {int(r.n_paths)} paths)"
            for r in com.itertuples(index=False)]
    sel = st.selectbox("Select a commodity (origin → destination)", opts)
    idx = opts.index(sel)
    row = com.iloc[idx]
    s_, d_ = int(row["src"]), int(row["dst"])

    m = st.columns(5)
    m[0].metric("Demand", fmt(row["demand"], 1))
    m[1].metric("Paths used", fmt(row["n_paths"]))
    m[2].metric("Avg transfers", fmt(row["avg_transfers"], 2))
    m[3].metric("Avg distance", fmt(row["avg_distance"], 1))
    m[4].metric("Detour ratio", fmt(row["detour"], 2))

    paths_df = sol.result[(sol.result["src"] == s_) & (sol.result["dst"] == d_)].copy()
    paths_df = paths_df.sort_values("volume", ascending=False)

    left, right = st.columns([3, 2])
    with left:
        fig = plots.network_map(
            sol, node_size_metric, edge_color_metric, show_unused_edges=False,
            highlight_paths=list(paths_df["path"]),
            highlight_label=f"{s_}→{d_}")
        st.plotly_chart(fig, width='stretch')
    with right:
        st.markdown(f"**Paths for {s_} → {d_}**")
        disp = paths_df.assign(
            path=paths_df["path"].apply(lambda p: " → ".join(map(str, p))),
            share=(paths_df["volume"] / paths_df["volume"].sum() * 100).round(1))
        st.dataframe(
            disp[["path", "volume", "share", "n_transfers", "n_hops", "distance"]]
            .round(2),
            width='stretch', hide_index=True,
            column_config={"share": "share %"})

# ---- Overview ------------------------------------------------------------
with tab_overview:
    o1, o2 = st.columns(2)
    with o1:
        st.markdown("**Cost composition**")
        import plotly.express as px
        cost_df = pd.DataFrame({
            "component": ["transport (vehicles × edge cost)",
                          "transfer (overload at transit nodes)"],
            "cost": [sol.cost["transport"], sol.cost["transfer"]]})
        figc = px.pie(cost_df, names="component", values="cost", hole=0.5)
        figc.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(figc, width='stretch')
    with o2:
        st.markdown("**Solution quality**")
        q = pd.DataFrame({
            "stage": ["initial (greedy)", "VNS heuristic", "optimal (MILP)"],
            "price": [init, vns, opt]}).dropna()
        figq = px.bar(q, x="stage", y="price", color="stage", text_auto=".3s")
        figq.update_layout(height=360, showlegend=False,
                           margin=dict(l=10, r=10, t=10, b=10),
                           plot_bgcolor="white")
        st.plotly_chart(figq, width='stretch')
        if improve is not None:
            st.success(f"VNS improved the initial solution by **{improve:.1f}%**"
                       + (f"; within **{gap:.2f}%** of the MILP optimum."
                          if gap is not None else "."))

    st.markdown("**Generation parameters**")
    gp = sol.gen_params
    keys = ["storage_count", "cities_count", "total_flow", "budget",
            "vehicle_capacity", "km_cost", "max_population", "dist_between_cites",
            "random_seed"]
    show = {k: gp[k] for k in keys if k in gp}
    st.dataframe(pd.DataFrame([show]).T.rename(columns={0: "value"}),
                 width='stretch')

# ---- Raw data ------------------------------------------------------------
with tab_raw:
    which = st.selectbox("Table", ["result (path flows)", "edge vehicles + flow",
                                   "commodities (aggregated)", "warehouses",
                                   "requests (demand)", "edges (distances)"])
    if which == "result (path flows)":
        df = sol.result.assign(path=sol.result["path"].apply(lambda p: " → ".join(map(str, p))))
    elif which == "edge vehicles + flow":
        df = sol.edge_flow
    elif which == "commodities (aggregated)":
        df = sol.commodities
    elif which == "warehouses":
        df = sol.node_stats
    elif which == "requests (demand)":
        df = sol.reqs
    else:
        df = sol.edges
    st.dataframe(df.round(3), width='stretch', hide_index=True)
    st.download_button("Download as CSV", df.to_csv(index=False),
                       file_name=f"{label.replace('/', '_').replace(' ', '')}_{which.split()[0]}.csv")
