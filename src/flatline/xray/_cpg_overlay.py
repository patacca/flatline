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
from flatline.xray._canvas import manhattan_route, nearest_side_anchors, node_pad
from flatline.xray._theme import (
    CBRANCH_FALSE_COLOR,
    CBRANCH_TRUE_COLOR,
    IOP_EDGE_COLOR,
    IOP_EDGE_DASH,
)

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
    op_by_id: dict,
    opid_to_root: dict[int, VisualNode],
) -> list[tuple[VisualNode, VisualNode]]:
    """Collect overlay edges for IOP (internal op pointer) varnodes."""
    edges: list[tuple[VisualNode, VisualNode]] = []
    for vn in varnode_by_id.values():
        if not isinstance(vn, IopVarnode):
            continue
        if vn.target_op_id is None:
            continue
        target_root = opid_to_root.get(vn.target_op_id)
        if target_root is None:
            continue
        if not vn.use_op_ids:
            continue
        source_root = opid_to_root.get(vn.use_op_ids[0])
        if source_root is None:
            continue
        edges.append((source_root, target_root))
    return edges


def make_virtual_node_id(label: str, index: int) -> str:
    """Create a deterministic id for a virtual (off-graph) overlay node."""

    return f"fspec_virtual_{index}"


def collect_fspec_edges(
    varnode_by_id: dict,
    op_by_id: dict,
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


def draw_cbranch_edges(
    canvas: tk.Canvas,
    cbranch_edges: list[tuple[VisualNode, VisualNode, str]],
    op_by_id: dict,
    varnode_by_id: dict,
) -> None:
    """Draw true/false conditional branch overlay edges on the canvas.

    Each edge runs from the bottom of *source* to the top of *target* using
    orthogonal Manhattan routing.  True branches are green, false branches red.
    """

    for source, target, branch_type in cbranch_edges:
        sx = source.x
        sy = source.y + node_pad(source, op_by_id, varnode_by_id)
        tx = target.x
        ty = target.y - node_pad(target, op_by_id, varnode_by_id)
        color = CBRANCH_TRUE_COLOR if branch_type == "true" else CBRANCH_FALSE_COLOR
        coords = manhattan_route(sx, sy, tx, ty)
        canvas.create_line(
            *coords,
            fill=color,
            width=1.8,
            arrow=tk.LAST,
            arrowshape=(12, 14, 6),
            tags=("cbranch_edge",),
        )


def draw_iop_edges(
    canvas: tk.Canvas,
    iop_edges: list[tuple[VisualNode, VisualNode]],
    op_by_id: dict,
    varnode_by_id: dict,
) -> None:
    """Draw IOP reference overlay edges on the canvas.

    Each edge runs between the nearest horizontal sides of *source* and *target*
    using orthogonal Manhattan routing.  IOP edges use an amber dashed style to
    distinguish them from data-flow and control-flow edges.
    """
    for source, target in iop_edges:
        (sx, sy), (tx, ty) = nearest_side_anchors(source, target, op_by_id, varnode_by_id)
        coords = manhattan_route(sx, sy, tx, ty)
        canvas.create_line(
            *coords,
            fill=IOP_EDGE_COLOR,
            width=1.4,
            dash=IOP_EDGE_DASH,
            arrow=tk.LAST,
            arrowshape=(10, 12, 5),
            tags=("iop_edge",),
        )


__all__ = [
    "build_address_to_roots",
    "build_opid_to_root",
    "collect_cbranch_edges",
    "collect_fspec_edges",
    "collect_iop_edges",
    "draw_cbranch_edges",
    "draw_iop_edges",
    "make_virtual_node_id",
]
