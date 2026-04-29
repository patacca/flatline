"""Helpers for indexing visual subtrees and collecting CPG overlay edges.

This module keeps control-flow overlay bookkeeping out of ``_graph_window``.
It maps visual subtrees back to instruction addresses and pcode op ids, then
uses those indexes to resolve typed ``Cbranch`` operations into overlay edges.
"""

from __future__ import annotations

import tkinter as tk
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from flatline.models.pcode_ops.branch import Cbranch
from flatline.models.varnodes import FspecVarnode, IopVarnode
from flatline.xray._cpg_routing import (
    OverlayEdge,
    OverlayShape,
    route_overlay_edges,
    visual_node_shape,
)
from flatline.xray._edge_anchoring import anchor_polyline_endpoints
from flatline.xray._layout import Position, node_size
from flatline.xray._theme import (
    BODY_FONT,
    CANVAS_BG,
    CBRANCH_FALSE_COLOR,
    CBRANCH_TRUE_COLOR,
    FSPEC_EDGE_COLOR,
    IOP_EDGE_COLOR,
    IOP_EDGE_DASH,
    PANEL_BG,
    PANEL_TITLE_FONT,
    TEXT,
)

# Minimum horizontal stub (pixels) added to IOP edge anchors so that the
# horizontal departure segment is always visible.
_IOP_STUB_PX = 15.0


def _visual_node_position(
    node: VisualNode,
    op_by_id: Mapping,
    varnode_by_id: Mapping,
) -> Position:
    w, h = node_size(node, op_by_id, varnode_by_id)
    return Position(x=node.x, y=node.y, w=w, h=h)


if TYPE_CHECKING:
    from flatline.models import PcodeOpInfo
    from flatline.models.types import FunctionInfo
    from flatline.xray._layout import VisualNode


def build_address_to_roots(
    visual_roots: Sequence[VisualNode],
    op_by_id: Mapping[int, PcodeOpInfo],
) -> dict[int, list[VisualNode]]:
    """Map each instruction address to every visual root that contains it."""

    address_to_roots: dict[int, list[VisualNode]] = defaultdict(list)

    def walk(node: VisualNode, subtree_root: VisualNode) -> None:
        if node.actual[0] == "op":
            op = op_by_id.get(node.actual[1])
            if op is not None:
                address_to_roots[op.instruction_address].append(subtree_root)
        for child in node.children:
            walk(child, subtree_root)

    for root in visual_roots:
        walk(root, root)
    return dict(address_to_roots)


def build_opid_to_root(
    visual_roots: Sequence[VisualNode],
    op_by_id: Mapping[int, PcodeOpInfo],
) -> dict[int, VisualNode]:
    """Map each visualized pcode op id to the root of its containing subtree."""

    opid_to_root: dict[int, VisualNode] = {}

    def walk(node: VisualNode, subtree_root: VisualNode) -> None:
        if node.actual[0] == "op" and node.actual[1] in op_by_id:
            opid_to_root[node.actual[1]] = subtree_root
        for child in node.children:
            walk(child, subtree_root)

    for root in visual_roots:
        walk(root, root)
    return opid_to_root


def build_opid_to_node(
    visual_roots: Sequence[VisualNode],
) -> dict[int, VisualNode]:
    """Map each visualized pcode op id to its own visual node."""

    opid_to_node: dict[int, VisualNode] = {}

    def walk(node: VisualNode) -> None:
        if node.actual[0] == "op":
            opid_to_node[node.actual[1]] = node
        for child in node.children:
            walk(child)

    for root in visual_roots:
        walk(root)
    return opid_to_node


def build_vnid_to_node(
    visual_roots: Sequence[VisualNode],
) -> dict[int, VisualNode]:
    """Map each visualized varnode id to its own visual node."""

    vnid_to_node: dict[int, VisualNode] = {}

    def walk(node: VisualNode) -> None:
        if node.actual[0] == "varnode":
            vnid_to_node[node.actual[1]] = node
        for child in node.children:
            walk(child)

    for root in visual_roots:
        walk(root)
    return vnid_to_node


def collect_cbranch_edges(
    pcode_ops: Sequence[PcodeOpInfo],
    addr_to_roots: Mapping[int, Sequence[VisualNode]],
    opid_to_root: Mapping[int, VisualNode],
) -> list[tuple[VisualNode, VisualNode, str]]:
    """Collect true/false overlay edges for typed conditional branch ops."""

    edges: list[tuple[VisualNode, VisualNode, str]] = []
    for op in pcode_ops:
        if not isinstance(op, Cbranch):
            continue

        source_root = opid_to_root.get(op.id)
        if source_root is None:
            continue

        for label, target_address in (
            ("true", op.true_target_address),
            ("false", op.false_target_address),
        ):
            if target_address is None:
                continue
            for target_root in addr_to_roots.get(target_address, ()):
                edges.append((source_root, target_root, label))
    return edges


def collect_iop_edges(
    varnode_by_id: dict,
    opid_to_node: dict[int, VisualNode],
    vnid_to_node: dict[int, VisualNode],
) -> list[tuple[VisualNode, VisualNode]]:
    """Collect overlay edges for IOP (internal op pointer) varnodes.

    Each edge runs from the IOP varnode's own visual node to the visual node
    of the target pcode op it references.
    """
    edges: list[tuple[VisualNode, VisualNode]] = []
    for vn in varnode_by_id.values():
        if not isinstance(vn, IopVarnode):
            continue
        if vn.target_op_id is None:
            continue
        target_node = opid_to_node.get(vn.target_op_id)
        if target_node is None:
            continue
        source_node = vnid_to_node.get(vn.id)
        if source_node is None:
            continue
        edges.append((source_node, target_node))
    return edges


def make_virtual_node_id(label: str, index: int) -> str:
    """Create a deterministic id for a virtual (off-graph) overlay node."""

    return f"fspec_virtual_{index}"


def collect_fspec_edges(
    varnode_by_id: dict,
    opid_to_root: dict[int, VisualNode],
    function_info: FunctionInfo | None,
) -> list[tuple[VisualNode, str]]:
    """Collect overlay edges for FSPEC (call-spec) varnodes.

    Each valid fspec varnode produces a ``(source_root, label)`` pair where
    *label* is the hex callee address (e.g. ``"0x401000"``).  Varnodes that
    lack a resolvable call site are silently skipped.
    """

    edges: list[tuple[VisualNode, str]] = []
    for vn in varnode_by_id.values():
        if not isinstance(vn, FspecVarnode):
            continue
        if function_info is None:
            continue
        if vn.call_site_index is None:
            continue
        if vn.call_site_index >= len(function_info.call_sites):
            continue
        call_site = function_info.call_sites[vn.call_site_index]
        if call_site.target_address is None:
            continue
        if not vn.use_op_ids:
            continue
        source_root = opid_to_root.get(vn.use_op_ids[0])
        if source_root is None:
            continue
        edges.append((source_root, hex(call_site.target_address)))
    return edges


def _build_overlay_shapes(
    visual_nodes: Sequence[VisualNode],
    op_by_id: dict,
    varnode_by_id: dict,
) -> list[OverlayShape]:
    return [visual_node_shape(node, op_by_id, varnode_by_id) for node in visual_nodes]


def build_cbranch_overlay_specs(
    cbranch_edges: Sequence[tuple[VisualNode, VisualNode, str]],
) -> list[OverlayEdge]:
    """Convert (source, target, branch_type) triples to libavoid overlay specs.

    Sibling source pins are spread across the bottom side via slot indices
    so multiple outgoing branches do not stack on the same emission point.
    """
    source_slot_counts: dict[str, int] = {}
    for source, _target, _branch_type in cbranch_edges:
        source_slot_counts[source.key] = source_slot_counts.get(source.key, 0) + 1
    source_slot_seen: dict[str, int] = {}
    overlay_edges: list[OverlayEdge] = []
    for source, target, _branch_type in cbranch_edges:
        source_slot_seen[source.key] = source_slot_seen.get(source.key, 0) + 1
        overlay_edges.append(
            OverlayEdge(
                source_key=source.key,
                target_key=target.key,
                source_side="bottom",
                target_side="top",
                source_slot_index=source_slot_seen[source.key],
                source_slot_count=source_slot_counts[source.key],
            )
        )
    return overlay_edges


def build_iop_overlay_specs(
    iop_edges: Sequence[tuple[VisualNode, VisualNode]],
) -> list[OverlayEdge]:
    """Convert IOP (source, target) pairs to libavoid overlay specs.

    Source side is the horizontal side nearest *target*; target side is its
    mirror.  An ``insideOffset`` stub is requested at the source pin so the
    connector emerges with a visible horizontal departure even when nodes
    are vertically aligned.
    """
    overlay_edges: list[OverlayEdge] = []
    for source, target in iop_edges:
        s_side = "right" if target.x >= source.x else "left"
        t_side = "left" if target.x >= source.x else "right"
        overlay_edges.append(
            OverlayEdge(
                source_key=source.key,
                target_key=target.key,
                source_side=s_side,
                target_side=t_side,
                inset_px=_IOP_STUB_PX,
            )
        )
    return overlay_edges


@dataclass(frozen=True)
class FspecOverlayPlan:
    """Materialized fspec overlay routing inputs.

    ``edges`` is the libavoid spec list, ``virtual_shapes`` is the matching
    list of off-graph rectangles to register as endpoint shapes, and
    ``virtual_positions`` carries the (cx, cy) used to draw the rectangle.
    All three lists are parallel to the input ``fspec_edges``.
    """

    edges: list[OverlayEdge]
    virtual_shapes: list[OverlayShape]
    virtual_positions: list[tuple[float, float]]
    virtual_half_extents: tuple[float, float]


def build_fspec_overlay_plan(
    fspec_edges: Sequence[tuple[VisualNode, str]],
    op_by_id: dict,
    varnode_by_id: dict,
) -> FspecOverlayPlan:
    """Build libavoid specs and virtual destination rectangles for fspec edges."""
    vw, vh = 40, 10
    edges: list[OverlayEdge] = []
    shapes: list[OverlayShape] = []
    positions: list[tuple[float, float]] = []
    for index, (source, label) in enumerate(fspec_edges):
        sw, sh = node_size(source, op_by_id, varnode_by_id)
        vx = source.x + sw * 1.5
        vy = source.y + sh * 0.6 * index
        virtual_key = make_virtual_node_id(label, index)
        positions.append((vx, vy))
        shapes.append(
            OverlayShape(key=virtual_key, cx=vx, cy=vy, w=float(vw * 2), h=float(vh * 2))
        )
        edges.append(
            OverlayEdge(
                source_key=source.key,
                target_key=virtual_key,
                source_side="right",
                target_side="left",
            )
        )
    return FspecOverlayPlan(
        edges=edges,
        virtual_shapes=shapes,
        virtual_positions=positions,
        virtual_half_extents=(float(vw), float(vh)),
    )


def draw_cbranch_edges(
    canvas: tk.Canvas,
    cbranch_edges: list[tuple[VisualNode, VisualNode, str]],
    op_by_id: dict,
    varnode_by_id: dict,
    visual_nodes: Sequence[VisualNode] = (),
    precomputed_routes: Sequence[Sequence[tuple[float, float]]] | None = None,
) -> None:
    """Draw true/false conditional branch overlay edges on the canvas.

    When *precomputed_routes* is supplied (one polyline per cbranch edge,
    in the same order) the libavoid call is skipped and the given
    polylines are drawn directly; this is the path used by the unified
    main+overlay routing pass in ``_graph_window``.  When omitted, the
    function performs its own self-contained libavoid routing pass for
    standalone callers and tests.  True branches are green, false branches
    red.
    """
    if not cbranch_edges:
        return

    if precomputed_routes is None:
        overlay_edges = build_cbranch_overlay_specs(cbranch_edges)
        shapes = _build_overlay_shapes(visual_nodes, op_by_id, varnode_by_id)
        routes: Sequence[Sequence[tuple[float, float]]] = route_overlay_edges(
            overlay_edges, shapes
        )
    else:
        routes = precomputed_routes

    for polyline, (_source, _target, branch_type) in zip(routes, cbranch_edges, strict=True):
        if _source.key != _target.key:
            src_pos = _visual_node_position(_source, op_by_id, varnode_by_id)
            tgt_pos = _visual_node_position(_target, op_by_id, varnode_by_id)
            polyline = anchor_polyline_endpoints(polyline, src_pos, tgt_pos, axis="vertical")
        color = CBRANCH_TRUE_COLOR if branch_type == "true" else CBRANCH_FALSE_COLOR
        coords = [coord for point in polyline for coord in point]
        canvas.create_line(
            *coords,
            fill=color,
            width=1.8,
            arrow=tk.LAST,
            arrowshape=(10, 11, 5),
            tags=("cbranch_edge", "arrow_edge"),
        )


def draw_iop_edges(
    canvas: tk.Canvas,
    iop_edges: list[tuple[VisualNode, VisualNode]],
    op_by_id: dict,
    varnode_by_id: dict,
    visual_nodes: Sequence[VisualNode] = (),
    precomputed_routes: Sequence[Sequence[tuple[float, float]]] | None = None,
) -> None:
    """Draw IOP reference overlay edges on the canvas.

    When *precomputed_routes* is supplied the libavoid call is skipped and
    the given polylines are drawn directly; this is how the unified
    main+overlay routing pass passes routes that were nudged against the
    main graph edges.  When omitted, the function performs its own
    self-contained routing pass for standalone callers and tests.  IOP
    edges use an amber dashed style to distinguish them from data-flow
    and control-flow edges.
    """
    if not iop_edges:
        return

    if precomputed_routes is None:
        overlay_edges = build_iop_overlay_specs(iop_edges)
        shapes = _build_overlay_shapes(visual_nodes, op_by_id, varnode_by_id)
        routes: Sequence[Sequence[tuple[float, float]]] = route_overlay_edges(
            overlay_edges, shapes
        )
    else:
        routes = precomputed_routes

    for polyline, (source, target) in zip(routes, iop_edges, strict=True):
        if source.key != target.key:
            src_pos = _visual_node_position(source, op_by_id, varnode_by_id)
            tgt_pos = _visual_node_position(target, op_by_id, varnode_by_id)
            polyline = anchor_polyline_endpoints(polyline, src_pos, tgt_pos, axis="horizontal")
        coords = [coord for point in polyline for coord in point]
        canvas.create_line(
            *coords,
            fill=IOP_EDGE_COLOR,
            width=1.4,
            dash=IOP_EDGE_DASH,
            arrow=tk.LAST,
            arrowshape=(8, 10, 4),
            tags=("iop_edge", "arrow_edge"),
        )


def draw_fspec_edges(
    canvas: tk.Canvas,
    fspec_edges: list[tuple[VisualNode, str]],
    op_by_id: dict,
    varnode_by_id: dict,
    visual_nodes: Sequence[VisualNode] = (),
    precomputed_routes: Sequence[Sequence[tuple[float, float]]] | None = None,
    precomputed_plan: FspecOverlayPlan | None = None,
) -> None:
    """Draw fspec call-target overlay edges with virtual destination boxes.

    When *precomputed_routes* and *precomputed_plan* are supplied together
    the libavoid call is skipped; the plan supplies the virtual rectangle
    geometry so the boxes drawn match the routed endpoints exactly.  When
    omitted, the function performs its own self-contained routing pass for
    standalone callers and tests.
    """
    if not fspec_edges:
        return

    if precomputed_routes is None:
        plan = build_fspec_overlay_plan(fspec_edges, op_by_id, varnode_by_id)
        shapes = _build_overlay_shapes(visual_nodes, op_by_id, varnode_by_id)
        shapes.extend(plan.virtual_shapes)
        routes: Sequence[Sequence[tuple[float, float]]] = route_overlay_edges(plan.edges, shapes)
    else:
        if precomputed_plan is None:
            raise ValueError(
                "draw_fspec_edges requires precomputed_plan when precomputed_routes is given"
            )
        plan = precomputed_plan
        routes = precomputed_routes

    vw, vh = plan.virtual_half_extents
    for polyline, (source, label), virtual_shape, (vx, vy) in zip(
        routes, fspec_edges, plan.virtual_shapes, plan.virtual_positions, strict=True
    ):
        canvas.create_rectangle(
            vx - vw,
            vy - vh,
            vx + vw,
            vy + vh,
            outline=FSPEC_EDGE_COLOR,
            fill=CANVAS_BG,
            tags=(virtual_shape.key, "fspec_virtual_node"),
        )
        canvas.create_text(
            vx,
            vy,
            text=label,
            fill=FSPEC_EDGE_COLOR,
            font=("Courier", 8),
            tags=(virtual_shape.key, "fspec_virtual_node"),
        )
        if source.key != virtual_shape.key:
            src_pos = _visual_node_position(source, op_by_id, varnode_by_id)
            tgt_pos = Position(x=vx, y=vy, w=float(vw * 2), h=float(vh * 2))
            polyline = anchor_polyline_endpoints(polyline, src_pos, tgt_pos, axis="horizontal")
        coords = [coord for point in polyline for coord in point]
        canvas.create_line(
            *coords,
            fill=FSPEC_EDGE_COLOR,
            width=1.4,
            dash=(4, 3),
            arrow=tk.LAST,
            arrowshape=(8, 10, 4),
            tags=("fspec_edge", "arrow_edge"),
        )


def build_checkbox_panel(
    parent: tk.Frame,
    canvas: tk.Canvas,
    cpg_enabled: bool,
) -> tk.Frame:
    """Build an edge-visibility checkbox panel for the CPG overlay.

    Returns a ``tk.Frame`` containing a labelled section with three checkboxes:
    control-flow (cbranch), IOP references, and fspec call targets.  The
    control-flow checkbox is greyed out when *cpg_enabled* is ``False``.
    """
    frame = tk.Frame(parent, bg=PANEL_BG)
    tk.Label(
        frame,
        text="Edge Visibility",
        bg=PANEL_BG,
        fg=TEXT,
        font=PANEL_TITLE_FONT,
    ).pack(anchor="w", padx=14, pady=(8, 4))

    # --- Control-flow edges (cbranch) ---
    cf_var = tk.BooleanVar(value=True)

    def _toggle_cf() -> None:
        canvas.itemconfigure("cbranch_edge", state="normal" if cf_var.get() else "hidden")

    cf_cb = tk.Checkbutton(
        frame,
        text="Control-flow edges",
        variable=cf_var,
        command=_toggle_cf,
        bg=PANEL_BG,
        fg=TEXT,
        selectcolor=PANEL_BG,
        font=BODY_FONT,
        anchor="w",
    )
    if not cpg_enabled:
        cf_cb.configure(state="disabled")
    cf_cb.pack(fill="x", padx=14, pady=2)

    # --- IOP reference edges ---
    iop_var = tk.BooleanVar(value=True)

    def _toggle_iop() -> None:
        canvas.itemconfigure("iop_edge", state="normal" if iop_var.get() else "hidden")

    tk.Checkbutton(
        frame,
        text="IOP reference edges",
        variable=iop_var,
        command=_toggle_iop,
        bg=PANEL_BG,
        fg=TEXT,
        selectcolor=PANEL_BG,
        font=BODY_FONT,
        anchor="w",
    ).pack(fill="x", padx=14, pady=2)

    # --- Call target edges (fspec) ---
    fspec_var = tk.BooleanVar(value=True)

    def _toggle_fspec() -> None:
        state = "normal" if fspec_var.get() else "hidden"
        canvas.itemconfigure("fspec_edge", state=state)
        canvas.itemconfigure("fspec_virtual_node", state=state)

    tk.Checkbutton(
        frame,
        text="Call target edges",
        variable=fspec_var,
        command=_toggle_fspec,
        bg=PANEL_BG,
        fg=TEXT,
        selectcolor=PANEL_BG,
        font=BODY_FONT,
        anchor="w",
    ).pack(fill="x", padx=14, pady=2)

    return frame


__all__ = [
    "build_address_to_roots",
    "build_checkbox_panel",
    "build_opid_to_node",
    "build_opid_to_root",
    "build_vnid_to_node",
    "collect_cbranch_edges",
    "collect_fspec_edges",
    "collect_iop_edges",
    "draw_cbranch_edges",
    "draw_fspec_edges",
    "draw_iop_edges",
    "make_virtual_node_id",
]
