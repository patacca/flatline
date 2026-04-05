"""Pure layout helpers for flatline.xray."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flatline.models import PcodeOpInfo, VarnodeInfo

NodeId = tuple[str, int]

LABEL_ELLIPSIS = "..."
OPCODE_LABEL_MAX_CHARS = 7
VARNODE_LABEL_MAX_CHARS = 8
OPCODE_CHAR_WIDTH = 8.0
VARNODE_CHAR_WIDTH = 8.0
OPCODE_WIDTH_PAD = 28.0
VARNODE_WIDTH_PAD = 20.0
OPCODE_NODE_HEIGHT = 76.0
VARNODE_NODE_HEIGHT = 68.0
OPCODE_MIN_WIDTH = 76.0
CONSTANT_VARNODE_MIN_WIDTH = 74.0
VARNODE_MIN_WIDTH = 68.0
HORIZONTAL_NODE_GAP = 30.0
VERTICAL_LEVEL_GAP = 132.0


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
    child_gap: float = HORIZONTAL_NODE_GAP,
    node_width_pad: float = HORIZONTAL_NODE_GAP,
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
    level_gap: float = VERTICAL_LEVEL_GAP,
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
    child_gap: float = HORIZONTAL_NODE_GAP,
    level_gap: float = VERTICAL_LEVEL_GAP,
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


def shorten_label(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if len(text) <= max_chars:
        return text
    if max_chars <= len(LABEL_ELLIPSIS):
        return text[:max_chars]
    return f"{text[: max_chars - len(LABEL_ELLIPSIS)]}{LABEL_ELLIPSIS}"


def fit_opcode_label(opcode: str, max_chars: int = OPCODE_LABEL_MAX_CHARS) -> str:
    return shorten_label(opcode, max_chars)


def varnode_badge(varnode) -> str:
    if varnode.flags.is_constant:
        return "CONST"
    if varnode.flags.is_input:
        return "INPUT"
    if varnode.space == "register":
        return "REGISTER"
    if varnode.space == "ram":
        return "RAM"
    if varnode.space == "unique":
        return "TEMP"
    return varnode.space.upper()


def fit_varnode_badge(varnode, max_chars: int = VARNODE_LABEL_MAX_CHARS) -> str:
    return shorten_label(varnode_badge(varnode), max_chars)


def node_label_lines(
    node: VisualNode,
    op_by_id: Mapping[int, PcodeOpInfo],
    varnode_by_id: Mapping[int, VarnodeInfo],
) -> tuple[str, ...]:
    if node.actual[0] == "op":
        op = op_by_id[node.actual[1]]
        return (*fit_opcode_label(op.opcode).splitlines(), f"#{op.id}")
    varnode = varnode_by_id[node.actual[1]]
    return (fit_varnode_badge(varnode), f"v{varnode.id}")


def node_size(
    node: VisualNode,
    op_by_id: Mapping[int, PcodeOpInfo],
    varnode_by_id: Mapping[int, VarnodeInfo],
) -> tuple[float, float]:
    """Return the node size used by the drawing code."""

    label_lines = node_label_lines(node, op_by_id, varnode_by_id)
    label_width = max(len(line) for line in label_lines)
    if node.actual[0] == "op":
        width = max(OPCODE_MIN_WIDTH, label_width * OPCODE_CHAR_WIDTH + OPCODE_WIDTH_PAD)
        return (width, OPCODE_NODE_HEIGHT)
    varnode = varnode_by_id[node.actual[1]]
    width = max(label_width * VARNODE_CHAR_WIDTH + VARNODE_WIDTH_PAD, VARNODE_MIN_WIDTH)
    if varnode.flags.is_constant:
        return (max(width, CONSTANT_VARNODE_MIN_WIDTH), VARNODE_NODE_HEIGHT)
    return (width, VARNODE_NODE_HEIGHT)


def node_pad(
    node: VisualNode,
    op_by_id: Mapping[int, PcodeOpInfo],
    varnode_by_id: Mapping[int, VarnodeInfo],
) -> float:
    """Return the node radius used for edge attachment."""

    return node_size(node, op_by_id, varnode_by_id)[1] / 2.0


__all__ = [
    "HORIZONTAL_NODE_GAP",
    "VERTICAL_LEVEL_GAP",
    "NodeId",
    "VisualNode",
    "assign_forest_positions",
    "build_visual_forest",
    "collect_visual_nodes",
    "compute_canvas_size",
    "fit_opcode_label",
    "fit_varnode_badge",
    "measure_forest",
    "node_label_lines",
    "node_pad",
    "node_size",
    "shorten_label",
    "sink_ops",
    "sorted_ops",
    "varnode_badge",
]
