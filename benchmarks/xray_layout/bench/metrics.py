"""Frozen metrics for xray_layout benchmark.

Implements exactly 9 metrics computed from a LayoutResult and the source
graph. All values are returned as floats. Counts are cast from int to
float for schema uniformity.

Metric definitions are FROZEN; do not extend or modify formulas without
revising the benchmark schema and historical comparisons.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import networkx as nx

    from .adapters._base import LayoutResult


# Geometric epsilon for collinearity / overlap tests. Layout coordinates
# are float pixels; 1.0 is below the smallest meaningful node spacing.
_EPS = 1e-9
_OVERLAP_MIN = 1.0


def compute(layout_result: LayoutResult, graph: nx.MultiDiGraph) -> dict[str, float]:
    """Compute the 9 frozen layout-quality metrics.

    Args:
        layout_result: Output of an adapter's layout() call.
        graph: The source MultiDiGraph used to produce the layout. Node
            attributes must include 'instruction_addr'; edge attributes
            must include 'edge_type'.

    Returns:
        Dictionary with exactly 9 float-valued keys (see module docstring).
    """
    return {
        "edge_crossings": _metric_edge_crossings(layout_result, graph),
        "total_edge_length": _metric_total_edge_length(layout_result, graph),
        "runtime_ms": _metric_runtime_ms(layout_result, graph),
        "bend_count": _metric_bend_count(layout_result, graph),
        "bbox_area": _metric_bbox_area(layout_result, graph),
        "bbox_aspect": _metric_bbox_aspect(layout_result, graph),
        "port_violations": _metric_port_violations(layout_result, graph),
        "edge_overlaps": _metric_edge_overlaps(layout_result, graph),
        "same_instr_cluster_dist": _metric_same_instr_cluster_dist(layout_result, graph),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _segments(route: list) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Yield consecutive (p1, p2) segments from a polyline waypoint list."""
    segs = []
    for i in range(len(route) - 1):
        p1 = (float(route[i][0]), float(route[i][1]))
        p2 = (float(route[i + 1][0]), float(route[i + 1][1]))
        segs.append((p1, p2))
    return segs


def _cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    """2D cross product of vectors OA and OB."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _segments_properly_intersect(
    s1: tuple[tuple[float, float], tuple[float, float]],
    s2: tuple[tuple[float, float], tuple[float, float]],
) -> bool:
    """Return True iff two segments cross at an interior point.

    Excludes shared-endpoint touches and collinear overlaps (those are
    handled by edge_overlaps separately).
    """
    p1, p2 = s1
    p3, p4 = s2

    # Ignore endpoint coincidences (common for adjacent segments and
    # for edges that share a node; the spec excludes shared endpoints).
    shared = {p1, p2} & {p3, p4}
    if shared:
        return False

    d1 = _cross(p3, p4, p1)
    d2 = _cross(p3, p4, p2)
    d3 = _cross(p1, p2, p3)
    d4 = _cross(p1, p2, p4)

    # Proper intersection: strict sign opposition on both segments.
    if ((d1 > _EPS and d2 < -_EPS) or (d1 < -_EPS and d2 > _EPS)) and (
        (d3 > _EPS and d4 < -_EPS) or (d3 < -_EPS and d4 > _EPS)
    ):
        return True

    # Treat exactly-zero (touching/collinear) cases as non-crossings;
    # collinear overlap is reported by _metric_edge_overlaps.
    return False


def _endpoint_face(
    endpoint_xy: tuple[float, float],
    node_center: tuple[float, float],
    node_size: tuple[float, float],
) -> str:
    """Classify which bbox face an endpoint lies closest to."""
    cx, cy = float(node_center[0]), float(node_center[1])
    w, h = float(node_size[0]), float(node_size[1])
    x, y = float(endpoint_xy[0]), float(endpoint_xy[1])
    dists = {
        "top": abs(y - (cy - h / 2)),
        "bottom": abs(y - (cy + h / 2)),
        "left": abs(x - (cx - w / 2)),
        "right": abs(x - (cx + w / 2)),
    }
    return min(dists, key=lambda f: dists[f])


# ---------------------------------------------------------------------------
# Metric implementations
# ---------------------------------------------------------------------------


def _metric_edge_crossings(result: LayoutResult, graph: nx.MultiDiGraph) -> float:
    """Count proper segment-segment intersections across all edge pairs."""
    routes = list(result.edge_routes.values())
    all_segments: list[tuple[int, tuple]] = []
    for edge_idx, route in enumerate(routes):
        for seg in _segments(list(route)):
            all_segments.append((edge_idx, seg))

    count = 0
    n = len(all_segments)
    for i in range(n):
        ei, si = all_segments[i]
        for j in range(i + 1, n):
            ej, sj = all_segments[j]
            if ei == ej:
                # Same polyline; adjacent segments share endpoints by
                # construction, non-adjacent self-crossings within a
                # single edge are not counted as edge-edge crossings.
                continue
            if _segments_properly_intersect(si, sj):
                count += 1
    return float(count)


def _metric_total_edge_length(result: LayoutResult, graph: nx.MultiDiGraph) -> float:
    """Sum Manhattan-distance segment lengths across all edge polylines."""
    total = 0.0
    for route in result.edge_routes.values():
        pts = list(route)
        for i in range(len(pts) - 1):
            x1, y1 = float(pts[i][0]), float(pts[i][1])
            x2, y2 = float(pts[i + 1][0]), float(pts[i + 1][1])
            total += abs(x2 - x1) + abs(y2 - y1)
    return float(total)


def _metric_runtime_ms(result: LayoutResult, graph: nx.MultiDiGraph) -> float:
    """Forward the adapter-measured wall-clock runtime."""
    return float(result.runtime_ms)


def _metric_bend_count(result: LayoutResult, graph: nx.MultiDiGraph) -> float:
    """Sum interior vertices across all polylines (N-2 per polyline, floored at 0)."""
    total = 0
    for route in result.edge_routes.values():
        n = len(route)
        if n >= 3:
            total += n - 2
    return float(total)


def _metric_bbox_area(result: LayoutResult, graph: nx.MultiDiGraph) -> float:
    """Bounding-box area over node centers."""
    if not result.node_positions:
        return 0.0
    xs = [float(p[0]) for p in result.node_positions.values()]
    ys = [float(p[1]) for p in result.node_positions.values()]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))


def _metric_bbox_aspect(result: LayoutResult, graph: nx.MultiDiGraph) -> float:
    """Width/height aspect of node-center bbox; 0.0 if height is zero."""
    if not result.node_positions:
        return 0.0
    xs = [float(p[0]) for p in result.node_positions.values()]
    ys = [float(p[1]) for p in result.node_positions.values()]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    if height == 0:
        return 0.0
    return width / height


def _metric_port_violations(result: LayoutResult, graph: nx.MultiDiGraph) -> float:
    """Count edge endpoints that land on a face violating the edge's port contract.

    pcode_dataflow / cfg edges must enter/exit on top or bottom faces.
    iop edges must enter/exit on left or right faces.
    """
    violations = 0
    for u, v, key, data in graph.edges(keys=True, data=True):
        edge_type = data.get("edge_type")
        if edge_type in ("pcode_dataflow", "cfg"):
            allowed = {"top", "bottom"}
        elif edge_type == "iop":
            allowed = {"left", "right"}
        else:
            # Unknown edge type: not constrained, not counted.
            continue

        edge_id = (u, v, key)
        route = result.edge_routes.get(edge_id)
        if route is None or len(route) < 2:
            # No route available for this edge; cannot evaluate. Skip.
            continue

        # Source endpoint = first waypoint, attached to node u.
        src_face = _endpoint_face(
            (float(route[0][0]), float(route[0][1])),
            result.node_positions[u],
            result.node_sizes[u],
        )
        if src_face not in allowed:
            violations += 1

        # Target endpoint = last waypoint, attached to node v.
        tgt_face = _endpoint_face(
            (float(route[-1][0]), float(route[-1][1])),
            result.node_positions[v],
            result.node_sizes[v],
        )
        if tgt_face not in allowed:
            violations += 1
    return float(violations)


def _metric_edge_overlaps(result: LayoutResult, graph: nx.MultiDiGraph) -> float:
    """Count pairs of collinear segments whose overlap length exceeds 1.0 unit."""
    routes = list(result.edge_routes.values())
    all_segments: list[tuple[int, tuple]] = []
    for edge_idx, route in enumerate(routes):
        for seg in _segments(list(route)):
            all_segments.append((edge_idx, seg))

    count = 0
    n = len(all_segments)
    for i in range(n):
        ei, (a1, a2) = all_segments[i]
        for j in range(i + 1, n):
            ej, (b1, b2) = all_segments[j]
            if ei == ej:
                continue
            # Collinearity: all four points must be collinear.
            if abs(_cross(a1, a2, b1)) > _EPS:
                continue
            if abs(_cross(a1, a2, b2)) > _EPS:
                continue

            # Project all four points onto the dominant axis to compute
            # 1D interval overlap.
            dx = a2[0] - a1[0]
            dy = a2[1] - a1[1]
            if abs(dx) >= abs(dy):
                # Project onto x-axis.
                ia = sorted([a1[0], a2[0]])
                ib = sorted([b1[0], b2[0]])
            else:
                ia = sorted([a1[1], a2[1]])
                ib = sorted([b1[1], b2[1]])
            lo = max(ia[0], ib[0])
            hi = min(ia[1], ib[1])
            overlap = hi - lo
            if overlap > _OVERLAP_MIN:
                count += 1
    return float(count)


def _metric_same_instr_cluster_dist(
    result: LayoutResult, graph: nx.MultiDiGraph
) -> float:
    """Mean of per-instruction-group mean pairwise Euclidean distances."""
    groups: dict = {}
    for node_id, data in graph.nodes(data=True):
        addr = data.get("instruction_addr")
        if addr is None:
            continue
        if node_id not in result.node_positions:
            continue
        groups.setdefault(addr, []).append(node_id)

    per_group_means: list[float] = []
    for nodes in groups.values():
        if len(nodes) < 2:
            continue
        positions = [result.node_positions[n] for n in nodes]
        dists: list[float] = []
        for i in range(len(positions)):
            xi, yi = float(positions[i][0]), float(positions[i][1])
            for j in range(i + 1, len(positions)):
                xj, yj = float(positions[j][0]), float(positions[j][1])
                dists.append(math.hypot(xj - xi, yj - yi))
        if dists:
            per_group_means.append(sum(dists) / len(dists))

    if not per_group_means:
        return 0.0
    return sum(per_group_means) / len(per_group_means)
