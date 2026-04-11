from __future__ import annotations

import pytest

from flatline.xray._canvas import manhattan_route, nearest_side_anchors
from flatline.xray._layout import NodeRect, VisualNode, node_size

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


def test_manhattan_route_no_obstacles_same_as_default() -> None:
    coords_none = manhattan_route(10.0, 20.0, 80.0, 100.0, obstacles=None)
    coords_empty = manhattan_route(10.0, 20.0, 80.0, 100.0, obstacles=[])
    assert coords_none == coords_empty


def test_manhattan_route_detours_around_obstacle() -> None:
    obstacle = NodeRect(x_min=40.0, y_min=55.0, x_max=60.0, y_max=65.0)
    coords = manhattan_route(10.0, 20.0, 80.0, 100.0, obstacles=[obstacle])
    waypoints = list(zip(coords[::2], coords[1::2], strict=True))
    for i in range(len(waypoints) - 1):
        ax, ay = waypoints[i]
        bx, by = waypoints[i + 1]
        if ay != by:
            continue
        seg_y = ay
        x_lo, x_hi = min(ax, bx), max(ax, bx)
        overlaps_x = x_hi >= obstacle.x_min and x_lo <= obstacle.x_max
        inside_y = obstacle.y_min <= seg_y <= obstacle.y_max
        assert not (overlaps_x and inside_y), (
            f"horizontal segment at y={seg_y} from x={x_lo} to x={x_hi} "
            f"crosses obstacle {obstacle}"
        )


def test_manhattan_route_no_detour_when_obstacle_not_in_path() -> None:
    obstacle = NodeRect(x_min=200.0, y_min=200.0, x_max=250.0, y_max=250.0)
    coords = manhattan_route(10.0, 20.0, 80.0, 100.0, obstacles=[obstacle])
    assert len(coords) == 8


def test_manhattan_route_detour_picks_shorter_direction() -> None:
    obstacle = NodeRect(x_min=40.0, y_min=58.0, x_max=60.0, y_max=62.0)
    coords = manhattan_route(10.0, 20.0, 80.0, 100.0, obstacles=[obstacle])
    waypoints = list(zip(coords[::2], coords[1::2], strict=True))
    detour_ys = [y for _, y in waypoints if y < obstacle.y_min or y > obstacle.y_max]
    assert len(detour_ys) > 0


def test_manhattan_route_multiple_obstacles() -> None:
    obs1 = NodeRect(x_min=20.0, y_min=55.0, x_max=40.0, y_max=65.0)
    obs2 = NodeRect(x_min=60.0, y_min=45.0, x_max=80.0, y_max=55.0)
    coords = manhattan_route(10.0, 20.0, 100.0, 100.0, obstacles=[obs1, obs2])
    waypoints = list(zip(coords[::2], coords[1::2], strict=True))
    for i in range(len(waypoints) - 1):
        ax, ay = waypoints[i]
        bx, by = waypoints[i + 1]
        if ay != by:
            continue
        seg_y = ay
        x_lo, x_hi = min(ax, bx), max(ax, bx)
        for obs in [obs1, obs2]:
            overlaps_x = x_hi >= obs.x_min and x_lo <= obs.x_max
            inside_y = obs.y_min <= seg_y <= obs.y_max
            assert not (overlaps_x and inside_y)


def test_manhattan_route_result_has_even_length() -> None:
    obstacle = NodeRect(x_min=40.0, y_min=55.0, x_max=60.0, y_max=65.0)
    coords = manhattan_route(10.0, 20.0, 80.0, 100.0, obstacles=[obstacle])
    assert len(coords) % 2 == 0
    assert len(coords) >= 8


def test_manhattan_route_endpoints_preserved_with_obstacles() -> None:
    obstacle = NodeRect(x_min=40.0, y_min=55.0, x_max=60.0, y_max=65.0)
    coords = manhattan_route(10.0, 20.0, 80.0, 100.0, obstacles=[obstacle])
    assert coords[0] == 10.0
    assert coords[1] == 20.0
    assert coords[-2] == 80.0
    assert coords[-1] == 100.0


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
