"""Bit-identical determinism guard for compute_layout + route_edges."""

from __future__ import annotations

import pytest

from flatline.xray._edge_routing import route_edges
from flatline.xray._layout import compute_layout
from tests.regression._layout_helpers import (
    LAYOUT_FIXTURE_IDS,
    get_fixture,
    pcode_graph_for,
)


def _layout_snapshot(pcode_graph) -> tuple:
    layout = compute_layout(pcode_graph)
    routes = route_edges(layout, pcode_graph)
    nodes_snap = tuple(
        (key, pos.x, pos.y, pos.w, pos.h) for key, pos in sorted(layout.nodes.items())
    )
    routes_snap = tuple(
        (repr(src), repr(dst), repr(key), tuple((float(x), float(y)) for x, y in poly))
        for (src, dst, key), poly in sorted(
            routes.items(), key=lambda kv: (repr(kv[0][0]), repr(kv[0][1]), repr(kv[0][2]))
        )
    )
    return nodes_snap, routes_snap


@pytest.mark.parametrize("fixture_id", LAYOUT_FIXTURE_IDS)
def test_layout_bit_identity_three_runs(fixture_id: str, native_runtime_data_dir: str) -> None:
    fixture = get_fixture(fixture_id)
    pcode_graph = pcode_graph_for(fixture, native_runtime_data_dir)

    snapshots = [_layout_snapshot(pcode_graph) for _ in range(3)]

    assert snapshots[0] == snapshots[1], f"{fixture_id}: run1 vs run2 diverged"
    assert snapshots[1] == snapshots[2], f"{fixture_id}: run2 vs run3 diverged"
