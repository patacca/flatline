"""Helpers for indexing visual subtrees and collecting CPG overlay edges.

This module keeps control-flow overlay bookkeeping out of ``_graph_window``.
It maps visual subtrees back to instruction addresses and pcode op ids, then
uses those indexes to resolve typed ``Cbranch`` operations into overlay edges.
"""

from __future__ import annotations

import tkinter as tk
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from flatline.models.pcode_ops.branch import Cbranch
from flatline.models.varnodes import FspecVarnode, IopVarnode
from flatline.xray._cpg_routing import (
    OverlayEdge,
    OverlayShape,
    route_overlay_edges,
    visual_node_shape,
)
from flatline.xray._layout import node_size
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


def draw_cbranch_edges(
    canvas: tk.Canvas,
    cbranch_edges: list[tuple[VisualNode, VisualNode, str]],
    op_by_id: dict,
    varnode_by_id: dict,
    visual_nodes: Sequence[VisualNode] = (),
) -> None:
    """Draw true/false conditional branch overlay edges on the canvas.

    Each edge runs from the bottom of *source* to the top of *target* using
    libavoid orthogonal routing.  Sibling source pins are spread across the
    bottom side via slot indices so multiple outgoing branches do not stack.
    True branches are green, false branches red.
    """
    if not cbranch_edges:
        return

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

    shapes = _build_overlay_shapes(visual_nodes, op_by_id, varnode_by_id)
    routes = route_overlay_edges(overlay_edges, shapes)

    for polyline, (_source, _target, branch_type) in zip(routes, cbranch_edges, strict=True):
        color = CBRANCH_TRUE_COLOR if branch_type == "true" else CBRANCH_FALSE_COLOR
        coords = [coord for point in polyline for coord in point]
        canvas.create_line(
            *coords,
            fill=color,
            width=1.8,
            arrow=tk.LAST,
            arrowshape=(12, 14, 6),
            tags=("cbranch_edge", "arrow_edge"),
        )


def draw_iop_edges(
    canvas: tk.Canvas,
    iop_edges: list[tuple[VisualNode, VisualNode]],
    op_by_id: dict,
    varnode_by_id: dict,
    visual_nodes: Sequence[VisualNode] = (),
) -> None:
    """Draw IOP reference overlay edges on the canvas.

    Each edge is routed by libavoid between the nearest horizontal sides of
    *source* and *target*; an ``insideOffset`` stub of ``_IOP_STUB_PX`` is
    requested at the source pin so the connector emerges with a visible
    horizontal departure even when nodes are vertically aligned.  IOP edges
    use an amber dashed style to distinguish them from data-flow and
    control-flow edges.
    """
    if not iop_edges:
        return

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

    shapes = _build_overlay_shapes(visual_nodes, op_by_id, varnode_by_id)
    routes = route_overlay_edges(overlay_edges, shapes)

    for polyline in routes:
        coords = [coord for point in polyline for coord in point]
        canvas.create_line(
            *coords,
            fill=IOP_EDGE_COLOR,
            width=1.4,
            dash=IOP_EDGE_DASH,
            arrow=tk.LAST,
            arrowshape=(10, 12, 5),
            tags=("iop_edge", "arrow_edge"),
        )


def draw_fspec_edges(
    canvas: tk.Canvas,
    fspec_edges: list[tuple[VisualNode, str]],
    op_by_id: dict,
    varnode_by_id: dict,
    visual_nodes: Sequence[VisualNode] = (),
) -> None:
    """Draw fspec call-target overlay edges with virtual destination boxes.

    For each ``(source_node, label)`` pair a small virtual rectangle is drawn
    to the right of *source*, registered with the router as both an endpoint
    shape (so the connector lands on it) and as an obstacle for sibling
    edges.  The connector is routed by libavoid between the right side of
    *source* and the left side of the virtual box.
    """
    if not fspec_edges:
        return

    vw, vh = 40, 10
    virtual_positions: list[tuple[float, float]] = []
    virtual_keys: list[str] = []
    for index, (source, _label) in enumerate(fspec_edges):
        sw, sh = node_size(source, op_by_id, varnode_by_id)
        vx = source.x + sw * 1.5
        vy = source.y + sh * 0.6 * index
        virtual_positions.append((vx, vy))
        virtual_keys.append(make_virtual_node_id(_label, index))

    overlay_edges: list[OverlayEdge] = []
    for (source, _label), virtual_key in zip(fspec_edges, virtual_keys, strict=True):
        overlay_edges.append(
            OverlayEdge(
                source_key=source.key,
                target_key=virtual_key,
                source_side="right",
                target_side="left",
            )
        )

    shapes = _build_overlay_shapes(visual_nodes, op_by_id, varnode_by_id)
    # Virtual destination boxes participate as endpoint shapes; their drawn
    # half-extents are (vw, vh) so the OverlayShape uses (vw*2, vh*2).
    for virtual_key, (vx, vy) in zip(virtual_keys, virtual_positions, strict=True):
        shapes.append(
            OverlayShape(key=virtual_key, cx=vx, cy=vy, w=float(vw * 2), h=float(vh * 2))
        )

    routes = route_overlay_edges(overlay_edges, shapes)

    for polyline, (_source, label), virtual_key, (vx, vy) in zip(
        routes, fspec_edges, virtual_keys, virtual_positions, strict=True
    ):
        canvas.create_rectangle(
            vx - vw,
            vy - vh,
            vx + vw,
            vy + vh,
            outline=FSPEC_EDGE_COLOR,
            fill=CANVAS_BG,
            tags=(virtual_key, "fspec_virtual_node"),
        )
        canvas.create_text(
            vx,
            vy,
            text=label,
            fill=FSPEC_EDGE_COLOR,
            font=("Courier", 8),
            tags=(virtual_key, "fspec_virtual_node"),
        )
        coords = [coord for point in polyline for coord in point]
        canvas.create_line(
            *coords,
            fill=FSPEC_EDGE_COLOR,
            width=1.4,
            dash=(4, 3),
            arrow=tk.LAST,
            arrowshape=(10, 12, 5),
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
