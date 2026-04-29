"""Unified main-graph + CPG-overlay routing in a single libavoid transaction.

Routes the pcode dataflow graph and all CPG overlay edges (cbranch / IOP /
fspec) through one shared ``RoutingContext`` so libavoid's nudging and
crossing penalty can spread overlay segments away from main edges that
would otherwise share the same horizontal/vertical corridor.
"""

# pyright: reportAttributeAccessIssue=false, reportImplicitRelativeImport=false, reportIndexIssue=false, reportMissingTypeArgument=false

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from flatline._errors import InternalError
from flatline.xray._edge_routing import main_routes, register_main_graph
from flatline.xray._routing_context import RoutingContext

if TYPE_CHECKING:
    import networkx as nx

    from flatline.xray._cpg_routing import OverlayEdge, OverlayShape
    from flatline.xray._layout import LayoutResult


@dataclass(frozen=True)
class OverlayFamily:
    """One named family of overlay edges to route alongside the main graph.

    ``name`` distinguishes families when allocating per-shape pin classes
    (``cbranch`` / ``iop`` / ``fspec``).  ``edges`` is the list of overlay
    edges and ``virtual_shapes`` lists extra rectangles that act as both
    endpoint shapes and obstacles (used today only by fspec virtual boxes).
    """

    name: str
    edges: Sequence[OverlayEdge]
    virtual_shapes: Sequence[OverlayShape] = ()


@dataclass(frozen=True)
class UnifiedRoutes:
    """Result of one unified routing pass.

    ``main`` mirrors the dict returned by the standalone ``route_edges``.
    ``overlays`` maps each overlay-family name to a list of polylines
    parallel to its input ``edges`` list.
    """

    main: dict[tuple, list[tuple[float, float]]]
    overlays: dict[str, list[list[tuple[float, float]]]]


def _register_overlay_family(
    ctx: RoutingContext,
    family: OverlayFamily,
) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    for index, edge in enumerate(family.edges):
        if not ctx.has_shape(edge.source_key):
            raise InternalError(
                f"overlay edge {family.name}#{index} references unknown source shape "
                f"{edge.source_key!r}"
            )
        if not ctx.has_shape(edge.target_key):
            raise InternalError(
                f"overlay edge {family.name}#{index} references unknown target shape "
                f"{edge.target_key!r}"
            )

        target_pin_key = ("overlay-target", family.name, edge.target_side)
        target_class = ctx.ensure_pin(
            edge.target_key,
            target_pin_key,
            side=edge.target_side,
        )

        source_pin_key = ("overlay-source", family.name, index)
        source_class = ctx.ensure_pin(
            edge.source_key,
            source_pin_key,
            side=edge.source_side,
            slot_index=edge.source_slot_index,
            slot_count=edge.source_slot_count,
            inset_px=edge.inset_px,
        )

        connector_key = ("overlay", family.name, index)
        ctx.add_connector(
            connector_key,
            edge.source_key,
            source_class,
            edge.target_key,
            target_class,
        )
        keys.append((family.name, str(index)))
    return keys


def route_all(
    layout: LayoutResult,
    pcode_graph: nx.MultiDiGraph,
    overlay_families: Sequence[OverlayFamily] = (),
) -> UnifiedRoutes:
    """Route main edges and overlay families inside one libavoid transaction.

    All shapes referenced by overlay edges must either belong to *layout*
    (real visual nodes) or be supplied via an overlay family's
    ``virtual_shapes``.  Virtual shapes are registered as ordinary
    rectangles, so they participate as both endpoints and obstacles for the
    main router.
    """
    ctx = RoutingContext.create()
    self_loops = register_main_graph(ctx, layout, pcode_graph)

    for family in overlay_families:
        for shape in family.virtual_shapes:
            ctx.add_shape(shape.key, shape.cx, shape.cy, shape.w, shape.h)

    for family in overlay_families:
        _register_overlay_family(ctx, family)

    ctx.process()

    overlays: dict[str, list[list[tuple[float, float]]]] = {}
    for family in overlay_families:
        overlays[family.name] = [
            ctx.route_for(("overlay", family.name, index)) for index in range(len(family.edges))
        ]

    return UnifiedRoutes(
        main=main_routes(ctx, pcode_graph, self_loops),
        overlays=overlays,
    )


__all__ = [
    "OverlayFamily",
    "UnifiedRoutes",
    "route_all",
]
