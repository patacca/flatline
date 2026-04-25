"""Structural invariants for compute_layout + route_edges across all fixtures."""

from __future__ import annotations

import math

import pytest

from flatline.xray._edge_routing import route_edges
from flatline.xray._layout import compute_layout
from tests.regression._layout_helpers import (
    LAYOUT_FIXTURE_IDS,
    get_fixture,
    pcode_graph_for,
)


@pytest.mark.parametrize("fixture_id", LAYOUT_FIXTURE_IDS)
def test_layout_structural_invariants(fixture_id: str, native_runtime_data_dir: str) -> None:
    fixture = get_fixture(fixture_id)
    pcode_graph = pcode_graph_for(fixture, native_runtime_data_dir)

    layout = compute_layout(pcode_graph)
    routes = route_edges(layout, pcode_graph)

    assert layout.nodes, f"{fixture_id}: empty layout nodes"

    for node_key, pos in layout.nodes.items():
        for attr in ("x", "y", "w", "h"):
            value = getattr(pos, attr)
            assert not math.isnan(value), f"{fixture_id}: NaN {attr} on node {node_key}"
        assert pos.w > 0, f"{fixture_id}: non-positive width on node {node_key}"
        assert pos.h > 0, f"{fixture_id}: non-positive height on node {node_key}"

    for (src, dst, key), polyline in routes.items():
        is_self_loop = src == dst
        if is_self_loop:
            assert len(polyline) == 5, (
                f"{fixture_id}: self-loop {src!r}->{dst!r} key={key!r} "
                f"has {len(polyline)} vertices, expected 5"
            )
        else:
            assert len(polyline) >= 2, (
                f"{fixture_id}: edge {src!r}->{dst!r} key={key!r} "
                f"has {len(polyline)} vertices, expected >= 2"
            )
        for x, y in polyline:
            assert not math.isnan(x), f"{fixture_id}: NaN x in polyline {src!r}->{dst!r}"
            assert not math.isnan(y), f"{fixture_id}: NaN y in polyline {src!r}->{dst!r}"
