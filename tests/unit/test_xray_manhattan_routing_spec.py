from __future__ import annotations

import pytest

from flatline.xray._edge_routing import (
    _build_initial_waypoints,
    _collapse_collinear,
    _filter_endpoint_obstacles,
    _point_in_rect,
    _v_segment_hits,
    manhattan_route,
    nearest_side_anchors,
)
from flatline.xray._layout import NodeRect, VisualNode, node_size

from ._xray_support import make_sample_pcode

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers used across multiple tests
# ---------------------------------------------------------------------------


def _coords_to_waypoints(coords: list[float]) -> list[tuple[float, float]]:
    """Convert a flat coordinate list to (x, y) waypoint pairs."""
    return list(zip(coords[::2], coords[1::2], strict=True))


def _assert_no_segment_crosses_any_rect(
    coords: list[float],
    obstacles: list[NodeRect],
) -> None:
    """Assert no segment in *coords* overlaps any rect (both axes)."""
    waypoints = _coords_to_waypoints(coords)
    for i in range(len(waypoints) - 1):
        ax, ay = waypoints[i]
        bx, by = waypoints[i + 1]
        for obs in obstacles:
            if ay == by:
                # Horizontal segment.
                seg_y = ay
                x_lo, x_hi = min(ax, bx), max(ax, bx)
                overlaps_x = x_hi >= obs.x_min and x_lo <= obs.x_max
                inside_y = obs.y_min <= seg_y <= obs.y_max
                assert not (overlaps_x and inside_y), (
                    f"horizontal segment at y={seg_y} from x={x_lo} to x={x_hi} "
                    f"crosses obstacle {obs}"
                )
            elif ax == bx:
                # Vertical segment.
                seg_x = ax
                y_lo, y_hi = min(ay, by), max(ay, by)
                overlaps_y = y_hi >= obs.y_min and y_lo <= obs.y_max
                inside_x = obs.x_min <= seg_x <= obs.x_max
                assert not (overlaps_y and inside_x), (
                    f"vertical segment at x={seg_x} from y={y_lo} to y={y_hi} "
                    f"crosses obstacle {obs}"
                )


# ---------------------------------------------------------------------------
# Original tests (unchanged)
# ---------------------------------------------------------------------------


def test_manhattan_route_diagonal() -> None:
    coords = manhattan_route(100.0, 200.0, 300.0, 400.0)
    mid_y = (200.0 + 400.0) / 2.0
    assert len(coords) == 8
    assert coords == [100.0, 200.0, 100.0, mid_y, 300.0, mid_y, 300.0, 400.0]


def test_manhattan_route_same_x() -> None:
    coords = manhattan_route(50.0, 10.0, 50.0, 90.0)
    assert len(coords) == 4
    assert coords == [50.0, 10.0, 50.0, 90.0]


def test_manhattan_route_same_y() -> None:
    coords = manhattan_route(10.0, 75.0, 90.0, 75.0)
    mid_y = 75.0
    assert coords[1] == mid_y
    assert coords[3] == mid_y
    assert coords[5] == mid_y
    assert coords[7] == mid_y


def test_manhattan_route_returns_even_length_coords() -> None:
    for x1, y1, x2, y2 in [(0, 0, 0, 0), (-5, 10, 20, -30), (1.5, 2.5, 3.5, 4.5)]:
        coords = manhattan_route(x1, y1, x2, y2)
        assert len(coords) >= 4
        assert len(coords) % 2 == 0
        assert all(isinstance(v, (int, float)) for v in coords)


def test_manhattan_route_no_obstacles_same_as_default() -> None:
    coords_none = manhattan_route(10.0, 20.0, 80.0, 100.0, obstacles=None)
    coords_empty = manhattan_route(10.0, 20.0, 80.0, 100.0, obstacles=[])
    assert coords_none == coords_empty


def test_manhattan_route_detours_around_obstacle() -> None:
    obstacle = NodeRect(x_min=40.0, y_min=55.0, x_max=60.0, y_max=65.0)
    coords = manhattan_route(10.0, 20.0, 80.0, 100.0, obstacles=[obstacle])
    _assert_no_segment_crosses_any_rect(coords, [obstacle])


def test_manhattan_route_no_detour_when_obstacle_not_in_path() -> None:
    obstacle = NodeRect(x_min=200.0, y_min=200.0, x_max=250.0, y_max=250.0)
    coords = manhattan_route(10.0, 20.0, 80.0, 100.0, obstacles=[obstacle])
    assert len(coords) == 8


def test_manhattan_route_detour_picks_shorter_direction() -> None:
    obstacle = NodeRect(x_min=40.0, y_min=58.0, x_max=60.0, y_max=62.0)
    coords = manhattan_route(10.0, 20.0, 80.0, 100.0, obstacles=[obstacle])
    waypoints = _coords_to_waypoints(coords)
    detour_ys = [y for _, y in waypoints if y < obstacle.y_min or y > obstacle.y_max]
    assert len(detour_ys) > 0


def test_manhattan_route_multiple_obstacles() -> None:
    obs1 = NodeRect(x_min=20.0, y_min=55.0, x_max=40.0, y_max=65.0)
    obs2 = NodeRect(x_min=60.0, y_min=45.0, x_max=80.0, y_max=55.0)
    coords = manhattan_route(10.0, 20.0, 100.0, 100.0, obstacles=[obs1, obs2])
    _assert_no_segment_crosses_any_rect(coords, [obs1, obs2])


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


# ---------------------------------------------------------------------------
# New tests: vertical segment avoidance (Bug 1)
# ---------------------------------------------------------------------------


def test_v_segment_hits_detects_overlap() -> None:
    """_v_segment_hits returns True when a vertical line crosses a rect."""
    rect = NodeRect(x_min=40.0, y_min=50.0, x_max=60.0, y_max=70.0)
    # Vertical line at x=50 from y=30 to y=90 — passes through the rect.
    assert _v_segment_hits(30.0, 90.0, 50.0, rect) is True


def test_v_segment_hits_misses_when_outside_x() -> None:
    """_v_segment_hits returns False when x is outside the rect."""
    rect = NodeRect(x_min=40.0, y_min=50.0, x_max=60.0, y_max=70.0)
    assert _v_segment_hits(30.0, 90.0, 30.0, rect) is False


def test_v_segment_hits_misses_when_outside_y() -> None:
    """_v_segment_hits returns False when the y-range is fully outside."""
    rect = NodeRect(x_min=40.0, y_min=50.0, x_max=60.0, y_max=70.0)
    assert _v_segment_hits(80.0, 100.0, 50.0, rect) is False


def test_manhattan_route_vertical_segment_avoids_obstacle() -> None:
    """Vertical segment through an obstacle must detour around it."""
    # Route from (50, 0) to (50, 200).  Default vertical path goes straight
    # down at x=50.  Obstacle sits at x=40..60, y=80..120 — blocks that line.
    obstacle = NodeRect(x_min=40.0, y_min=80.0, x_max=60.0, y_max=120.0)
    coords = manhattan_route(50.0, 0.0, 50.0, 200.0, obstacles=[obstacle])
    _assert_no_segment_crosses_any_rect(coords, [obstacle])
    # Must have extra waypoints (detour introduced).
    assert len(coords) > 8


def test_manhattan_route_vertical_detour_left_or_right() -> None:
    """Vertical detour must go left or right of the obstacle, never through."""
    obstacle = NodeRect(x_min=45.0, y_min=40.0, x_max=55.0, y_max=60.0)
    coords = manhattan_route(50.0, 10.0, 50.0, 90.0, obstacles=[obstacle])
    waypoints = _coords_to_waypoints(coords)
    # At least one waypoint must have an x outside the obstacle x-range.
    detour_xs = [x for x, _ in waypoints if x < obstacle.x_min or x > obstacle.x_max]
    assert len(detour_xs) > 0, "vertical detour did not leave obstacle x-range"
    _assert_no_segment_crosses_any_rect(coords, [obstacle])


# ---------------------------------------------------------------------------
# New tests: horizontal-first routing (Bug 3 — IOP edges)
# ---------------------------------------------------------------------------


def test_horizontal_first_builds_h_v_h_shape() -> None:
    """first_axis='horizontal' produces horizontal→vertical→horizontal."""
    wp = _build_initial_waypoints(0.0, 100.0, 200.0, 300.0, "horizontal")
    assert len(wp) == 4
    # First segment horizontal (same y), middle vertical, last horizontal.
    assert wp[0][1] == wp[1][1], "first segment should be horizontal"
    assert wp[1][0] == wp[2][0], "middle segment should be vertical"
    assert wp[2][1] == wp[3][1], "last segment should be horizontal"


def test_manhattan_route_horizontal_first_no_obstacles() -> None:
    """Horizontal-first route without obstacles returns an h→v→h path."""
    coords = manhattan_route(0.0, 100.0, 200.0, 300.0, first_axis="horizontal")
    wp = _coords_to_waypoints(coords)
    assert len(wp) == 4
    # y stays the same for the first segment.
    assert wp[0][1] == wp[1][1]
    # x stays the same for the middle segment.
    assert wp[1][0] == wp[2][0]
    # y stays the same for the last segment.
    assert wp[2][1] == wp[3][1]


def test_manhattan_route_horizontal_first_avoids_obstacle() -> None:
    """Horizontal-first routing also detours around obstacles."""
    # Edge goes from left side to right side, obstacle sits in the middle.
    obstacle = NodeRect(x_min=90.0, y_min=95.0, x_max=110.0, y_max=105.0)
    coords = manhattan_route(
        0.0,
        100.0,
        200.0,
        100.0,
        obstacles=[obstacle],
        first_axis="horizontal",
    )
    _assert_no_segment_crosses_any_rect(coords, [obstacle])


def test_manhattan_route_horizontal_first_endpoints_preserved() -> None:
    """Start and end points survive horizontal-first routing with obstacles."""
    obstacle = NodeRect(x_min=90.0, y_min=95.0, x_max=110.0, y_max=105.0)
    coords = manhattan_route(
        0.0,
        100.0,
        200.0,
        100.0,
        obstacles=[obstacle],
        first_axis="horizontal",
    )
    assert coords[0] == 0.0
    assert coords[1] == 100.0
    assert coords[-2] == 200.0
    assert coords[-1] == 100.0


# ---------------------------------------------------------------------------
# New tests: endpoint-obstacle filtering
# ---------------------------------------------------------------------------


def test_filter_endpoint_obstacles_excludes_source_rect() -> None:
    """Obstacle containing the start point is excluded from routing."""
    # Source sits at (50, 50), rect encloses that point.
    src_rect = NodeRect(x_min=40.0, y_min=40.0, x_max=60.0, y_max=60.0)
    other = NodeRect(x_min=100.0, y_min=100.0, x_max=120.0, y_max=120.0)
    filtered = _filter_endpoint_obstacles([src_rect, other], 50.0, 50.0, 200.0, 200.0)
    assert src_rect not in filtered
    assert other in filtered


def test_filter_endpoint_obstacles_excludes_target_rect() -> None:
    """Obstacle containing the end point is excluded from routing."""
    tgt_rect = NodeRect(x_min=190.0, y_min=190.0, x_max=210.0, y_max=210.0)
    other = NodeRect(x_min=100.0, y_min=100.0, x_max=120.0, y_max=120.0)
    filtered = _filter_endpoint_obstacles([tgt_rect, other], 0.0, 0.0, 200.0, 200.0)
    assert tgt_rect not in filtered
    assert other in filtered


def test_manhattan_route_ignores_obstacle_at_start() -> None:
    """Route must not detour around the obstacle that contains the start anchor."""
    # Obstacle at start: the route should pass through it normally since it's
    # the source node itself.
    src_obs = NodeRect(x_min=5.0, y_min=15.0, x_max=15.0, y_max=25.0)
    coords = manhattan_route(10.0, 20.0, 80.0, 100.0, obstacles=[src_obs])
    # No extra detour needed — should be the basic 4-waypoint path.
    assert len(coords) == 8


# ---------------------------------------------------------------------------
# New tests: _point_in_rect helper
# ---------------------------------------------------------------------------


def test_point_in_rect_inside() -> None:
    rect = NodeRect(x_min=10.0, y_min=20.0, x_max=50.0, y_max=60.0)
    assert _point_in_rect(30.0, 40.0, rect) is True


def test_point_in_rect_on_boundary() -> None:
    rect = NodeRect(x_min=10.0, y_min=20.0, x_max=50.0, y_max=60.0)
    # On the edge (inclusive).
    assert _point_in_rect(10.0, 20.0, rect) is True
    assert _point_in_rect(50.0, 60.0, rect) is True


def test_point_in_rect_outside() -> None:
    rect = NodeRect(x_min=10.0, y_min=20.0, x_max=50.0, y_max=60.0)
    assert _point_in_rect(5.0, 40.0, rect) is False
    assert _point_in_rect(30.0, 70.0, rect) is False


# ---------------------------------------------------------------------------
# New tests: _collapse_collinear helper
# ---------------------------------------------------------------------------


def test_collapse_collinear_removes_redundant_horizontal() -> None:
    """Three points on the same horizontal line collapse to two."""
    wp = [(0.0, 10.0), (5.0, 10.0), (10.0, 10.0)]
    result = _collapse_collinear(wp)
    assert result == [(0.0, 10.0), (10.0, 10.0)]


def test_collapse_collinear_removes_redundant_vertical() -> None:
    """Three points on the same vertical line collapse to two."""
    wp = [(10.0, 0.0), (10.0, 5.0), (10.0, 10.0)]
    result = _collapse_collinear(wp)
    assert result == [(10.0, 0.0), (10.0, 10.0)]


def test_collapse_collinear_preserves_corners() -> None:
    """A proper L-shape must not lose its corner point."""
    wp = [(0.0, 0.0), (0.0, 10.0), (10.0, 10.0)]
    result = _collapse_collinear(wp)
    assert result == wp


def test_collapse_collinear_short_path_untouched() -> None:
    """Paths with ≤2 waypoints pass through unchanged."""
    assert _collapse_collinear([]) == []
    assert _collapse_collinear([(1.0, 2.0)]) == [(1.0, 2.0)]
    two = [(0.0, 0.0), (1.0, 1.0)]
    assert _collapse_collinear(two) == two


# ---------------------------------------------------------------------------
# New tests: comprehensive crossing check (Bug 1 — both axes)
# ---------------------------------------------------------------------------


def test_manhattan_route_no_segment_crosses_obstacle_comprehensive() -> None:
    """No segment (H or V) in the routed path overlaps any obstacle."""
    obstacles = [
        NodeRect(x_min=40.0, y_min=55.0, x_max=60.0, y_max=65.0),
        NodeRect(x_min=45.0, y_min=30.0, x_max=55.0, y_max=45.0),
        NodeRect(x_min=70.0, y_min=80.0, x_max=90.0, y_max=95.0),
    ]
    coords = manhattan_route(50.0, 10.0, 50.0, 120.0, obstacles=obstacles)
    _assert_no_segment_crosses_any_rect(coords, obstacles)


def test_manhattan_route_obstacle_on_vertical_path_between_different_x() -> None:
    """Obstacle on the first vertical leg of a diagonal route forces detour."""
    obstacle = NodeRect(x_min=5.0, y_min=90.0, x_max=15.0, y_max=110.0)
    coords = manhattan_route(10.0, 0.0, 80.0, 200.0, obstacles=[obstacle])
    _assert_no_segment_crosses_any_rect(coords, [obstacle])


def test_manhattan_route_obstacle_on_second_vertical_leg() -> None:
    """Obstacle on the *second* vertical segment (at x2) forces a detour."""
    obstacle = NodeRect(x_min=75.0, y_min=90.0, x_max=85.0, y_max=110.0)
    coords = manhattan_route(10.0, 0.0, 80.0, 200.0, obstacles=[obstacle])
    _assert_no_segment_crosses_any_rect(coords, [obstacle])


# ---------------------------------------------------------------------------
# Dense graph: IOP horizontal-first edge must not cross obstacles (Bug C)
# ---------------------------------------------------------------------------


def _make_dense_grid_obstacles(
    cols: int = 6,
    rows: int = 6,
    node_w: float = 76.0,
    node_h: float = 76.0,
    gap_x: float = 30.0,
    gap_y: float = 132.0,
    origin_x: float = 100.0,
    origin_y: float = 100.0,
    padding: float = 4.0,
) -> list[NodeRect]:
    """Build a grid of padded node rects simulating a dense pcode graph."""
    rects: list[NodeRect] = []
    for col in range(cols):
        cx = origin_x + col * (node_w + gap_x)
        for row in range(rows):
            cy = origin_y + row * (node_h + gap_y)
            rects.append(
                NodeRect(
                    x_min=cx - node_w / 2.0 - padding,
                    y_min=cy - node_h / 2.0 - padding,
                    x_max=cx + node_w / 2.0 + padding,
                    y_max=cy + node_h / 2.0 + padding,
                )
            )
    return rects


def test_horizontal_first_dense_grid_no_crossing() -> None:
    """IOP edge across dense 6x6 grid must not cross any intermediate node."""
    obstacles = _make_dense_grid_obstacles()
    leftmost_x = obstacles[0].x_min - 20.0
    rightmost_x = obstacles[-1].x_max + 20.0
    src_y = 100.0
    tgt_y = 100.0 + 3 * (76.0 + 132.0)

    coords = manhattan_route(
        leftmost_x,
        src_y,
        rightmost_x,
        tgt_y,
        obstacles=obstacles,
        first_axis="horizontal",
    )
    safe_obstacles = _filter_endpoint_obstacles(
        obstacles,
        leftmost_x,
        src_y,
        rightmost_x,
        tgt_y,
    )
    _assert_no_segment_crosses_any_rect(coords, safe_obstacles)


def test_horizontal_first_many_obstacles_on_midpoint_column() -> None:
    """8 obstacles stacked on the naive midpoint x must not block routing."""
    mid_x = 500.0
    half_w = 38.0 + 4.0
    obstacles = [
        NodeRect(
            x_min=mid_x - half_w,
            y_min=100.0 + i * 80.0,
            x_max=mid_x + half_w,
            y_max=100.0 + i * 80.0 + 60.0,
        )
        for i in range(8)
    ]
    coords = manhattan_route(
        0.0,
        300.0,
        1000.0,
        400.0,
        obstacles=obstacles,
        first_axis="horizontal",
    )
    _assert_no_segment_crosses_any_rect(coords, obstacles)


# ---------------------------------------------------------------------------
# Distance minimization: aligned endpoints produce shorter paths
# ---------------------------------------------------------------------------


def test_aligned_vertical_produces_direct_segment() -> None:
    """When x1 ≈ x2, _build_initial_waypoints returns a 2-point path."""
    wp = _build_initial_waypoints(100.0, 0.0, 100.0, 200.0, "vertical")
    assert len(wp) == 2
    assert wp == [(100.0, 0.0), (100.0, 200.0)]


def test_aligned_horizontal_produces_direct_segment() -> None:
    """When y1 ≈ y2, _build_initial_waypoints returns a 2-point path."""
    wp = _build_initial_waypoints(0.0, 50.0, 300.0, 50.0, "horizontal")
    assert len(wp) == 2
    assert wp == [(0.0, 50.0), (300.0, 50.0)]


def test_near_aligned_within_threshold() -> None:
    """Endpoints within 1px threshold are treated as aligned."""
    wp = _build_initial_waypoints(100.0, 0.0, 100.5, 200.0, "vertical")
    assert len(wp) == 2


def test_not_aligned_beyond_threshold() -> None:
    """Endpoints beyond the near-alignment ratio still get the 4-point path."""
    wp = _build_initial_waypoints(100.0, 0.0, 130.0, 200.0, "vertical")
    assert len(wp) == 4


# ---------------------------------------------------------------------------
# Regression: nearly-aligned edges must not have wasteful midpoint jogs
# ---------------------------------------------------------------------------


def _path_total_length(coords: list[float]) -> float:
    """Sum of segment lengths in a flat coordinate list."""
    total = 0.0
    for i in range(0, len(coords) - 2, 2):
        dx = coords[i + 2] - coords[i]
        dy = coords[i + 3] - coords[i + 1]
        total += abs(dx) + abs(dy)
    return total


def test_nearly_aligned_vertical_minimizes_distance() -> None:
    """Slot-offset anchors (small dx) must not place a horizontal jog at mid-y."""
    coords = manhattan_route(97.5, 0.0, 102.5, 200.0)
    wps = _coords_to_waypoints(coords)

    mid_y = 100.0
    horizontal_at_mid = any(
        wps[i][1] == wps[i + 1][1] == mid_y and wps[i][0] != wps[i + 1][0]
        for i in range(len(wps) - 1)
    )
    assert not horizontal_at_mid, f"path has a horizontal jog at mid-y={mid_y}: {wps}"


# ---------------------------------------------------------------------------
# Regression: obstacle on mid-y horizontal segment must not create S-shape
# ---------------------------------------------------------------------------


def test_obstacle_on_midpoint_horizontal_avoids_s_shape() -> None:
    """Blocked default mid_y must not create an S-shaped detour."""
    obstacle = NodeRect(x_min=400.0, y_min=270.0, x_max=470.0, y_max=330.0)
    coords = manhattan_route(460.0, 0.0, 560.0, 600.0, obstacles=[obstacle])
    _assert_no_segment_crosses_any_rect(coords, [obstacle])

    optimal_length = abs(460.0 - 560.0) + abs(0.0 - 600.0)
    actual_length = _path_total_length(coords)
    assert actual_length <= optimal_length * 1.05, (
        f"path length {actual_length:.1f} exceeds 105% of optimal {optimal_length:.1f}, "
        f"likely S-shape detour. Waypoints: {_coords_to_waypoints(coords)}"
    )


def test_obstacle_on_midpoint_horizontal_still_avoids_obstacle() -> None:
    """Mid-y optimization must still produce a collision-free path."""
    obstacle = NodeRect(x_min=430.0, y_min=10.0, x_max=570.0, y_max=590.0)
    coords = manhattan_route(460.0, 0.0, 540.0, 600.0, obstacles=[obstacle])
    _assert_no_segment_crosses_any_rect(coords, [obstacle])


# -- Dense grid: S-shape cascade regression ------------------------------------


def _make_4x3_grid_obstacles() -> list[NodeRect]:
    node_w, node_h, pad = 80.0, 30.0, 4.0
    gap_x, gap_y = 40.0, 50.0
    rects: list[NodeRect] = []
    for row in range(4):
        for col in range(3):
            cx = 200.0 + col * (node_w + gap_x)
            cy = 100.0 + row * (node_h + gap_y)
            rects.append(NodeRect(
                x_min=cx - node_w / 2 - pad, y_min=cy - node_h / 2 - pad,
                x_max=cx + node_w / 2 + pad, y_max=cy + node_h / 2 + pad,
            ))
    return rects


def test_dense_grid_adjacent_column_avoids_s_shape() -> None:
    obstacles = _make_4x3_grid_obstacles()
    coords = manhattan_route(200.0, 119.0, 320.0, 321.0, obstacles=obstacles)
    _assert_no_segment_crosses_any_rect(coords, _filter_endpoint_obstacles(
        obstacles, 200.0, 119.0, 320.0, 321.0,
    ))
    optimal = abs(200.0 - 320.0) + abs(119.0 - 321.0)
    actual = _path_total_length(coords)
    assert actual <= optimal * 1.15, (
        f"path {actual:.0f} exceeds 115% of optimal {optimal:.0f} — "
        f"likely cascading S-shape. Waypoints: {_coords_to_waypoints(coords)}"
    )
