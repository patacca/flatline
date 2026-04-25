"""libavoid edge routing facade for flatline.xray."""

# pyright: reportAttributeAccessIssue=false, reportImplicitRelativeImport=false, reportIndexIssue=false, reportMissingTypeArgument=false

from __future__ import annotations

from typing import TYPE_CHECKING

from flatline._errors import InternalError
from flatline.xray._layout import LayoutResult

if TYPE_CHECKING:
    import networkx as nx

_CROSSING_PENALTY = 10000
_SEGMENT_PENALTY = 50
_FIXED_SHARED_PATH_PENALTY = 110
_SHAPE_BUFFER_DISTANCE = 8.0
_SELF_LOOP_OFFSET = 40.0


def _load_avoid():
    try:
        from flatline._native_layout import avoid
    except ImportError as exc:
        raise InternalError("libavoid native layout bindings are unavailable") from exc
    return avoid


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


def _configure_router(avoid: object) -> object:
    router = avoid.Router(avoid.RouterFlag.OrthogonalRouting)
    router.setRoutingParameter(avoid.RoutingParameter.segmentPenalty, float(_SEGMENT_PENALTY))
    router.setRoutingParameter(avoid.RoutingParameter.crossingPenalty, float(_CROSSING_PENALTY))
    router.setRoutingParameter(
        avoid.RoutingParameter.fixedSharedPathPenalty,
        float(_FIXED_SHARED_PATH_PENALTY),
    )
    router.setRoutingParameter(avoid.RoutingParameter.shapeBufferDistance, _SHAPE_BUFFER_DISTANCE)
    router.setRoutingOption(avoid.RoutingOption.nudgeOrthogonalSegmentsConnectedToShapes, True)
    return router


def _source_pin_classes(pcode_graph: nx.MultiDiGraph) -> dict[tuple, int]:
    pins: dict[tuple, int] = {}
    for node_id in pcode_graph.nodes:
        for class_id, edge_id in enumerate(pcode_graph.out_edges(node_id, keys=True), start=1):
            pins[edge_id] = class_id
    return pins


def _route_points(route: object, edge_id: tuple) -> list[tuple[float, float]]:
    if route.size < 2:
        raise InternalError(f"libavoid produced no route for edge {edge_id!r}")
    return [(route[i].x, route[i].y) for i in range(route.size)]


def route_edges(
    layout: LayoutResult,
    pcode_graph: nx.MultiDiGraph,
) -> dict[tuple, list[tuple[float, float]]]:
    """Route graph edges through libavoid using orthogonal polylines."""
    avoid = _load_avoid()
    router = _configure_router(avoid)
    shapes = {}
    for node_key, pos in layout.nodes.items():
        rect = avoid.Rectangle(
            avoid.Point(pos.x - pos.w / 2.0, pos.y - pos.h / 2.0),
            avoid.Point(pos.x + pos.w / 2.0, pos.y + pos.h / 2.0),
        )
        shapes[node_key] = avoid.ShapeRef(router, rect)

    for node_id in pcode_graph.nodes:
        shape = shapes[_node_id_string(node_id)]
        target_pin = avoid.ShapeConnectionPin(shape, 100, 0.5, 0.0)
        target_pin.setExclusive(False)
        out_count = max(1, pcode_graph.out_degree(node_id))
        for index in range(out_count):
            prop_x = (index + 1) / (out_count + 1)
            source_pin = avoid.ShapeConnectionPin(shape, index + 1, prop_x, 1.0)
            source_pin.setExclusive(False)

    source_pin_classes = _source_pin_classes(pcode_graph)
    connectors = {}
    routes = {}
    for edge_id in pcode_graph.edges(keys=True):
        source, target, _key = edge_id
        if source == target:
            routes[edge_id] = _make_self_loop_route(layout.nodes[_node_id_string(source)])
            continue
        src_shape = shapes[_node_id_string(source)]
        tgt_shape = shapes[_node_id_string(target)]
        src_end = avoid.ConnEnd(src_shape, source_pin_classes[edge_id])
        tgt_end = avoid.ConnEnd(tgt_shape, 100)
        connectors[edge_id] = avoid.ConnRef(router, src_end, tgt_end)

    router.processTransaction()
    for edge_id, conn in connectors.items():
        routes[edge_id] = _route_points(conn.displayRoute(), edge_id)
    return routes


__all__ = [
    "route_edges",
]
