"""Plotly figure builders for the logistics-network solution viewer."""

from __future__ import annotations

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from loader import Solution

# qualitative palette for highlighted commodity paths
_PATH_COLORS = px.colors.qualitative.Bold + px.colors.qualitative.Set2


def _aspect_layout(fig: go.Figure, title: str | None = None) -> go.Figure:
    fig.update_layout(
        title=title,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=10, r=10, t=40 if title else 10, b=10),
        height=640,
        plot_bgcolor="white",
        hovermode="closest",
    )
    fig.update_xaxes(showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(showgrid=False, zeroline=False, visible=False,
                     scaleanchor="x", scaleratio=1)
    return fig


_EDGE_CBAR_TITLES = {"utilization": "edge util.", "vehicle": "vehicles",
                     "flow": "flow", "transport_cost": "edge cost"}


def _edge_hover(r) -> str:
    return (f"edge {r.src}→{r.dst}<br>vehicles: {r.vehicle}"
            f"<br>flow: {r.flow:.1f}<br>capacity: {r.capacity:.0f}"
            f"<br>utilization: {r.utilization:.2f}"
            f"<br>edge cost: {r.price:.0f}")


def _node_hover(n, row) -> str:
    return (f"<b>node {n}</b>"
            f"<br>transit volume: {row['transit_volume']:.1f}"
            f"<br>overload cap (W): {row['transfer_max']:.0f}"
            f"<br>overload util: {row['overload_util']:.2f}"
            f"<br>transfer price (f): {row['transfer_price']:.2f}"
            f"<br>origin vol: {row['origin_volume']:.0f}"
            f"<br>dest vol: {row['dest_volume']:.0f}"
            f"<br>vehicles in/out: {row['vehicles_in']}/{row['vehicles_out']}"
            f"<br>population: {row['population']:.0f}")


def _node_sizes(ns, metric, lo=10, hi=44):
    smetric = ns[metric].fillna(0).to_numpy()
    smax = max(smetric.max(), 1e-9)
    return [lo + (hi - lo) * (v if not np.isnan(v) else 0) / smax for v in smetric]


def network_map(
    sol: Solution,
    node_size_metric: str = "transit_volume",
    edge_color_metric: str = "utilization",
    show_unused_edges: bool = False,
    highlight_paths: list[list[int]] | None = None,
    highlight_label: str | None = None,
) -> go.Figure:
    if sol.is_geographic:
        return network_map_geo(sol, node_size_metric, edge_color_metric,
                               show_unused_edges, highlight_paths, highlight_label)
    coord = sol._coord
    ns = sol.node_stats.set_index("node")
    ef = sol.edge_flow

    fig = go.Figure()

    # ---- context: all available edges (faint) ---------------------------
    if show_unused_edges:
        used = set(zip(ef["src"], ef["dst"]))
        xs, ys = [], []
        for r in sol.edges.itertuples(index=False):
            if (r.src, r.dst) in used or (r.dst, r.src) in used:
                continue
            (x0, y0), (x1, y1) = coord[r.src], coord[r.dst]
            xs += [x0, x1, None]
            ys += [y0, y1, None]
        if xs:
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines", name="unused road",
                line=dict(color="rgba(200,200,200,0.35)", width=1),
                hoverinfo="skip"))

    # ---- used edges: gray topology lines --------------------------------
    xs, ys = [], []
    for r in ef.itertuples(index=False):
        (x0, y0), (x1, y1) = coord[r.src], coord[r.dst]
        xs += [x0, x1, None]
        ys += [y0, y1, None]
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines", name="used edge",
        line=dict(color="rgba(120,120,120,0.45)", width=1),
        hoverinfo="skip"))

    # ---- edge markers at midpoints: color = metric, size = vehicles -----
    mx, my, mcolor, msize, mtext = [], [], [], [], []
    vmax = max(ef["vehicle"].max(), 1)
    for r in ef.itertuples(index=False):
        (x0, y0), (x1, y1) = coord[r.src], coord[r.dst]
        # small perpendicular offset so opposing directed edges separate
        dx, dy = x1 - x0, y1 - y0
        L = (dx * dx + dy * dy) ** 0.5 or 1.0
        off = 0.04 * L if r.src < r.dst else -0.04 * L
        mx.append((x0 + x1) / 2 + (-dy / L) * off)
        my.append((y0 + y1) / 2 + (dx / L) * off)
        val = getattr(r, edge_color_metric)
        mcolor.append(val)
        msize.append(6 + 16 * (r.vehicle / vmax))
        mtext.append(
            f"edge {r.src}→{r.dst}<br>vehicles: {r.vehicle}"
            f"<br>flow: {r.flow:.1f}<br>capacity: {r.capacity:.0f}"
            f"<br>utilization: {r.utilization:.2f}"
            f"<br>edge cost: {r.price:.0f}")
    cbar_title = {"utilization": "edge util.", "vehicle": "vehicles",
                  "flow": "flow", "transport_cost": "edge cost"}.get(
                      edge_color_metric, edge_color_metric)
    fig.add_trace(go.Scatter(
        x=mx, y=my, mode="markers", name="edge",
        marker=dict(size=msize, color=mcolor, colorscale="YlOrRd",
                    cmin=0, showscale=True,
                    colorbar=dict(title=cbar_title, x=1.0, len=0.45, y=0.78),
                    line=dict(width=0)),
        text=mtext, hoverinfo="text"))

    # ---- nodes ----------------------------------------------------------
    nx_, ny_, nsize, ncolor, ntext = [], [], [], [], []
    smetric = ns[node_size_metric].fillna(0).to_numpy()
    smax = max(smetric.max(), 1e-9)
    for n, row in ns.iterrows():
        x, y = coord[n]
        nx_.append(x)
        ny_.append(y)
        nsize.append(10 + 34 * (row[node_size_metric] if not np.isnan(row[node_size_metric]) else 0) / smax)
        ncolor.append(row["overload_util"] if not np.isnan(row["overload_util"]) else 0)
        ntext.append(
            f"<b>node {n}</b>"
            f"<br>transit volume: {row['transit_volume']:.1f}"
            f"<br>overload cap (W): {row['transfer_max']:.0f}"
            f"<br>overload util: {row['overload_util']:.2f}"
            f"<br>transfer price (f): {row['transfer_price']:.2f}"
            f"<br>origin vol: {row['origin_volume']:.0f}"
            f"<br>dest vol: {row['dest_volume']:.0f}"
            f"<br>vehicles in/out: {row['vehicles_in']}/{row['vehicles_out']}"
            f"<br>population: {row['population']:.0f}")
    fig.add_trace(go.Scatter(
        x=nx_, y=ny_, mode="markers+text", name="warehouse",
        text=[str(n) for n in ns.index], textposition="middle center",
        textfont=dict(size=9, color="white"),
        marker=dict(size=nsize, color=ncolor, colorscale="Tealrose",
                    cmin=0, cmax=1, showscale=True,
                    colorbar=dict(title="node overload", x=1.08, len=0.45, y=0.25),
                    line=dict(width=1, color="rgba(40,40,40,0.7)")),
        customdata=ntext,
        hovertemplate="%{customdata}<extra></extra>"))

    # ---- highlighted commodity paths ------------------------------------
    if highlight_paths:
        for i, path in enumerate(highlight_paths):
            xs = [coord[n][0] for n in path]
            ys = [coord[n][1] for n in path]
            color = _PATH_COLORS[i % len(_PATH_COLORS)]
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="lines+markers",
                name=(highlight_label or "path") + f" #{i+1}",
                line=dict(color=color, width=4),
                marker=dict(size=10, color=color, symbol="arrow",
                            angleref="previous"),
                hoverinfo="skip"))

    return _aspect_layout(fig)


def _auto_zoom(lons, lats) -> tuple[dict, float]:
    lons, lats = np.asarray(lons), np.asarray(lats)
    center = dict(lon=float(np.nanmean(lons)), lat=float(np.nanmean(lats)))
    span = max(float(np.nanmax(lons) - np.nanmin(lons)),
               float(np.nanmax(lats) - np.nanmin(lats)), 1e-3)
    zoom = float(np.clip(np.log2(360.0 / span) - 0.5, 1, 12))
    return center, zoom


def network_map_geo(
    sol: Solution,
    node_size_metric: str = "transit_volume",
    edge_color_metric: str = "utilization",
    show_unused_edges: bool = False,
    highlight_paths: list[list[int]] | None = None,
    highlight_label: str | None = None,
) -> go.Figure:
    """Geographic map for Real_Graph instances (coords are Web Mercator → lon/lat)."""
    ll = sol._lonlat
    ns = sol.node_stats.set_index("node")
    ef = sol.edge_flow
    fig = go.Figure()

    # ---- context: unused roads -----------------------------------------
    if show_unused_edges:
        used = set(zip(ef["src"], ef["dst"]))
        lon, lat = [], []
        for r in sol.edges.itertuples(index=False):
            if (r.src, r.dst) in used or (r.dst, r.src) in used:
                continue
            (a0, b0), (a1, b1) = ll[r.src], ll[r.dst]
            lon += [a0, a1, None]
            lat += [b0, b1, None]
        if lon:
            fig.add_trace(go.Scattermap(
                lon=lon, lat=lat, mode="lines", name="unused road",
                line=dict(color="rgba(150,150,150,0.4)", width=1),
                hoverinfo="skip"))

    # ---- used edges: topology lines ------------------------------------
    lon, lat = [], []
    for r in ef.itertuples(index=False):
        (a0, b0), (a1, b1) = ll[r.src], ll[r.dst]
        lon += [a0, a1, None]
        lat += [b0, b1, None]
    fig.add_trace(go.Scattermap(
        lon=lon, lat=lat, mode="lines", name="used edge",
        line=dict(color="rgba(70,70,70,0.55)", width=1.5), hoverinfo="skip"))

    # ---- edge midpoint markers -----------------------------------------
    mlon, mlat, mcolor, msize, mtext = [], [], [], [], []
    vmax = max(ef["vehicle"].max(), 1)
    for r in ef.itertuples(index=False):
        (a0, b0), (a1, b1) = ll[r.src], ll[r.dst]
        mlon.append((a0 + a1) / 2)
        mlat.append((b0 + b1) / 2)
        mcolor.append(getattr(r, edge_color_metric))
        msize.append(6 + 16 * (r.vehicle / vmax))
        mtext.append(_edge_hover(r))
    fig.add_trace(go.Scattermap(
        lon=mlon, lat=mlat, mode="markers", name="edge",
        marker=dict(size=msize, color=mcolor, colorscale="YlOrRd", cmin=0,
                    showscale=True,
                    colorbar=dict(title=_EDGE_CBAR_TITLES.get(edge_color_metric,
                                                              edge_color_metric),
                                  x=1.0, len=0.45, y=0.78)),
        text=mtext, hoverinfo="text"))

    # ---- nodes ----------------------------------------------------------
    nlon, nlat, ncolor, ntext = [], [], [], []
    for n, row in ns.iterrows():
        a, b = ll[n]
        nlon.append(a)
        nlat.append(b)
        ncolor.append(row["overload_util"] if not np.isnan(row["overload_util"]) else 0)
        ntext.append(_node_hover(n, row))
    fig.add_trace(go.Scattermap(
        lon=nlon, lat=nlat, mode="markers+text", name="warehouse",
        text=[str(n) for n in ns.index], textposition="top center",
        textfont=dict(size=11, color="black"),
        marker=dict(size=_node_sizes(ns, node_size_metric, 9, 30),
                    color=ncolor, colorscale="Tealrose", cmin=0, cmax=1,
                    showscale=True,
                    colorbar=dict(title="node overload", x=1.08, len=0.45, y=0.25)),
        customdata=ntext, hovertemplate="%{customdata}<extra></extra>"))

    # ---- highlighted commodity paths -----------------------------------
    if highlight_paths:
        for i, path in enumerate(highlight_paths):
            lons = [ll[n][0] for n in path]
            lats = [ll[n][1] for n in path]
            color = _PATH_COLORS[i % len(_PATH_COLORS)]
            fig.add_trace(go.Scattermap(
                lon=lons, lat=lats, mode="lines+markers",
                name=(highlight_label or "path") + f" #{i+1}",
                line=dict(color=color, width=5),
                marker=dict(size=11, color=color), hoverinfo="skip"))

    center, zoom = _auto_zoom([ll[n][0] for n in ns.index],
                              [ll[n][1] for n in ns.index])
    fig.update_layout(
        map=dict(style="open-street-map", center=center, zoom=zoom),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0),
        margin=dict(l=0, r=0, t=30, b=0), height=660, hovermode="closest")
    return fig


def histogram(values, x_title, weights=None, nbins=None, color="#4C78A8"):
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=values, y=weights, histfunc="sum" if weights is not None else "count",
        nbinsx=nbins, marker_color=color))
    fig.update_layout(
        xaxis_title=x_title,
        yaxis_title="volume" if weights is not None else "count",
        bargap=0.05, height=340, margin=dict(l=10, r=10, t=10, b=40),
        plot_bgcolor="white")
    return fig


def bar(df, x, y, x_title, y_title, color=None, color_scale="YlOrRd"):
    fig = px.bar(df, x=x, y=y, color=color, color_continuous_scale=color_scale)
    fig.update_layout(
        xaxis_title=x_title, yaxis_title=y_title,
        height=380, margin=dict(l=10, r=10, t=10, b=40), plot_bgcolor="white")
    return fig
