# pyright: reportMissingImports=false

from __future__ import annotations

import networkx as nx
import pytest

from flatline._errors import InternalError
from flatline.xray._edge_routing import route_edges
from flatline.xray._layout import LayoutResult, Position

pytestmark = pytest.mark.unit


def _layout_for(nodes: dict[str, tuple[float, float]]) -> LayoutResult:
    return LayoutResult(
        nodes={node_id: Position(x=x, y=y, w=76.0, h=68.0) for node_id, (x, y) in nodes.items()},
        meta={"schema_version": 1, "back_edges": []},
    )


def test_two_node_edge_returns_polyline() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("a", "b")
    layout = _layout_for({"'a'": (0.0, 0.0), "'b'": (0.0, 180.0)})

    routes = route_edges(layout, graph)

    assert set(routes) == {("a", "b", 0)}
    assert len(routes[("a", "b", 0)]) >= 2


def test_three_node_cycle_routes_every_edge() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
    layout = _layout_for({"'a'": (0.0, 0.0), "'b'": (160.0, 160.0), "'c'": (-160.0, 160.0)})

    routes = route_edges(layout, graph)

    assert set(routes) == {("a", "b", 0), ("b", "c", 0), ("c", "a", 0)}
    assert all(polyline for polyline in routes.values())


def test_self_loop_uses_five_vertex_right_side_u_polyline() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("n0", "n0")
    layout = _layout_for({"'n0'": (100.0, 200.0)})

    polyline = route_edges(layout, graph)[("n0", "n0", 0)]

    node = layout.nodes["'n0'"]
    right_edge = node.x + node.w / 2.0
    assert polyline == [
        (right_edge, node.y),
        (right_edge + 40.0, node.y),
        (right_edge + 40.0, node.y - node.h / 2.0 - 30.0),
        (node.x, node.y - node.h / 2.0 - 30.0),
        (node.x, node.y - node.h / 2.0),
    ]
    assert polyline[1][0] > right_edge
    assert polyline[2][0] > right_edge


def test_empty_libavoid_route_for_non_self_loop_raises_internal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from flatline._native_layout import avoid

    graph = nx.MultiDiGraph()
    graph.add_edge("a", "b")
    layout = _layout_for({"'a'": (0.0, 0.0), "'b'": (0.0, 180.0)})

    class EmptyRoute:
        size = 0

    monkeypatch.setattr(avoid.ConnRef, "displayRoute", lambda _conn: EmptyRoute())

    with pytest.raises(InternalError, match="libavoid produced no route"):
        route_edges(layout, graph)
