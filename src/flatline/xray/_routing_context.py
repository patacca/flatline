"""Shared libavoid routing context for flatline.xray.

A single ``RoutingContext`` owns one ``avoid.Router`` instance, registers all
node shapes once, and allocates pin classes per shape with semantic keys so
main graph edges and CPG overlay edges (cbranch / IOP / fspec) can share the
same routing transaction.

Why one transaction matters: libavoid's nudging
(``nudgeOrthogonalSegmentsConnectedToShapes``) and crossing penalty only act
on connectors registered against the same ``Router``.  Routing main edges in
one router and overlay edges in a second, independent router lets overlay
segments collapse onto the same horizontal/vertical line as a main segment
because each router is unaware of the other's geometry.  Sharing a router
lets libavoid spread all segments globally.
"""

# pyright: reportAttributeAccessIssue=false, reportImplicitRelativeImport=false, reportIndexIssue=false, reportMissingTypeArgument=false

from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from flatline._errors import InternalError

if TYPE_CHECKING:
    pass


# Routing penalties.  Mirrors the values previously duplicated in
# ``_edge_routing`` and ``_cpg_routing`` so unified routing keeps the same
# spacing and avoidance behavior the standalone routers used.
CROSSING_PENALTY = 1000
SEGMENT_PENALTY = 50
FIXED_SHARED_PATH_PENALTY = 110
SHAPE_BUFFER_DISTANCE = 14.0
# See _edge_routing for rationale; portDirection acts as an effective hard
# constraint making top-target / bottom-source pins behave as pinned sides.
PORT_DIRECTION_PENALTY = 200.0
# libavoid's default idealNudgingDistance is 4 px, which lets the final
# orthogonal segment collapse to a few pixels and visually glues bend points
# to arrow heads.  Doubling it widens parallel-segment spacing and pushes the
# last bend further from the target shape so the stub before the arrowhead
# stays long enough to read cleanly.
IDEAL_NUDGING_DISTANCE = 8.0


def _load_avoid():
    try:
        from flatline._native_layout import avoid
    except ImportError as exc:
        raise InternalError("libavoid native layout bindings are unavailable") from exc
    return avoid


@dataclass
class _ShapeEntry:
    """Per-shape registry: shape ref + semantic-key -> pin-class-id map."""

    ref: Any
    pins: dict[Hashable, int] = field(default_factory=dict)
    next_class_id: int = 1


@dataclass
class RoutingContext:
    """One libavoid router with shared shape and pin-class registries.

    Callers register every visible rectangle exactly once via
    ``add_shape``, request pins via ``ensure_pin`` (idempotent per
    ``(shape_key, pin_key)``), and finally add connectors with
    ``add_connector`` whose return value is a ``ConnRef``.  ``process()``
    runs the libavoid transaction and ``route_for`` retrieves the resulting
    polyline for any registered connector.
    """

    avoid: Any
    router: Any
    _shapes: dict[str, _ShapeEntry] = field(default_factory=dict)
    _connectors: dict[Hashable, Any] = field(default_factory=dict)
    _processed: bool = False

    @classmethod
    def create(cls) -> RoutingContext:
        avoid = _load_avoid()
        router = avoid.Router(avoid.RouterFlag.OrthogonalRouting)
        router.setRoutingParameter(avoid.RoutingParameter.segmentPenalty, float(SEGMENT_PENALTY))
        router.setRoutingParameter(avoid.RoutingParameter.crossingPenalty, float(CROSSING_PENALTY))
        router.setRoutingParameter(
            avoid.RoutingParameter.fixedSharedPathPenalty,
            float(FIXED_SHARED_PATH_PENALTY),
        )
        router.setRoutingParameter(
            avoid.RoutingParameter.shapeBufferDistance, SHAPE_BUFFER_DISTANCE
        )
        router.setRoutingParameter(
            avoid.RoutingParameter.portDirectionPenalty, PORT_DIRECTION_PENALTY
        )
        router.setRoutingParameter(
            avoid.RoutingParameter.idealNudgingDistance, IDEAL_NUDGING_DISTANCE
        )
        router.setRoutingOption(avoid.RoutingOption.nudgeOrthogonalSegmentsConnectedToShapes, True)
        return cls(avoid=avoid, router=router)

    def add_shape(self, key: str, cx: float, cy: float, w: float, h: float) -> None:
        """Register a rectangle with the router, idempotent on ``key``.

        Subsequent calls with the same key are silently ignored so callers
        can safely re-register endpoints they already added as obstacles.
        """
        if key in self._shapes:
            return
        rect = self.avoid.Rectangle(
            self.avoid.Point(cx - w / 2.0, cy - h / 2.0),
            self.avoid.Point(cx + w / 2.0, cy + h / 2.0),
        )
        ref = self.avoid.ShapeRef(self.router, rect)
        self._shapes[key] = _ShapeEntry(ref=ref)

    def has_shape(self, key: str) -> bool:
        return key in self._shapes

    def shape_ref(self, key: str) -> Any:
        entry = self._shapes.get(key)
        if entry is None:
            raise InternalError(f"routing context has no shape registered for {key!r}")
        return entry.ref

    def ensure_pin(
        self,
        shape_key: str,
        pin_key: Hashable,
        side: str,
        slot_index: int = 0,
        slot_count: int = 1,
        inset_px: float = 0.0,
        exclusive: bool = False,
    ) -> int:
        """Allocate-or-return the libavoid pin class for ``(shape, pin_key)``.

        ``pin_key`` is any hashable identity for the pin (e.g. ``("target",
        "top")`` to share one top-target pin between main and overlay edges,
        or ``("overlay-source", "iop", edge_index)`` to give a specific
        overlay edge its own emission point).  Pin classes are allocated
        per-shape monotonically so main-source and overlay-source pin
        classes never collide on the same shape.
        """
        entry = self._shapes.get(shape_key)
        if entry is None:
            raise InternalError(f"cannot allocate pin on unregistered shape {shape_key!r}")
        if pin_key in entry.pins:
            return entry.pins[pin_key]
        class_id = entry.next_class_id
        entry.next_class_id += 1
        entry.pins[pin_key] = class_id

        x_prop, y_prop = _side_pin_props(side, slot_index, slot_count)
        pin = self.avoid.ShapeConnectionPin(
            entry.ref,
            class_id,
            x_prop,
            y_prop,
            max(0.0, inset_px),
            _side_vis_dir(self.avoid, side),
        )
        pin.setExclusive(exclusive)
        return class_id

    def add_connector(
        self,
        connector_key: Hashable,
        source_shape: str,
        source_class: int,
        target_shape: str,
        target_class: int,
    ) -> Any:
        """Register a libavoid connector between two pins, return its ConnRef."""
        if connector_key in self._connectors:
            raise InternalError(f"routing context already has a connector for {connector_key!r}")
        src_end = self.avoid.ConnEnd(self.shape_ref(source_shape), source_class)
        tgt_end = self.avoid.ConnEnd(self.shape_ref(target_shape), target_class)
        conn = self.avoid.ConnRef(self.router, src_end, tgt_end)
        self._connectors[connector_key] = conn
        return conn

    def process(self) -> None:
        if self._processed:
            return
        self.router.processTransaction()
        self._processed = True

    def route_for(self, connector_key: Hashable) -> list[tuple[float, float]]:
        if not self._processed:
            raise InternalError("RoutingContext.process() must be called before route_for")
        conn = self._connectors.get(connector_key)
        if conn is None:
            raise InternalError(f"routing context has no connector for {connector_key!r}")
        route = conn.displayRoute()
        if route.size < 2:
            raise InternalError(f"libavoid produced no route for connector {connector_key!r}")
        return [(route[i].x, route[i].y) for i in range(route.size)]


def _side_vis_dir(avoid, side: str):
    # ConnDirFlag is the OUTWARD perpendicular of the pin's side: it is the
    # direction the connector leaves the shape.  Top -> Up, bottom -> Down,
    # left -> Left, right -> Right.  Inverting any of these makes libavoid
    # route around the shape to satisfy portDirectionPenalty.
    if side == "top":
        return avoid.ConnDirFlag.ConnDirUp
    if side == "bottom":
        return avoid.ConnDirFlag.ConnDirDown
    if side == "left":
        return avoid.ConnDirFlag.ConnDirLeft
    if side == "right":
        return avoid.ConnDirFlag.ConnDirRight
    raise InternalError(f"invalid pin side: {side!r}")


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
    raise InternalError(f"invalid pin side: {side!r}")


__all__ = [
    "CROSSING_PENALTY",
    "FIXED_SHARED_PATH_PENALTY",
    "IDEAL_NUDGING_DISTANCE",
    "PORT_DIRECTION_PENALTY",
    "SEGMENT_PENALTY",
    "SHAPE_BUFFER_DISTANCE",
    "RoutingContext",
]
