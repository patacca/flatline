from __future__ import annotations

import math

import networkx as nx
import pytest

from flatline.xray._layout import LayoutResult, Position, compute_layout

pytestmark = pytest.mark.unit


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
