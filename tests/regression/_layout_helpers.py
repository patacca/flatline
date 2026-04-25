"""Shared helpers for layout/routing regression tests (T21)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests._native_fixtures import _FIXTURES, NativeFixture

if TYPE_CHECKING:
    import networkx as nx

# Fixture ids exercised by structural/determinism/golden tests. We use every
# committed fixture so multi-ISA coverage and edge-case shapes (switch,
# delay-slot, warning, external-call) all flow through the layout pipeline.
LAYOUT_FIXTURE_IDS: tuple[str, ...] = tuple(_FIXTURES.keys())


def get_fixture(fixture_id: str) -> NativeFixture:
    return _FIXTURES[fixture_id]


def pcode_graph_for(fixture: NativeFixture, runtime_data_dir: str) -> nx.MultiDiGraph:
    """Decompile fixture once and return its enriched pcode graph."""
    # Imported lazily so collection does not require the native bridge.
    from flatline import decompile_function

    request = fixture.build_request(runtime_data_dir, enriched=True)
    result = decompile_function(request)
    if result.error is not None:
        raise AssertionError(f"decompile failed for {fixture.fixture_id}: {result.error.category}")
    enriched = result.enriched
    assert enriched is not None, f"{fixture.fixture_id}: missing enriched payload"
    return enriched.pcode.to_graph()


def build_layout_payload(layout, routes) -> dict:
    """Mirror flatline.xray.__main__._build_layout_payload exactly.

    Keeping a local copy avoids depending on the CLI module's private API while
    guaranteeing golden comparisons see the same shape on disk.
    """
    back_edge_pairs = {tuple(pair) for pair in layout.meta.get("back_edges", [])}
    nodes_payload = {
        node_key: {"x": pos.x, "y": pos.y, "w": pos.w, "h": pos.h}
        for node_key, pos in layout.nodes.items()
    }
    edges_payload = []
    for (src, dst, key), polyline in routes.items():
        src_str = repr(src)
        dst_str = repr(dst)
        edges_payload.append(
            {
                "src": src_str,
                "dst": dst_str,
                "key": repr(key),
                "polyline": [[float(x), float(y)] for x, y in polyline],
                "back_edge": (src_str, dst_str) in back_edge_pairs,
            }
        )
    return {
        "schema_version": 1,
        "nodes": nodes_payload,
        "edges": edges_payload,
    }
