"""libavoid orthogonal routing for CPG overlay edges.

This module replaces the legacy manual Manhattan router for the three CPG
overlay families (cbranch, IOP, fspec).  It exposes a single entry point,
``route_overlay_edges``, that takes a list of source/target visual nodes
(plus optional virtual destination rectangles) and returns the routed
polylines.  Style and slot-assignment decisions remain in the caller.
"""

# pyright: reportAttributeAccessIssue=false, reportImplicitRelativeImport=false, reportIndexIssue=false, reportMissingTypeArgument=false

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from flatline._errors import InternalError
from flatline.xray._layout import node_size

if TYPE_CHECKING:
    from flatline.models import PcodeOpInfo, VarnodeInfo
    from flatline.xray._layout import VisualNode


# Routing penalties.  Mirrors the values used by ``_edge_routing.route_edges``
# so overlay edges are nudged consistently with the main graph edges.
_CROSSING_PENALTY = 1000
_SEGMENT_PENALTY = 50
_FIXED_SHARED_PATH_PENALTY = 110
_SHAPE_BUFFER_DISTANCE = 14.0
# See _edge_routing for rationale; same value keeps overlay direction
# constraints (top -> ConnDirDown) consistent with main graph routing.
_PORT_DIRECTION_PENALTY = 200.0
# See _edge_routing._IDEAL_NUDGING_DISTANCE for rationale; mirrored here so
# overlay edges nudge with the same spacing as main graph edges and avoid
# bend points landing on top of arrow heads.
_IDEAL_NUDGING_DISTANCE = 8.0

# Pin class identifiers.  libavoid requires distinct integer classes per pin
# attached to a shape; values are arbitrary as long as they are unique within
# a shape.  We allocate disjoint ranges so the same shape can host source and
# target pins simultaneously without collision.
_PIN_CLASS_TARGET_TOP = 100
_PIN_CLASS_TARGET_BOTTOM = 101
_PIN_CLASS_TARGET_LEFT = 102
_PIN_CLASS_TARGET_RIGHT = 103
_PIN_CLASS_SOURCE_BASE = 200


@dataclass(frozen=True)
class OverlayShape:
    """Rectangle registered with the router as either a node or an obstacle.

    *key* is a stable identifier (``VisualNode.key`` for visual nodes, or a
    caller-chosen string for virtual rectangles).  *cx*/*cy* are the center
    coordinates and *w*/*h* the full width/height of the rectangle.
    """

    key: str
    cx: float
    cy: float
    w: float
    h: float


@dataclass(frozen=True)
class OverlayEdge:
    """A single overlay edge to route.

    *source_key* / *target_key* must reference shapes registered in the same
    routing call.  *source_side* / *target_side* select the pin attachment
    side ("top", "bottom", "left", "right").  *source_slot_index* /
    *source_slot_count* spread sibling source pins along the chosen side
    (1-based index, total count); ``(0, 1)`` centers the pin.  *inset_px*
    pushes the pin inwards from the rectangle edge by that many pixels via
    libavoid's ``insideOffset`` so the connector emerges with a visible
    horizontal/vertical stub.
    """

    source_key: str
    target_key: str
    source_side: str
    target_side: str
    source_slot_index: int = 0
    source_slot_count: int = 1
    inset_px: float = 0.0


def _load_avoid():
    try:
        from flatline._native_layout import avoid
    except ImportError as exc:
        raise InternalError("libavoid native layout bindings are unavailable") from exc
    return avoid


def _configure_router(avoid):
    router = avoid.Router(avoid.RouterFlag.OrthogonalRouting)
    router.setRoutingParameter(avoid.RoutingParameter.segmentPenalty, float(_SEGMENT_PENALTY))
    router.setRoutingParameter(avoid.RoutingParameter.crossingPenalty, float(_CROSSING_PENALTY))
    router.setRoutingParameter(
        avoid.RoutingParameter.fixedSharedPathPenalty,
        float(_FIXED_SHARED_PATH_PENALTY),
    )
    router.setRoutingParameter(avoid.RoutingParameter.shapeBufferDistance, _SHAPE_BUFFER_DISTANCE)
    router.setRoutingParameter(
        avoid.RoutingParameter.portDirectionPenalty, _PORT_DIRECTION_PENALTY
    )
    router.setRoutingParameter(
        avoid.RoutingParameter.idealNudgingDistance, _IDEAL_NUDGING_DISTANCE
    )
    router.setRoutingOption(avoid.RoutingOption.nudgeOrthogonalSegmentsConnectedToShapes, True)
    return router


def _side_vis_dir(avoid, side: str):
    # ConnDirFlag is the OUTWARD perpendicular of the pin's side (the
    # direction the connector leaves the shape). Top -> Up, bottom -> Down,
    # left -> Left, right -> Right. Inverting any of these makes libavoid
    # route around the shape to satisfy portDirectionPenalty.
    if side == "top":
        return avoid.ConnDirFlag.ConnDirUp
    if side == "bottom":
        return avoid.ConnDirFlag.ConnDirDown
    if side == "left":
        return avoid.ConnDirFlag.ConnDirLeft
    if side == "right":
        return avoid.ConnDirFlag.ConnDirRight
    raise InternalError(f"invalid overlay edge side: {side!r}")


def _side_pin_props(side: str, slot_index: int, slot_count: int) -> tuple[float, float]:
    """Return libavoid (x_offset, y_offset) proportions for a pin.

    libavoid pin offsets are normalized to ``[0.0, 1.0]`` along each axis,
    where ``(0,0)`` is the shape's top-left corner and ``(1,1)`` is the
    bottom-right.  For sided pins one axis is fixed at 0 or 1 and the other
    is spread by slot index.
    """
    if slot_count <= 0:
        slot_count = 1
    prop = 0.5 if slot_index <= 0 else slot_index / (slot_count + 1)
    if side == "top":
        return (prop, 0.0)
    if side == "bottom":
        return (prop, 1.0)
    if side == "left":
        return (0.0, prop)
    if side == "right":
        return (1.0, prop)
    raise InternalError(f"invalid overlay edge side: {side!r}")


def _target_pin_class(side: str) -> int:
    if side == "top":
        return _PIN_CLASS_TARGET_TOP
    if side == "bottom":
        return _PIN_CLASS_TARGET_BOTTOM
    if side == "left":
        return _PIN_CLASS_TARGET_LEFT
    if side == "right":
        return _PIN_CLASS_TARGET_RIGHT
    raise InternalError(f"invalid overlay target side: {side!r}")


def _route_points(route, source_key: str, target_key: str) -> list[tuple[float, float]]:
    if route.size < 2:
        raise InternalError(
            f"libavoid produced no overlay route for edge {source_key!r} -> {target_key!r}"
        )
    return [(route[i].x, route[i].y) for i in range(route.size)]


def route_overlay_edges(
    edges: Sequence[OverlayEdge],
    shapes: Sequence[OverlayShape],
    obstacles: Sequence[OverlayShape] = (),
) -> list[list[tuple[float, float]]]:
    """Route the given overlay edges around the given shapes/obstacles.

    *shapes* must include every node referenced by *edges* (lookup is by
    ``OverlayShape.key``); duplicate keys are accepted but only the first
    registration is used.  *obstacles* are additional rectangles registered
    with the router so the connectors avoid them but are never used as
    endpoints.  The returned list is parallel to *edges*.
    """
    if not edges:
        return []

    avoid = _load_avoid()
    router = _configure_router(avoid)

    # Register every shape exactly once, keyed by stable string id.
    shape_refs: dict[str, object] = {}
    seen_keys: set[str] = set()
    for shape in list(shapes) + list(obstacles):
        if shape.key in seen_keys:
            continue
        seen_keys.add(shape.key)
        rect = avoid.Rectangle(
            avoid.Point(shape.cx - shape.w / 2.0, shape.cy - shape.h / 2.0),
            avoid.Point(shape.cx + shape.w / 2.0, shape.cy + shape.h / 2.0),
        )
        shape_refs[shape.key] = avoid.ShapeRef(router, rect)

    # Allocate per-shape source pin classes so multiple source pins on the
    # same shape do not collide with one another.
    source_class_counters: dict[str, int] = {}

    # Pre-create one target pin per (shape, side).  Multiple incoming edges
    # to the same side share the pin; libavoid spreads them via nudging.
    target_pins: dict[tuple[str, str], None] = {}

    def ensure_target_pin(key: str, side: str) -> None:
        cache_key = (key, side)
        if cache_key in target_pins:
            return
        target_pins[cache_key] = None
        x_prop, y_prop = _side_pin_props(side, slot_index=0, slot_count=1)
        pin = avoid.ShapeConnectionPin(
            shape_refs[key],
            _target_pin_class(side),
            x_prop,
            y_prop,
            0.0,
            _side_vis_dir(avoid, side),
        )
        pin.setExclusive(False)

    connectors: list[object] = []
    for edge in edges:
        if edge.source_key not in shape_refs or edge.target_key not in shape_refs:
            raise InternalError(
                f"overlay edge references unknown shape: {edge.source_key!r} -> "
                f"{edge.target_key!r}"
            )
        ensure_target_pin(edge.target_key, edge.target_side)

        # Allocate a fresh source pin class for this specific edge so it
        # does not share an emission point with any other edge.
        next_class = source_class_counters.get(edge.source_key, 0)
        source_class_counters[edge.source_key] = next_class + 1
        source_class_id = _PIN_CLASS_SOURCE_BASE + next_class

        x_prop, y_prop = _side_pin_props(
            edge.source_side, edge.source_slot_index, edge.source_slot_count
        )

        # Convert pixel-inset to libavoid's insideOffset (in pixels per the
        # binding signature).  Only meaningful for sided pins; we apply it
        # uniformly so callers that need a stub get one regardless of side.
        inside_offset = max(0.0, edge.inset_px)

        source_pin = avoid.ShapeConnectionPin(
            shape_refs[edge.source_key],
            source_class_id,
            x_prop,
            y_prop,
            inside_offset,
            _side_vis_dir(avoid, edge.source_side),
        )
        source_pin.setExclusive(False)

        src_end = avoid.ConnEnd(shape_refs[edge.source_key], source_class_id)
        tgt_end = avoid.ConnEnd(shape_refs[edge.target_key], _target_pin_class(edge.target_side))
        connectors.append(avoid.ConnRef(router, src_end, tgt_end))

    router.processTransaction()

    return [
        _route_points(conn.displayRoute(), edge.source_key, edge.target_key)
        for conn, edge in zip(connectors, edges, strict=True)
    ]


def visual_node_shape(
    node: VisualNode,
    op_by_id: Mapping[int, PcodeOpInfo],
    varnode_by_id: Mapping[int, VarnodeInfo],
) -> OverlayShape:
    """Build an ``OverlayShape`` from a visual node using its drawn size."""
    width, height = node_size(node, op_by_id, varnode_by_id)
    return OverlayShape(key=node.key, cx=node.x, cy=node.y, w=width, h=height)


__all__ = [
    "OverlayEdge",
    "OverlayShape",
    "route_overlay_edges",
    "visual_node_shape",
]
