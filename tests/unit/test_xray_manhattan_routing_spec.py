from __future__ import annotations

import pytest

from flatline.xray._canvas import manhattan_route, nearest_side_anchors
from flatline.xray._layout import VisualNode, node_size

from ._xray_support import make_sample_pcode

pytestmark = pytest.mark.unit


def test_manhattan_route_diagonal() -> None:
    coords = manhattan_route(100.0, 200.0, 300.0, 400.0)
    mid_y = (200.0 + 400.0) / 2.0
    assert len(coords) == 8
    assert coords == [100.0, 200.0, 100.0, mid_y, 300.0, mid_y, 300.0, 400.0]


def test_manhattan_route_same_x() -> None:
    coords = manhattan_route(50.0, 10.0, 50.0, 90.0)
    assert len(coords) == 8
    assert coords[0] == coords[2] == coords[4] == coords[6] == 50.0


def test_manhattan_route_same_y() -> None:
    coords = manhattan_route(10.0, 75.0, 90.0, 75.0)
    mid_y = 75.0
    assert coords[1] == mid_y
    assert coords[3] == mid_y
    assert coords[5] == mid_y
    assert coords[7] == mid_y


def test_manhattan_route_returns_8_values() -> None:
    for x1, y1, x2, y2 in [(0, 0, 0, 0), (-5, 10, 20, -30), (1.5, 2.5, 3.5, 4.5)]:
        coords = manhattan_route(x1, y1, x2, y2)
        assert len(coords) == 8
        assert all(isinstance(v, (int, float)) for v in coords)


def _make_lookup_dicts() -> tuple[dict, dict]:
    pcode = make_sample_pcode()
    op_by_id = {op.id: op for op in pcode.pcode_ops}
    varnode_by_id = {v.id: v for v in pcode.varnodes}
    return op_by_id, varnode_by_id


def test_nearest_side_anchors_target_right() -> None:
    op_by_id, varnode_by_id = _make_lookup_dicts()
    source = VisualNode(key="s", actual=("op", 0), depth=0, x=100.0, y=300.0)
    target = VisualNode(key="t", actual=("op", 1), depth=0, x=500.0, y=300.0)
    (sx, _sy), (tx, _ty) = nearest_side_anchors(source, target, op_by_id, varnode_by_id)
    sw, _ = node_size(source, op_by_id, varnode_by_id)
    tw, _ = node_size(target, op_by_id, varnode_by_id)
    assert sx == source.x + sw / 2.0
    assert tx == target.x - tw / 2.0


def test_nearest_side_anchors_target_left() -> None:
    op_by_id, varnode_by_id = _make_lookup_dicts()
    source = VisualNode(key="s", actual=("op", 0), depth=0, x=500.0, y=300.0)
    target = VisualNode(key="t", actual=("op", 1), depth=0, x=100.0, y=300.0)
    (sx, _sy), (tx, _ty) = nearest_side_anchors(source, target, op_by_id, varnode_by_id)
    sw, _ = node_size(source, op_by_id, varnode_by_id)
    tw, _ = node_size(target, op_by_id, varnode_by_id)
    assert sx == source.x - sw / 2.0
    assert tx == target.x + tw / 2.0
