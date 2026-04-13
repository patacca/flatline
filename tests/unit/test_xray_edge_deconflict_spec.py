from __future__ import annotations

import pytest

from flatline.xray._edge_routing import deconflict_edge_segments
from flatline.xray._edge_slots import assign_edge_slots

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Port-slot spacing (assign_edge_slots)
# ---------------------------------------------------------------------------


def test_assign_edge_slots_single_edge_unchanged() -> None:
    """A single edge has no peers to spread against — returned unchanged."""
    edges = [(100.0, 200.0, 100.0, 300.0)]
    sizes = [(80.0, 40.0)]
    result = assign_edge_slots(edges, sizes, sizes)
    assert result == edges


def test_assign_edge_slots_two_edges_same_source_get_offset() -> None:
    """Two edges sharing the same source anchor get different x offsets."""
    edges = [
        (100.0, 200.0, 50.0, 300.0),
        (100.0, 200.0, 150.0, 300.0),
    ]
    sizes = [(80.0, 40.0), (80.0, 40.0)]
    result = assign_edge_slots(edges, sizes, sizes)
    src_xs = [sx for sx, _, _, _ in result]
    assert src_xs[0] != src_xs[1], "shared-source edges must get different x offsets"


def test_assign_edge_slots_two_edges_same_target_get_offset() -> None:
    """Two edges sharing the same target anchor get different x offsets."""
    edges = [
        (50.0, 100.0, 200.0, 300.0),
        (150.0, 100.0, 200.0, 300.0),
    ]
    sizes = [(80.0, 40.0), (80.0, 40.0)]
    result = assign_edge_slots(edges, sizes, sizes)
    tgt_xs = [tx for _, _, tx, _ in result]
    assert tgt_xs[0] != tgt_xs[1], "shared-target edges must get different x offsets"


def test_assign_edge_slots_side_left_right_offsets_y() -> None:
    """Side-based slots (left/right) distribute along the y axis."""
    edges = [
        (100.0, 200.0, 300.0, 200.0),
        (100.0, 200.0, 300.0, 250.0),
    ]
    sizes = [(80.0, 60.0), (80.0, 60.0)]
    result = assign_edge_slots(edges, sizes, sizes, source_side="right", target_side="left")
    src_ys = [sy for _, sy, _, _ in result]
    assert src_ys[0] != src_ys[1], "side slots must offset along y"


def test_assign_edge_slots_offsets_are_symmetric() -> None:
    """Slot offsets are centered around the original anchor: negative/positive."""
    edges = [
        (100.0, 200.0, 50.0, 300.0),
        (100.0, 200.0, 150.0, 300.0),
    ]
    sizes = [(80.0, 40.0), (80.0, 40.0)]
    result = assign_edge_slots(edges, sizes, sizes)
    sx0 = result[0][0]
    sx1 = result[1][0]
    assert sx0 < 100.0 < sx1 or sx1 < 100.0 < sx0, (
        f"offsets {sx0}, {sx1} are not symmetric around 100.0"
    )


def test_assign_edge_slots_three_edges_all_distinct() -> None:
    """Three edges sharing a source must all get distinct x offsets."""
    edges = [
        (100.0, 200.0, 30.0, 300.0),
        (100.0, 200.0, 100.0, 300.0),
        (100.0, 200.0, 170.0, 300.0),
    ]
    sizes = [(80.0, 40.0)] * 3
    result = assign_edge_slots(edges, sizes, sizes)
    src_xs = [sx for sx, _, _, _ in result]
    assert len(set(src_xs)) == 3, f"expected 3 distinct x values, got {src_xs}"


# ---------------------------------------------------------------------------
# Edge overlap deconfliction
# ---------------------------------------------------------------------------


def test_deconflict_single_edge_unchanged() -> None:
    coords = [10.0, 0.0, 10.0, 100.0]
    result = deconflict_edge_segments([coords])
    assert result == [coords]


def test_deconflict_no_overlap_unchanged() -> None:
    edge_a = [10.0, 0.0, 10.0, 100.0]
    edge_b = [50.0, 0.0, 50.0, 100.0]
    result = deconflict_edge_segments([edge_a, edge_b])
    assert result[0] == edge_a
    assert result[1] == edge_b


def test_deconflict_same_vertical_line_gets_offset() -> None:
    """Two edges on the same vertical x with overlapping y-span get offset."""
    edge_a = [100.0, 0.0, 100.0, 200.0]
    edge_b = [100.0, 50.0, 100.0, 150.0]
    result = deconflict_edge_segments([edge_a, edge_b])
    xs_a = {result[0][0], result[0][2]}
    xs_b = {result[1][0], result[1][2]}
    assert xs_a != xs_b, "overlapping vertical edges must get different x offsets"


def test_deconflict_same_horizontal_line_gets_offset() -> None:
    """Two edges on the same horizontal y with overlapping x-span get offset."""
    edge_a = [0.0, 100.0, 200.0, 100.0]
    edge_b = [50.0, 100.0, 150.0, 100.0]
    result = deconflict_edge_segments([edge_a, edge_b])
    ys_a = {result[0][1], result[0][3]}
    ys_b = {result[1][1], result[1][3]}
    assert ys_a != ys_b, "overlapping horizontal edges must get different y offsets"


def test_deconflict_three_overlapping_all_distinct() -> None:
    """Three edges on the same vertical line all get distinct x offsets."""
    edges = [
        [100.0, 0.0, 100.0, 200.0],
        [100.0, 10.0, 100.0, 190.0],
        [100.0, 20.0, 100.0, 180.0],
    ]
    result = deconflict_edge_segments(edges)
    xs = [result[i][0] for i in range(3)]
    assert len(set(xs)) == 3, f"expected 3 distinct x values, got {xs}"


def test_deconflict_non_overlapping_spans_unchanged() -> None:
    """Two edges on the same x but non-overlapping y-spans stay unchanged."""
    edge_a = [100.0, 0.0, 100.0, 50.0]
    edge_b = [100.0, 200.0, 100.0, 300.0]
    result = deconflict_edge_segments([edge_a, edge_b])
    assert result[0] == edge_a
    assert result[1] == edge_b


# ---------------------------------------------------------------------------
# Regression: multi-segment edges with shared horizontal midpoint
# ---------------------------------------------------------------------------


def _coords_to_waypoints(coords: list[float]) -> list[tuple[float, float]]:
    """Convert a flat coordinate list to (x, y) waypoint pairs."""
    return list(zip(coords[::2], coords[1::2], strict=True))


def test_deconflict_shared_horizontal_midpoint_segment() -> None:
    """Two 4-segment manhattan paths whose horizontal midpoint segments
    share the same y must be offset so they do NOT overlap visually.

    Regression: edges routed from different source/target x but through the
    same mid_y would draw on top of each other on the horizontal segment.
    """
    # Edge A: (100, 0) -> (100, 100) -> (200, 100) -> (200, 200)
    # Edge B: (150, 0) -> (150, 100) -> (250, 100) -> (250, 200)
    # Both have a horizontal segment at y=100 that overlaps in x=[150..200].
    edge_a = [100.0, 0.0, 100.0, 100.0, 200.0, 100.0, 200.0, 200.0]
    edge_b = [150.0, 0.0, 150.0, 100.0, 250.0, 100.0, 250.0, 200.0]
    result = deconflict_edge_segments([edge_a, edge_b])

    wps_a = _coords_to_waypoints(result[0])
    wps_b = _coords_to_waypoints(result[1])
    horiz_y_edge_a = wps_a[1][1]
    horiz_y_edge_b = wps_b[1][1]
    assert abs(horiz_y_edge_a - horiz_y_edge_b) >= 3.0, (
        f"overlapping horizontal midpoint segments must be offset: "
        f"edge_a y={horiz_y_edge_a}, edge_b y={horiz_y_edge_b}"
    )


def test_deconflict_cross_edge_overlaps_tree_edge_horizontal() -> None:
    """L-path edges with slot-offset source y values that land in different
    deconfliction buckets must still be detected and separated.

    Regression: edge-slot offsets shift source y by a few pixels (e.g.
    y=100.0 vs y=102.5).  Both produce L-paths whose horizontal segments
    are close enough to overlap visually but land in different buckets
    because the bucket width (_BUCKET_ROUND=3.0) cannot catch a 2.5px gap
    that straddles a bucket boundary.
    """
    from flatline.xray._edge_routing import manhattan_route

    # Edge A: source y=100.0, L-path horizontal at y=100.0, x=[100..108]
    edge_a = manhattan_route(100.0, 100.0, 108.0, 300.0)
    # Edge B: source y=102.5 (slot offset), L-path horizontal at y=102.5
    edge_b = manhattan_route(104.0, 102.5, 112.0, 302.5)

    wps_a = _coords_to_waypoints(edge_a)
    wps_b = _coords_to_waypoints(edge_b)
    assert len(wps_a) == 3, f"expected L-path, got {wps_a}"
    assert len(wps_b) == 3, f"expected L-path, got {wps_b}"

    result = deconflict_edge_segments([edge_a, edge_b])
    r_a = _coords_to_waypoints(result[0])
    r_b = _coords_to_waypoints(result[1])

    def horiz_ys(wps: list[tuple[float, float]]) -> list[float]:
        return [
            wps[i][1]
            for i in range(len(wps) - 1)
            if abs(wps[i][1] - wps[i + 1][1]) < 0.5 and abs(wps[i][0] - wps[i + 1][0]) > 0.5
        ]

    hy_a = horiz_ys(r_a)
    hy_b = horiz_ys(r_b)
    assert hy_a and hy_b, "deconfliction should preserve horizontal segments"
    assert abs(hy_a[0] - hy_b[0]) >= 3.0, (
        f"near-same-y L-path horizontal segments must be offset: a y={hy_a[0]}, b y={hy_b[0]}"
    )


def test_deconflict_near_same_line_horizontal_segments() -> None:
    """Two horizontal segments at slightly different y (within visual overlap
    tolerance) must still be separated.

    Regression: edges whose midpoint y-values differ by a fraction of a pixel
    (e.g. y=99.8 vs y=100.2) were not bucketed together, causing visual
    overlap even though deconfliction was active.
    """
    # Edge A: horizontal at y=100.0, x=[0..200]
    # Edge B: horizontal at y=100.3, x=[50..150] (nearly same line, overlapping span)
    edge_a = [0.0, 100.0, 200.0, 100.0]
    edge_b = [50.0, 100.3, 150.0, 100.3]
    result = deconflict_edge_segments([edge_a, edge_b])

    wps_a = _coords_to_waypoints(result[0])
    wps_b = _coords_to_waypoints(result[1])
    y_a = wps_a[0][1]
    y_b = wps_b[0][1]
    assert abs(y_a - y_b) >= 3.0, (
        f"near-same-line horizontal segments must be offset: y_a={y_a}, y_b={y_b}"
    )
