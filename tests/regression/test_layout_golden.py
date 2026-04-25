"""Compare current layout/routing output against committed golden dumps."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from flatline.xray._edge_routing import route_edges
from flatline.xray._layout import compute_layout
from tests.regression._layout_helpers import (
    build_layout_payload,
    get_fixture,
    pcode_graph_for,
)

_GOLDEN_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "layout_golden"
_TOLERANCE = 0.5


def _golden_files() -> list[Path]:
    return sorted(p for p in _GOLDEN_DIR.glob("*__0x1000.json"))


def _fixture_id_from_golden(path: Path) -> str:
    return path.name.split("__", 1)[0]


@pytest.mark.parametrize(
    "golden_path",
    _golden_files(),
    ids=lambda p: p.stem,
)
def test_layout_matches_golden(golden_path: Path, native_runtime_data_dir: str) -> None:
    fixture_id = _fixture_id_from_golden(golden_path)
    fixture = get_fixture(fixture_id)
    pcode_graph = pcode_graph_for(fixture, native_runtime_data_dir)

    layout = compute_layout(pcode_graph)
    routes = route_edges(layout, pcode_graph)
    actual = build_layout_payload(layout, routes)
    expected = json.loads(golden_path.read_text(encoding="utf-8"))

    assert actual["schema_version"] == expected["schema_version"]

    assert set(actual["nodes"].keys()) == set(expected["nodes"].keys()), (
        f"{fixture_id}: node id set differs from golden"
    )
    for node_key, exp_pos in expected["nodes"].items():
        act_pos = actual["nodes"][node_key]
        for attr in ("x", "y", "w", "h"):
            diff = abs(act_pos[attr] - exp_pos[attr])
            assert diff <= _TOLERANCE, (
                f"{fixture_id}: node {node_key} {attr} drift {diff:.3f} > {_TOLERANCE}"
            )

    # Edge order is not stable across implementations; key by (src, dst, key).
    def _index(edges: list[dict]) -> dict[tuple[str, str, str], dict]:
        return {(e["src"], e["dst"], e["key"]): e for e in edges}

    actual_idx = _index(actual["edges"])
    expected_idx = _index(expected["edges"])

    assert set(actual_idx.keys()) == set(expected_idx.keys()), (
        f"{fixture_id}: edge identity set differs from golden"
    )

    for edge_key, exp_edge in expected_idx.items():
        act_edge = actual_idx[edge_key]
        exp_poly = exp_edge["polyline"]
        act_poly = act_edge["polyline"]
        assert len(act_poly) == len(exp_poly), (
            f"{fixture_id}: edge {edge_key} vertex count {len(act_poly)} != {len(exp_poly)}"
        )
        for i, ((ax, ay), (ex, ey)) in enumerate(zip(act_poly, exp_poly, strict=True)):
            assert abs(ax - ex) <= _TOLERANCE, (
                f"{fixture_id}: edge {edge_key} vertex {i} x drift "
                f"{abs(ax - ex):.3f} > {_TOLERANCE}"
            )
            assert abs(ay - ey) <= _TOLERANCE, (
                f"{fixture_id}: edge {edge_key} vertex {i} y drift "
                f"{abs(ay - ey):.3f} > {_TOLERANCE}"
            )
