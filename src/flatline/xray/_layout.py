"""Pure layout helpers for flatline.xray."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flatline.models import PcodeOpInfo, VarnodeInfo

NodeId = tuple[str, int]


@dataclass
class VisualNode:
    """One node in the visual tree."""

    key: str
    actual: NodeId
    depth: int
    children: list[VisualNode] = field(default_factory=list)
    span: float = 0.0
    x: float = 0.0
    y: float = 0.0


def sorted_ops(pcode_ops: Sequence[PcodeOpInfo]) -> list[PcodeOpInfo]:
    """Return pcode ops in stable visual order."""

    return sorted(
        pcode_ops,
        key=lambda op: (
            op.instruction_address,
            op.sequence_time,
            op.sequence_order,
            op.id,
        ),
    )


def sink_ops(
    sorted_pcode_ops: Sequence[PcodeOpInfo],
    varnode_by_id: Mapping[int, VarnodeInfo],
) -> list[PcodeOpInfo]:
    """Return root candidates for the visual forest."""

    sinks: list[PcodeOpInfo] = []
    for op in sorted_pcode_ops:
        output_id = op.output_varnode_id
        if output_id is None:
            sinks.append(op)
            continue
        output_varnode = varnode_by_id.get(output_id)
        if output_varnode is None or not output_varnode.use_op_ids:
            sinks.append(op)
    if sinks:
        return sinks
    return list(sorted_pcode_ops[-1:]) if sorted_pcode_ops else []


def build_visual_forest(
    op_by_id: Mapping[int, PcodeOpInfo],
    varnode_by_id: Mapping[int, VarnodeInfo],
    sorted_pcode_ops: Sequence[PcodeOpInfo],
) -> tuple[list[VisualNode], list[tuple[VisualNode, VisualNode]]]:
    """Build the visual forest plus any cross edges between reused nodes."""

    placed: dict[NodeId, VisualNode] = {}
    cross_edges: list[tuple[VisualNode, VisualNode]] = []
    counter = 0

    def new_node(actual: NodeId, depth: int) -> VisualNode:
        nonlocal counter
        counter += 1
        return VisualNode(key=f"n{counter}", actual=actual, depth=depth)

    def build_op_subtree(
        op_id: int,
        *,
        depth: int,
        active_ops: set[int],
        active_varnodes: set[int],
    ) -> VisualNode:
        node = new_node(("op", op_id), depth)
        placed[("op", op_id)] = node
        if op_id in active_ops:
            return node

        active_ops.add(op_id)
        op = op_by_id[op_id]
        for varnode_id in op.input_varnode_ids:
            if varnode_id not in varnode_by_id:
                continue
            vkey = ("varnode", varnode_id)
            if vkey in placed:
                cross_edges.append((node, placed[vkey]))
                continue
            node.children.append(
                build_varnode_subtree(
                    varnode_id,
                    depth=depth + 1,
                    active_ops=active_ops,
                    active_varnodes=active_varnodes,
                )
            )
        active_ops.remove(op_id)
        return node

    def build_varnode_subtree(
        varnode_id: int,
        *,
        depth: int,
        active_ops: set[int],
        active_varnodes: set[int],
    ) -> VisualNode:
        node = new_node(("varnode", varnode_id), depth)
        placed[("varnode", varnode_id)] = node
        if varnode_id in active_varnodes:
            return node

        varnode = varnode_by_id[varnode_id]
        defining_op_id = varnode.defining_op_id
        if (
            defining_op_id is None
            or varnode.flags.is_constant
            or varnode.flags.is_input
            or defining_op_id not in op_by_id
        ):
            return node

        okey = ("op", defining_op_id)
        if okey in placed:
            cross_edges.append((node, placed[okey]))
            return node

        active_varnodes.add(varnode_id)
        node.children.append(
            build_op_subtree(
                defining_op_id,
                depth=depth + 1,
                active_ops=active_ops,
                active_varnodes=active_varnodes,
            )
        )
        active_varnodes.remove(varnode_id)
        return node

    roots: list[VisualNode] = []
    for op in sink_ops(sorted_pcode_ops, varnode_by_id):
        if ("op", op.id) in placed:
            continue
        roots.append(
            build_op_subtree(
                op.id,
                depth=0,
                active_ops=set(),
                active_varnodes=set(),
            )
        )

    for op in sorted_pcode_ops:
        if ("op", op.id) not in placed:
            roots.append(
                build_op_subtree(
                    op.id,
                    depth=0,
                    active_ops=set(),
                    active_varnodes=set(),
                )
            )

    return roots, cross_edges


def collect_visual_nodes(roots: Sequence[VisualNode]) -> list[VisualNode]:
    """Flatten the forest into a depth-first list."""

    nodes: list[VisualNode] = []

    def walk(node: VisualNode) -> None:
        nodes.append(node)
        for child in node.children:
            walk(child)

    for root in roots:
        walk(root)
    return nodes


def measure_forest(
    roots: Sequence[VisualNode],
    node_size: Callable[[VisualNode], tuple[float, float]],
    *,
    child_gap: float = 26.0,
    node_width_pad: float = 26.0,
) -> int:
    """Measure spans for each node and return the maximum depth."""

    max_depth = 0

    def measure(node: VisualNode) -> float:
        nonlocal max_depth
        max_depth = max(max_depth, node.depth)
        own_width = node_size(node)[0] + node_width_pad
        if not node.children:
            node.span = own_width
            return node.span

        child_spans = [measure(child) for child in node.children]
        children_width = sum(child_spans) + child_gap * (len(node.children) - 1)
        node.span = max(own_width, children_width + 18.0)
        return node.span

    for root in roots:
        measure(root)
    return max_depth


def compute_canvas_size(
    roots: Sequence[VisualNode],
    max_depth: int,
    *,
    root_gap: float = 100.0,
    top_margin: float = 90.0,
    bottom_margin: float = 120.0,
    side_margin: float = 100.0,
    level_gap: float = 122.0,
) -> tuple[int, int]:
    """Compute the virtual canvas size for the measured forest."""

    if not roots:
        return (1400, 940)

    total_width = sum(root.span for root in roots)
    if len(roots) > 1:
        total_width += root_gap * (len(roots) - 1)
    width = max(1400, int(total_width + side_margin * 2))
    height = max(
        940,
        int(top_margin + bottom_margin + max_depth * level_gap + 120),
    )
    return (width, height)


def assign_forest_positions(
    roots: Sequence[VisualNode],
    virtual_height: int,
    *,
    side_margin: float = 100.0,
    bottom_margin: float = 120.0,
    root_gap: float = 100.0,
    child_gap: float = 26.0,
    level_gap: float = 122.0,
) -> None:
    """Assign x/y coordinates to the measured forest."""

    def assign(node: VisualNode, left: float) -> None:
        node.x = left + node.span / 2.0
        node.y = virtual_height - bottom_margin - node.depth * level_gap
        if not node.children:
            return

        children_width = sum(child.span for child in node.children) + child_gap * (
            len(node.children) - 1
        )
        child_left = left + (node.span - children_width) / 2.0
        for child in node.children:
            assign(child, child_left)
            child_left += child.span + child_gap

    left = side_margin
    for root in roots:
        assign(root, left)
        left += root.span + root_gap


def node_size(
    node: VisualNode,
    varnode_by_id: Mapping[int, VarnodeInfo],
) -> tuple[float, float]:
    """Return the node size used by the drawing code."""

    if node.actual[0] == "op":
        return (76.0, 76.0)
    varnode = varnode_by_id[node.actual[1]]
    if varnode.flags.is_constant:
        return (74.0, 68.0)
    return (68.0, 68.0)


def node_pad(
    node: VisualNode,
    varnode_by_id: Mapping[int, VarnodeInfo],
) -> float:
    """Return the node radius used for edge attachment."""

    return node_size(node, varnode_by_id)[1] / 2.0


__all__ = [
    "NodeId",
    "VisualNode",
    "assign_forest_positions",
    "build_visual_forest",
    "collect_visual_nodes",
    "compute_canvas_size",
    "measure_forest",
    "node_pad",
    "node_size",
    "sink_ops",
    "sorted_ops",
]
