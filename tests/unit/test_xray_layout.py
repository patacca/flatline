from __future__ import annotations

import math

import networkx as nx
import pytest

from flatline.models.enums import VarnodeSpace
from flatline.models.pcode_ops.branch import Cbranch
from flatline.models.types import PcodeOpInfo, VarnodeFlags
from flatline.models.varnodes import IopVarnode, RegisterVarnode
from flatline.xray._layout import (
    LayoutResult,
    Position,
    _overlay_graph_edges,
    compute_layout,
)

pytestmark = pytest.mark.unit


def _flags() -> VarnodeFlags:
    return VarnodeFlags(
        is_constant=False,
        is_input=False,
        is_free=False,
        is_implied=False,
        is_explicit=True,
        is_read_only=False,
        is_persist=False,
        is_addr_tied=False,
    )


def _op(op_id: int, opcode: str, address: int, **kwargs) -> PcodeOpInfo:
    return PcodeOpInfo(
        id=op_id,
        opcode=opcode,
        instruction_address=address,
        sequence_time=0,
        sequence_order=op_id,
        input_varnode_ids=[],
        output_varnode_id=None,
        **kwargs,
    )


def _cbranch(op_id: int, address: int, true_addr: int, false_addr: int) -> Cbranch:
    return Cbranch(
        id=op_id,
        opcode="CBRANCH",
        instruction_address=address,
        sequence_time=0,
        sequence_order=op_id,
        input_varnode_ids=[],
        output_varnode_id=None,
        true_target_address=true_addr,
        false_target_address=false_addr,
    )


def _assert_valid_position(position: Position) -> None:
    assert math.isfinite(position.x)
    assert math.isfinite(position.y)
    assert math.isfinite(position.w)
    assert math.isfinite(position.h)
    assert position.w > 0
    assert position.h > 0


def test_empty_graph_returns_empty_layout_result() -> None:
    result = compute_layout(nx.MultiDiGraph())

    assert result == LayoutResult(nodes={}, meta={"schema_version": 1, "back_edges": []})


def test_single_node_has_one_valid_position() -> None:
    graph = nx.MultiDiGraph()
    graph.add_node("solo")

    result = compute_layout(graph)

    assert set(result.nodes) == {"'solo'"}
    _assert_valid_position(result.nodes["'solo'"])


def test_five_node_dag_assigns_distinct_y_values() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edges_from([("a", "b"), ("b", "c"), ("c", "d"), ("d", "e")])

    result = compute_layout(graph)

    y_values = [position.y for position in result.nodes.values()]

    assert len(result.nodes) == 5
    assert len(set(y_values)) == 5


def test_cyclic_three_node_graph_keeps_all_nodes_and_marks_back_edges() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])

    result = compute_layout(graph)

    back_edges = {tuple(edge) for edge in result.meta["back_edges"]}

    assert set(result.nodes) == {"'a'", "'b'", "'c'"}
    assert back_edges == {("'a'", "'b'"), ("'b'", "'c'"), ("'c'", "'a'")}


def test_self_loop_node_remains_positioned_and_marks_back_edge() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("loop", "loop")

    result = compute_layout(graph)

    assert set(result.nodes) == {"'loop'"}
    assert result.meta["back_edges"] == [("'loop'", "'loop'")]
    _assert_valid_position(result.nodes["'loop'"])


def test_layout_is_deterministic_for_same_graph() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edges_from([("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")])

    results = [compute_layout(graph) for _ in range(3)]

    assert results[0] == results[1] == results[2]


def test_overlay_edges_empty_when_graph_has_no_payloads() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edges_from([("a", "b"), ("b", "c")])

    assert _overlay_graph_edges(graph) == []


def test_overlay_edges_emits_cbranch_true_and_false_targets() -> None:
    target_true = _op(10, "COPY", 0x100)
    target_false = _op(11, "COPY", 0x200)
    cbranch = _cbranch(1, address=0x10, true_addr=0x100, false_addr=0x200)

    graph = nx.MultiDiGraph()
    graph.add_node(("op", cbranch.id), kind="pcode_op", op=cbranch)
    graph.add_node(("op", target_true.id), kind="pcode_op", op=target_true)
    graph.add_node(("op", target_false.id), kind="pcode_op", op=target_false)

    edges = _overlay_graph_edges(graph)

    assert (("op", 1), ("op", 10)) in edges
    assert (("op", 1), ("op", 11)) in edges
    assert len(edges) == 2


def test_overlay_edges_skip_cbranch_target_missing_from_graph() -> None:
    cbranch = _cbranch(1, address=0x10, true_addr=0x100, false_addr=0x200)

    graph = nx.MultiDiGraph()
    graph.add_node(("op", cbranch.id), kind="pcode_op", op=cbranch)

    assert _overlay_graph_edges(graph) == []


def test_overlay_edges_emit_iop_target_edge() -> None:
    target_op = _op(20, "COPY", 0x300)
    iop_vn = IopVarnode(
        id=5,
        space=VarnodeSpace.IOP,
        offset=0,
        size=4,
        flags=_flags(),
        defining_op_id=None,
        use_op_ids=[],
        target_op_id=target_op.id,
    )

    graph = nx.MultiDiGraph()
    graph.add_node(("op", target_op.id), kind="pcode_op", op=target_op)
    graph.add_node(("varnode", iop_vn.id), kind="varnode", varnode=iop_vn)

    edges = _overlay_graph_edges(graph)

    assert edges == [(("varnode", 5), ("op", 20))]


def test_overlay_edges_skip_iop_when_target_missing() -> None:
    iop_vn = IopVarnode(
        id=5,
        space=VarnodeSpace.IOP,
        offset=0,
        size=4,
        flags=_flags(),
        defining_op_id=None,
        use_op_ids=[],
        target_op_id=999,
    )
    graph = nx.MultiDiGraph()
    graph.add_node(("varnode", iop_vn.id), kind="varnode", varnode=iop_vn)

    assert _overlay_graph_edges(graph) == []


def test_overlay_edges_ignore_non_iop_varnodes() -> None:
    reg_vn = RegisterVarnode(
        id=7,
        space=VarnodeSpace.REGISTER,
        offset=0,
        size=4,
        flags=_flags(),
        defining_op_id=None,
        use_op_ids=[],
    )
    graph = nx.MultiDiGraph()
    graph.add_node(("varnode", reg_vn.id), kind="varnode", varnode=reg_vn)

    assert _overlay_graph_edges(graph) == []


def test_overlay_edges_are_sorted_and_deduplicated() -> None:
    target_op = _op(2, "COPY", 0x100)
    target_dup = _op(3, "COPY", 0x100)
    cbranch = _cbranch(1, address=0x10, true_addr=0x100, false_addr=0x100)

    graph = nx.MultiDiGraph()
    graph.add_node(("op", cbranch.id), kind="pcode_op", op=cbranch)
    graph.add_node(("op", target_op.id), kind="pcode_op", op=target_op)
    graph.add_node(("op", target_dup.id), kind="pcode_op", op=target_dup)

    edges = _overlay_graph_edges(graph)

    assert edges == sorted(set(edges), key=lambda e: (repr(e[0]), repr(e[1])))
    assert (("op", 1), ("op", 2)) in edges
    assert (("op", 1), ("op", 3)) in edges
    assert len(edges) == 2


def test_layout_cache_does_not_alias_recycled_graph_ids() -> None:
    # Regression: id(graph) was used as cache key without weakref tracking,
    # so a recycled CPython id from a GC'd graph could return a stale layout
    # whose node set did not match the new graph (CI golden test failure).
    from flatline.xray import _layout as layout_mod

    layout_mod._layout_cache.clear()
    layout_mod._layout_cache_refs.clear()

    first = nx.MultiDiGraph()
    first.add_node(("op", 1), kind="pcode_op")
    first_result = LayoutResult(
        nodes={"('op', 1)": Position(x=0.0, y=0.0, w=10.0, h=10.0)},
        meta={"schema_version": 1, "back_edges": []},
    )
    layout_mod._store_layout_result(first, first_result)
    recycled_id = id(first)
    del first

    second = nx.MultiDiGraph()
    second.add_node(("op", 99), kind="pcode_op")
    if id(second) != recycled_id:
        pytest.skip("CPython did not recycle the id; cache aliasing path not exercised")

    cached = layout_mod._layout_cache.get(id(second))
    cached_ref = layout_mod._layout_cache_refs.get(id(second))
    if cached is not None:
        assert cached_ref is None or cached_ref() is not second, (
            "stale layout returned for recycled graph id"
        )
