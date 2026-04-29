"""Unified overlay routing + drawing pipeline for the X-Ray graph window.

Collects all CPG overlay edges (IOP, fspec, optional cbranch), builds their
libavoid specs, routes the main pcode graph and all overlay families inside
a single shared libavoid Router so its nudging keeps overlay segments off
main edges, then draws main edges, nodes and overlay edges in the correct
z-order.  Extracted from ``_graph_window`` to keep that module under the
600-line cap.
"""

# pyright: reportImplicitRelativeImport=false

from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

from flatline.xray._canvas import draw_nodes, draw_routed_edges
from flatline.xray._cpg_overlay import (
    build_address_to_roots,
    build_cbranch_overlay_specs,
    build_fspec_overlay_plan,
    build_iop_overlay_specs,
    build_opid_to_node,
    build_opid_to_root,
    build_vnid_to_node,
    collect_cbranch_edges,
    collect_fspec_edges,
    collect_iop_edges,
    draw_cbranch_edges,
    draw_fspec_edges,
    draw_iop_edges,
)
from flatline.xray._unified_routing import OverlayFamily, route_all

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    import networkx as nx

    from flatline.models import Pcode
    from flatline.xray._layout import LayoutResult, VisualNode


def render_graph_with_overlays(
    canvas: tk.Canvas,
    *,
    layout: LayoutResult,
    pcode_graph: nx.MultiDiGraph,
    pcode: Pcode,
    visual_roots: Sequence[VisualNode],
    visual_nodes: Sequence[VisualNode],
    op_by_id: dict,
    varnode_by_id: dict,
    function_info,
    show_node: Callable[[VisualNode], None],
    cpg_enabled: bool,
) -> None:
    opid_to_root = build_opid_to_root(visual_roots, op_by_id)
    opid_to_node = build_opid_to_node(visual_roots)
    vnid_to_node = build_vnid_to_node(visual_roots)
    iop_edges = collect_iop_edges(varnode_by_id, opid_to_node, vnid_to_node)
    fspec_edges = collect_fspec_edges(varnode_by_id, opid_to_root, function_info)
    cbranch_edges: list = []
    if cpg_enabled:
        addr_to_roots = build_address_to_roots(visual_roots, op_by_id)
        cbranch_edges = collect_cbranch_edges(pcode.pcode_ops, addr_to_roots, opid_to_root)

    iop_specs = build_iop_overlay_specs(iop_edges)
    fspec_plan = build_fspec_overlay_plan(fspec_edges, op_by_id, varnode_by_id)
    cbranch_specs = build_cbranch_overlay_specs(cbranch_edges)
    families = [
        OverlayFamily(name="iop", edges=iop_specs),
        OverlayFamily(
            name="fspec", edges=fspec_plan.edges, virtual_shapes=fspec_plan.virtual_shapes
        ),
        OverlayFamily(name="cbranch", edges=cbranch_specs),
    ]
    unified = route_all(layout, pcode_graph, families)

    draw_routed_edges(canvas, unified.main, layout)
    for root in visual_roots:
        draw_nodes(canvas, root, op_by_id, varnode_by_id, show_node)
    # CPG overlay: IOP + fspec always drawn; CBRANCH only when CPG enabled.
    draw_iop_edges(
        canvas,
        iop_edges,
        op_by_id,
        varnode_by_id,
        visual_nodes,
        precomputed_routes=unified.overlays["iop"],
    )
    draw_fspec_edges(
        canvas,
        fspec_edges,
        op_by_id,
        varnode_by_id,
        visual_nodes,
        precomputed_routes=unified.overlays["fspec"],
        precomputed_plan=fspec_plan,
    )
    if cpg_enabled:
        draw_cbranch_edges(
            canvas,
            cbranch_edges,
            op_by_id,
            varnode_by_id,
            visual_nodes,
            precomputed_routes=unified.overlays["cbranch"],
        )


__all__ = ["render_graph_with_overlays"]
