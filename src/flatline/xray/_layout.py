"""Pure layout helpers for flatline.xray."""

from __future__ import annotations

import math
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import networkx as nx

from flatline._errors import InternalError
from flatline.models.enums import VarnodeSpace

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
_LAYER_DISTANCE = 80
_NODE_DISTANCE = 40
_DEFAULT_LAYOUT_NODE_SIZE = (76.0, 68.0)
_LAYOUT_CACHE_MAXSIZE = 8


@dataclass(frozen=True)
class Position:
    """Center-based node rectangle returned by the native layout."""

    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class LayoutResult:
    """Native layout output keyed by stable node ID strings."""

    nodes: dict[str, Position]
    meta: dict


_layout_cache: OrderedDict[int, LayoutResult] = OrderedDict()


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
    if varnode.space == VarnodeSpace.REGISTER:
        return "REGISTER"
    if varnode.space == VarnodeSpace.RAM:
        return "RAM"
    if varnode.space == VarnodeSpace.UNIQUE:
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


def compute_layout(pcode_graph: nx.MultiDiGraph) -> LayoutResult:
    """Compute a deterministic center-based Sugiyama layout for a pcode graph."""

    cached = _layout_cache.get(id(pcode_graph))
    if cached is not None:
        _layout_cache.move_to_end(id(pcode_graph))
        return cached

    if pcode_graph.number_of_nodes() == 0:
        return _store_layout_result(
            id(pcode_graph),
            LayoutResult(nodes={}, meta={"schema_version": 1, "back_edges": []}),
        )

    try:
        from flatline._native_layout import ogdf  # lazy: native bridge optional
    except ImportError as exc:
        raise InternalError(
            "compute_layout() requires the native bridge; "
            "install flatline with native_bridge=enabled"
        ) from exc

    ogdf.setSeed(0)
    graph = ogdf.Graph()
    graph_nodes = _stable_graph_nodes(pcode_graph)
    ogdf_nodes = {node_id: graph.newNode() for node_id in graph_nodes}
    for source, target in _stable_graph_edges(pcode_graph):
        if source != target:
            graph.newEdge(ogdf_nodes[source], ogdf_nodes[target])

    attributes = ogdf.GraphAttributes(graph, ogdf.nodeGraphics | ogdf.edgeGraphics)
    for node_id, native_node in ogdf_nodes.items():
        width, height = _layout_node_size(pcode_graph, node_id)
        attributes.setWidth(native_node, width)
        attributes.setHeight(native_node, height)

    layout = ogdf.SugiyamaLayout()
    layout.setRuns(1)
    hierarchy_layout = ogdf.FastHierarchyLayout()
    hierarchy_layout.layerDistance(_LAYER_DISTANCE)
    hierarchy_layout.nodeDistance(_NODE_DISTANCE)
    _ = ogdf.OptimalRanking()
    layout.call(attributes)

    positions: dict[str, Position] = {}
    for node_id in graph_nodes:
        native_node = ogdf_nodes[node_id]
        position = Position(
            x=float(attributes.x(native_node)),
            y=float(attributes.y(native_node)),
            w=float(attributes.width(native_node)),
            h=float(attributes.height(native_node)),
        )
        _validate_position(node_id, position)
        positions[_node_id_string(node_id)] = position

    result = LayoutResult(
        nodes=positions,
        meta={"schema_version": 1, "back_edges": _back_edges(pcode_graph)},
    )
    return _store_layout_result(id(pcode_graph), result)


def _store_layout_result(cache_key: int, result: LayoutResult) -> LayoutResult:
    _layout_cache[cache_key] = result
    _layout_cache.move_to_end(cache_key)
    while len(_layout_cache) > _LAYOUT_CACHE_MAXSIZE:
        _layout_cache.popitem(last=False)
    return result


def _stable_graph_nodes(pcode_graph: nx.MultiDiGraph) -> list[object]:
    return sorted(pcode_graph.nodes, key=_node_id_string)


def _stable_graph_edges(pcode_graph: nx.MultiDiGraph) -> list[tuple[object, object]]:
    return sorted(
        pcode_graph.edges(),
        key=lambda edge: (_node_id_string(edge[0]), _node_id_string(edge[1])),
    )


def _node_id_string(node_id: object) -> str:
    return repr(node_id)


def _back_edges(pcode_graph: nx.MultiDiGraph) -> list[tuple[str, str]]:
    components = list(nx.strongly_connected_components(pcode_graph))
    cyclic_nodes = {node for component in components if len(component) > 1 for node in component}
    back_edges = [
        (_node_id_string(source), _node_id_string(target))
        for source, target in pcode_graph.edges()
        if source == target or (source in cyclic_nodes and target in cyclic_nodes)
    ]
    return sorted(back_edges)


def _layout_node_size(pcode_graph: nx.MultiDiGraph, node_id: object) -> tuple[float, float]:
    op_by_id, varnode_by_id = _layout_payloads(pcode_graph)
    if isinstance(node_id, tuple) and len(node_id) == 2 and isinstance(node_id[1], int):
        kind, numeric_id = node_id
        if kind == "op" and numeric_id in op_by_id:
            node = VisualNode(key=_node_id_string(node_id), actual=node_id, depth=0)
            return node_size(node, op_by_id, varnode_by_id)
        if kind == "varnode" and numeric_id in varnode_by_id:
            node = VisualNode(key=_node_id_string(node_id), actual=node_id, depth=0)
            return node_size(node, op_by_id, varnode_by_id)
    return _DEFAULT_LAYOUT_NODE_SIZE


def _layout_payloads(
    pcode_graph: nx.MultiDiGraph,
) -> tuple[dict[int, PcodeOpInfo], dict[int, VarnodeInfo]]:
    op_by_id = {}
    varnode_by_id = {}
    for _node_id, data in pcode_graph.nodes(data=True):
        op = data.get("op")
        if op is not None:
            op_by_id[op.id] = op
        varnode = data.get("varnode")
        if varnode is not None:
            varnode_by_id[varnode.id] = varnode
    return op_by_id, varnode_by_id


def _validate_position(node_id: object, position: Position) -> None:
    values = (position.x, position.y, position.w, position.h)
    if not all(math.isfinite(value) for value in values):
        raise InternalError(f"layout produced non-finite coordinate for {node_id!r}")


__all__ = [
    "HORIZONTAL_NODE_GAP",
    "VERTICAL_LEVEL_GAP",
    "LayoutResult",
    "NodeId",
    "Position",
    "VisualNode",
    "compute_layout",
    "fit_opcode_label",
    "fit_varnode_badge",
    "node_label_lines",
    "node_pad",
    "node_size",
    "shorten_label",
    "sorted_ops",
    "varnode_badge",
]
