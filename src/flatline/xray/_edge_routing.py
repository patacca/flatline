"""libavoid edge routing facade for flatline.xray."""

# pyright: reportAttributeAccessIssue=false, reportImplicitRelativeImport=false, reportIndexIssue=false, reportMissingTypeArgument=false

from __future__ import annotations

from typing import TYPE_CHECKING

from flatline.xray._layout import LayoutResult
from flatline.xray._routing_context import RoutingContext

if TYPE_CHECKING:
    import networkx as nx

# Manual self-loop detour: libavoid cannot route a connector whose source
# and target shapes coincide, so we synthesize a U-shaped polyline outside
# the shape.  This must remain symmetrical with what the unified routing
# pass produces for self-edges.
_SELF_LOOP_OFFSET = 40.0


def _node_id_string(node_id: object) -> str:
    return repr(node_id)


def _make_self_loop_route(node: object) -> list[tuple[float, float]]:
    cx, cy, w, h = node.x, node.y, node.w, node.h
    right = cx + w / 2.0
    top = cy - h / 2.0
    y_detour = top - 30.0
    return [
        (right, cy),
        (right + _SELF_LOOP_OFFSET, cy),
        (right + _SELF_LOOP_OFFSET, y_detour),
        (cx, y_detour),
        (cx, top),
    ]


def register_main_graph(
    ctx: RoutingContext,
    layout: LayoutResult,
    pcode_graph: nx.MultiDiGraph,
) -> dict[tuple, list[tuple[float, float]]]:
    """Register every main-graph node and edge with the routing context.

    Returns the dict of synthetic self-loop routes that bypass libavoid;
    real edges are deferred to ``ctx.process()`` and retrieved later via
    ``main_routes`` below.
    """
    for node_key, pos in layout.nodes.items():
        ctx.add_shape(node_key, pos.x, pos.y, pos.w, pos.h)

    for node_id in pcode_graph.nodes:
        shape_key = _node_id_string(node_id)
        ctx.ensure_pin(shape_key, ("target", "top"), side="top")
        out_count = max(1, pcode_graph.out_degree(node_id))
        for index in range(out_count):
            ctx.ensure_pin(
                shape_key,
                ("main-source", index),
                side="bottom",
                slot_index=index + 1,
                slot_count=out_count,
            )

    self_loop_routes: dict[tuple, list[tuple[float, float]]] = {}
    for edge_id in pcode_graph.edges(keys=True):
        source, target, _key = edge_id
        if source == target:
            self_loop_routes[edge_id] = _make_self_loop_route(
                layout.nodes[_node_id_string(source)]
            )
            continue
        src_shape = _node_id_string(source)
        tgt_shape = _node_id_string(target)
        out_indices = list(pcode_graph.out_edges(source, keys=True))
        slot_index = out_indices.index(edge_id)
        src_class = ctx.ensure_pin(
            src_shape,
            ("main-source", slot_index),
            side="bottom",
            slot_index=slot_index + 1,
            slot_count=max(1, len(out_indices)),
        )
        tgt_class = ctx.ensure_pin(tgt_shape, ("target", "top"), side="top")
        ctx.add_connector(("main", edge_id), src_shape, src_class, tgt_shape, tgt_class)
    return self_loop_routes


def main_routes(
    ctx: RoutingContext,
    pcode_graph: nx.MultiDiGraph,
    self_loop_routes: dict[tuple, list[tuple[float, float]]],
) -> dict[tuple, list[tuple[float, float]]]:
    """Collect routes for all main-graph edges after ``ctx.process()``."""
    routes: dict[tuple, list[tuple[float, float]]] = dict(self_loop_routes)
    for edge_id in pcode_graph.edges(keys=True):
        source, target, _key = edge_id
        if source == target:
            continue
        routes[edge_id] = ctx.route_for(("main", edge_id))
    return routes


def route_edges(
    layout: LayoutResult,
    pcode_graph: nx.MultiDiGraph,
) -> dict[tuple, list[tuple[float, float]]]:
    """Route graph edges through libavoid using orthogonal polylines.

    Standalone entry point: builds a fresh ``RoutingContext`` for the main
    graph only.  For unified routing that nudges main and overlay edges
    together, see ``flatline.xray._unified_routing.route_all``.
    """
    ctx = RoutingContext.create()
    self_loops = register_main_graph(ctx, layout, pcode_graph)
    ctx.process()
    return main_routes(ctx, pcode_graph, self_loops)


__all__ = [
    "main_routes",
    "register_main_graph",
    "route_edges",
]
