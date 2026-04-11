"""Helpers for indexing visual subtrees and collecting CPG overlay edges.

This module keeps control-flow overlay bookkeeping out of ``_graph_window``.
It maps visual subtrees back to instruction addresses and pcode op ids, then
uses those indexes to resolve typed ``Cbranch`` operations into overlay edges.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from flatline.models.pcode_ops.branch import Cbranch

if TYPE_CHECKING:
    from flatline.models import PcodeOpInfo
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


__all__ = [
    "build_address_to_roots",
    "build_opid_to_root",
    "collect_cbranch_edges",
]
