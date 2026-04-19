"""Manhattan edge routing and segment deconfliction for flatline.xray.

Computes obstacle-avoiding polyline paths between nodes and offsets edges
that would otherwise share the same visual line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flatline.xray._layout import NodeRect, VisualNode, node_size

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

_OBSTACLE_MARGIN = 6.0
_MAX_DETOUR_PASSES = 30

# Minimum pixel offset applied between edges that would otherwise share the
# same vertical or horizontal line.
_EDGE_PARALLEL_SPACING = 6.0

# Two segment coordinates are considered "on the same line" when they differ
# by less than this.
_EDGE_OVERLAP_TOLERANCE = 0.5

# Number of evenly-spaced candidate midpoints tested when the default midpoint
# is blocked by an obstacle.  Higher values find tighter paths at the cost of
# a linear scan.
_MIDPOINT_CANDIDATES = 20


def _h_segment_hits(
    x_lo: float,
    x_hi: float,
    seg_y: float,
    rect: NodeRect,
) -> bool:
    """Return True if a horizontal segment at *seg_y* from *x_lo* to *x_hi*
    overlaps *rect*.  Both ranges are treated as closed intervals.
    """
    return x_hi >= rect.x_min and x_lo <= rect.x_max and rect.y_min <= seg_y <= rect.y_max


def _v_segment_hits(
    y_lo: float,
    y_hi: float,
    seg_x: float,
    rect: NodeRect,
) -> bool:
    """Return True if a vertical segment at *seg_x* from *y_lo* to *y_hi*
    overlaps *rect*.  Both ranges are treated as closed intervals.
    """
    return y_hi >= rect.y_min and y_lo <= rect.y_max and rect.x_min <= seg_x <= rect.x_max


def _point_in_rect(px: float, py: float, rect: NodeRect) -> bool:
    """Return True if point (px, py) lies inside *rect* (inclusive)."""
    return rect.x_min <= px <= rect.x_max and rect.y_min <= py <= rect.y_max


def _h_segment_blocked(
    x_lo: float,
    x_hi: float,
    seg_y: float,
    obstacles: list[NodeRect],
) -> int:
    """Return the number of obstacles that are crossed by a horizontal segment at *seg_y*
    from *x_lo* to *x_hi*
    """
    return sum(1 for r in obstacles if _h_segment_hits(x_lo, x_hi, seg_y, r))


def _v_segment_blocked(
    y_lo: float,
    y_hi: float,
    seg_x: float,
    obstacles: list[NodeRect],
) -> int:
    """Return the number of obstacles that are crossed by a vertical segment at *seg_x*
    from *y_lo* to *y_hi*
    """
    return sum(1 for r in obstacles if _v_segment_hits(y_lo, y_hi, seg_x, r))


def _find_clear_midpoint_y(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    obstacles: list[NodeRect],
    transpose: bool = False,
) -> float:
    """Find a mid_y where the full Z-shape path crosses the fewest obstacles.
    If ``transpose`` is enabled the obstacles coordinates are transposed as in a
    symetry along y=x

    Tests the horizontal segment at mid_y AND the two vertical legs
    (x1: y1→mid_y) and (x2: mid_y→y2).  Returns the candidate with the fewer blockers,
    if there are multiple it returns the one closest to the geometric midpoint.
    """
    mid_y = (y1 + y2) / 2.0
    x_lo, x_hi = min(x1, x2), max(x1, x2)

    def _z_path_blocked(candidate: float) -> bool:
        total = 0
        v1_lo, v1_hi = min(y1, candidate), max(y1, candidate)
        v2_lo, v2_hi = min(candidate, y2), max(candidate, y2)

        if transpose:
            # When transposing the horizontal segment (x_lo, x_hi) becomes vertical but the
            # coordinates remain the same, even though they represents coordinates for the y-axis.
            # Same goes the the y-coordinate `candidate` that becomes a x-coord with the same value
            # and for the vertical segments (v1_lo, v1_hi) and (v2_lo, v2_hi).
            total += _v_segment_blocked(x_lo, x_hi, candidate, obstacles)
            total += _h_segment_blocked(v1_lo, v1_hi, x1, obstacles)
            total += _h_segment_blocked(v2_lo, v2_hi, x2, obstacles)
        else:
            total += _h_segment_blocked(x_lo, x_hi, candidate, obstacles)
            total += _v_segment_blocked(v1_lo, v1_hi, x1, obstacles)
            total += _v_segment_blocked(v2_lo, v2_hi, x2, obstacles)
        return total

    if _z_path_blocked(mid_y) == 0:
        return mid_y

    lo_y, hi_y = min(y1, y2), max(y1, y2)
    best: tuple[int, float, float] = ()  # (blockers, distance to mid_y, candidate)
    step = (hi_y - lo_y) / (_MIDPOINT_CANDIDATES + 1)
    for i in range(1, _MIDPOINT_CANDIDATES + 1):
        candidate = lo_y + i * step
        blockers = _z_path_blocked(candidate)
        curr = (blockers, abs(candidate - mid_y), candidate)
        if not best or curr < best:
            best = curr
    return best[2]


def _filter_endpoint_obstacles(
    obstacles: list[NodeRect],
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> list[NodeRect]:
    """Return obstacles excluding any that contain the start or end point.

    Without this filter, vertical/horizontal segment checks would
    immediately flag the padded source/target node rects as collisions
    since the anchor sits right on (or inside) their boundary.
    """
    return [
        r for r in obstacles if not _point_in_rect(x1, y1, r) and not _point_in_rect(x2, y2, r)
    ]


def _build_initial_waypoints(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    first_axis: str,
    obstacles: list[NodeRect] | None = None,
) -> list[tuple[float, float]]:
    """Build the initial waypoint path based on *first_axis*.

    When source and target are aligned (or nearly so) along the routing
    axis, produces a minimal 2-point straight segment.  When nearly aligned
    (small offset relative to the main span), produces a 3-point L-shaped
    path with the displacement at the source end, avoiding visible midpoint
    zigzag.

    When *obstacles* are supplied and the default geometric midpoint is
    blocked, the midpoint is shifted to an obstacle-free position to avoid
    costly S-shaped detours in the downstream obstacle-avoidance pass.

    ``"vertical"`` (default): vertical → horizontal → vertical.
    ``"horizontal"``: horizontal → vertical → horizontal.
    """
    _ALIGN_THRESHOLD = 1.0
    _NEAR_ALIGN_RATIO = 0.1

    def _transpose(points: Iterable[Sequence[int]]) -> list[tuple[int]]:
        """
        Swaps the x and y coordinates of every point in ``points``, equivalent
        to a reflection over y=x, ONLY if ``first_axis == "horizontal"``

        points: An iterable of 2D coordinate pairs (x, y)
        """
        return [(p[1], p[0]) for p in points] if first_axis == "horizontal" else list(points)

    # Apply symmetry over y=x only for horizontal lines, so we always work with vertical lines
    (x1, y1), (x2, y2) = _transpose(((x1, y1), (x2, y2)))

    dx = abs(x1 - x2)
    dy = abs(y1 - y2)
    if dx <= _ALIGN_THRESHOLD:
        return _transpose(((x1, y1), (x2, y2)))
    if dy > 0 and dx / dy < _NEAR_ALIGN_RATIO:
        return _transpose(((x1, y1), (x1, y2), (x2, y2)))
    mid_y = (y1 + y2) / 2.0
    if obstacles:
        mid_y = _find_clear_midpoint_y(
            x1, y1, x2, y2, obstacles, transpose=first_axis == "horizontal"
        )
    return _transpose(((x1, y1), (x1, mid_y), (x2, mid_y), (x2, y2)))


def _collapse_collinear(
    waypoints: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Remove interior points that are collinear with their neighbours.

    This cleans up redundant waypoints introduced by repeated detour
    splicing (e.g. zero-length segments or three consecutive points on the
    same horizontal/vertical line).
    """
    if len(waypoints) <= 2:
        return waypoints
    result: list[tuple[float, float]] = [waypoints[0]]
    for i in range(1, len(waypoints) - 1):
        px, py = waypoints[i - 1]
        cx, cy = waypoints[i]
        nx, ny = waypoints[i + 1]
        # Skip if all three are on the same horizontal or vertical line.
        if (px == cx == nx) or (py == cy == ny):
            continue
        result.append((cx, cy))
    result.append(waypoints[-1])
    return result


def _coords_to_waypoints(coords: list[float]) -> list[tuple[float, float]]:
    return list(zip(coords[::2], coords[1::2], strict=True))


def _waypoints_to_coords(waypoints: list[tuple[float, float]]) -> list[float]:
    return [c for pt in waypoints for c in pt]


def _segments_overlap_on_line(
    a_lo: float,
    a_hi: float,
    b_lo: float,
    b_hi: float,
) -> bool:
    """True if two 1-D ranges share any interior overlap (not just touching)."""
    return min(a_hi, b_hi) > max(a_lo, b_lo) + _EDGE_OVERLAP_TOLERANCE


def deconflict_edge_segments(
    all_coords: list[list[float]],
) -> list[list[float]]:
    """Offset edges that share the same vertical or horizontal line.

    Scans every pair of routed polylines for segments that run along the
    same coordinate (same x for vertical, same y for horizontal) with
    overlapping span.  When found, the segments are offset symmetrically
    so they run in parallel rather than overlapping.

    Mutates nothing — returns a new list of coordinate lists.
    """
    if len(all_coords) <= 1:
        return [list(c) for c in all_coords]

    edge_wps: list[list[tuple[float, float]]] = [_coords_to_waypoints(c) for c in all_coords]

    # Group segments by orientation and rounded axis coordinate.
    # Each entry is (edge_index, seg_index, axis_coord, span_lo, span_hi).
    # Bucket granularity must be wide enough to catch segments on visually
    # "near-same" lines (e.g. y=100.0 vs y=100.3 from slot offsets).
    _BUCKET_ROUND = _EDGE_PARALLEL_SPACING / 2.0

    def _round_key(val: float) -> float:
        return round(val / _BUCKET_ROUND) * _BUCKET_ROUND

    vert_buckets: dict[float, list[tuple[int, int, float, float, float]]] = {}
    horiz_buckets: dict[float, list[tuple[int, int, float, float, float]]] = {}

    def _insert_into_buckets(
        buckets: dict[float, list[tuple[int, int, float, float, float]]],
        coord: float,
        entry: tuple[int, int, float, float, float],
    ) -> None:
        """Insert into primary bucket and the nearest neighbour bucket.

        Segments near a bucket boundary (e.g. y=100 at boundary between
        99-bucket and 102-bucket) must appear in both so that nearby
        segments in the adjacent bucket are always compared.
        """
        primary = _round_key(coord)
        buckets.setdefault(primary, []).append(entry)
        remainder = coord - primary
        neighbor = primary + (_BUCKET_ROUND if remainder >= 0 else -_BUCKET_ROUND)
        buckets.setdefault(neighbor, []).append(entry)

    for ei, wps in enumerate(edge_wps):
        for si in range(len(wps) - 1):
            ax, ay = wps[si]
            bx, by = wps[si + 1]
            if abs(ax - bx) <= _EDGE_OVERLAP_TOLERANCE and abs(ay - by) > _EDGE_OVERLAP_TOLERANCE:
                lo, hi = (min(ay, by), max(ay, by))
                _insert_into_buckets(vert_buckets, ax, (ei, si, ax, lo, hi))
            elif (
                abs(ay - by) <= _EDGE_OVERLAP_TOLERANCE and abs(ax - bx) > _EDGE_OVERLAP_TOLERANCE
            ):
                lo, hi = (min(ax, bx), max(ax, bx))
                _insert_into_buckets(horiz_buckets, ay, (ei, si, ay, lo, hi))

    offsets: dict[tuple[int, int], float] = {}
    seen_pairs: set[tuple[int, int, int, int]] = set()

    def _assign_offsets(
        bucket: list[tuple[int, int, float, float, float]],
    ) -> None:
        """Find overlapping segment pairs within a bucket and assign offsets."""
        # Deduplicate: same (ei, si) may appear from primary + neighbour bucket.
        deduped: dict[tuple[int, int], tuple[int, int, float, float, float]] = {}
        for entry in bucket:
            key = (entry[0], entry[1])
            if key not in deduped:
                deduped[key] = entry
        unique = sorted(deduped.values(), key=lambda s: s[3])
        n = len(unique)
        if n <= 1:
            return
        groups: list[list[int]] = []
        assigned: set[int] = set()
        for i in range(n):
            if i in assigned:
                continue
            group = [i]
            assigned.add(i)
            ei_i, _, coord_i, lo_i, hi_i = unique[i]
            for j in range(i + 1, n):
                if j in assigned:
                    continue
                ei_j, _, coord_j, lo_j, hi_j = unique[j]
                if ei_i == ei_j:
                    continue
                if abs(coord_i - coord_j) > _BUCKET_ROUND:
                    continue
                if _segments_overlap_on_line(lo_i, hi_i, lo_j, hi_j):
                    group.append(j)
                    assigned.add(j)
            if len(group) > 1:
                groups.append(group)

        for group in groups:
            pair_key = tuple(sorted((unique[idx][0], unique[idx][1]) for idx in group))
            flat_key = tuple(c for p in pair_key for c in p)
            if flat_key in seen_pairs:
                continue
            seen_pairs.add(flat_key)

            count = len(group)
            spread = _EDGE_PARALLEL_SPACING * (count - 1)
            start = -spread / 2.0
            for rank, idx in enumerate(group):
                ei, si, _coord, _lo, _hi = unique[idx]
                offset = start + rank * _EDGE_PARALLEL_SPACING
                key = (ei, si)
                offsets[key] = offsets.get(key, 0.0) + offset

    for bucket in vert_buckets.values():
        _assign_offsets(bucket)
    for bucket in horiz_buckets.values():
        _assign_offsets(bucket)

    if not offsets:
        return [list(c) for c in all_coords]

    result_wps = [list(wps) for wps in edge_wps]
    for (ei, si), offset in offsets.items():
        wps = result_wps[ei]
        ax, ay = wps[si]
        bx, by = wps[si + 1]
        if abs(ax - bx) <= _EDGE_OVERLAP_TOLERANCE:
            wps[si] = (ax + offset, ay)
            wps[si + 1] = (bx + offset, by)
        else:
            wps[si] = (ax, ay + offset)
            wps[si + 1] = (bx, by + offset)

    return [_waypoints_to_coords(wps) for wps in result_wps]


def _find_reconnect_index(
    waypoints: list[tuple[float, float]],
    seg_idx: int,
    rect: NodeRect,
) -> int:
    """Scan forward from *seg_idx + 1* to find the first waypoint outside *rect*.

    Intermediate waypoints that sit inside the obstacle are skipped so the
    detour splice reconnects to a point that is actually reachable.
    """
    reconnect = seg_idx + 1
    while reconnect < len(waypoints) - 1 and _point_in_rect(*waypoints[reconnect], rect):
        reconnect += 1
    return reconnect


def _detour_segment(
    waypoints: list[tuple[float, float]],
    seg_idx: int,
    rect: NodeRect,
    *,
    horizontal: bool,
) -> bool:
    """Try to splice a detour around *rect* for the segment at *seg_idx*.

    Works for both horizontal segments (*horizontal=True*, where the
    segment has constant y) and vertical segments (*horizontal=False*,
    constant x).  The two cases are structurally identical with swapped
    axis roles, so a single ``(main, cross)`` abstraction handles both.

    Returns True and mutates *waypoints* in-place when a detour is
    spliced; returns False when the segment does not hit *rect*.
    """
    ax, ay = waypoints[seg_idx]
    bx, by = waypoints[seg_idx + 1]

    # Identify the axis roles: "main" is the axis along which the segment
    # travels (variable coordinate), "cross" is the constant coordinate.
    if horizontal:
        main_a, main_b, cross = ax, bx, ay
        main_lo, main_hi = min(ax, bx), max(ax, bx)
        if not _h_segment_hits(main_lo, main_hi, cross, rect):
            return False
        dist_neg = abs(cross - rect.y_min)
        dist_pos = abs(rect.y_max - cross)
        detour_cross = (
            rect.y_min - _OBSTACLE_MARGIN
            if dist_neg <= dist_pos
            else rect.y_max + _OBSTACLE_MARGIN
        )
        enter_main = rect.x_min - _OBSTACLE_MARGIN
        exit_main = rect.x_max + _OBSTACLE_MARGIN
    else:
        main_a, main_b, cross = ay, by, ax
        main_lo, main_hi = min(ay, by), max(ay, by)
        if not _v_segment_hits(main_lo, main_hi, cross, rect):
            return False
        dist_neg = abs(cross - rect.x_min)
        dist_pos = abs(rect.x_max - cross)
        detour_cross = (
            rect.x_min - _OBSTACLE_MARGIN
            if dist_neg <= dist_pos
            else rect.x_max + _OBSTACLE_MARGIN
        )
        enter_main = rect.y_min - _OBSTACLE_MARGIN
        exit_main = rect.y_max + _OBSTACLE_MARGIN

    if main_a > main_b:
        enter_main, exit_main = exit_main, enter_main

    reconnect = _find_reconnect_index(waypoints, seg_idx, rect)
    bx, by = waypoints[reconnect]

    # Build the 6-point detour splice.  For a horizontal segment the detour
    # goes: keep-y -> enter-x -> shift-y -> exit-x -> restore-y -> end.
    # For vertical, the pattern is transposed: keep-x -> enter-y -> shift-x
    # -> exit-y -> restore-x -> end.
    if horizontal:
        splice = [
            (ax, ay),
            (enter_main, ay),
            (enter_main, detour_cross),
            (exit_main, detour_cross),
            (exit_main, by),
            (bx, by),
        ]
    else:
        splice = [
            (ax, ay),
            (ax, enter_main),
            (detour_cross, enter_main),
            (detour_cross, exit_main),
            (bx, exit_main),
            (bx, by),
        ]

    waypoints[seg_idx : reconnect + 1] = splice
    return True


def _optimize_path(
    waypoints: list[tuple[float, float]], obstacles: list[NodeRect] | None = None
) -> list[tuple[float, float]]:
    if not waypoints:
        return []
    if len(waypoints) < 3:  # Simple one or two points path, cannot be improved
        return waypoints.copy()

    # Coloring each point to tell from which direction it was reached.
    # S=Start E=End U=Up D=Down L=Left R=Right I=Ignore
    colors = ["S"]  # Start
    for i, p in enumerate(waypoints[1:-1]):
        prev = waypoints[i - 1]
        if prev[0] == p[0] and prev[1] < p[1]:
            colors.append("D")
        elif prev[0] == p[0] and prev[1] > p[1]:
            colors.append("U")
        elif prev[1] == p[1] and prev[0] < p[0]:
            colors.append("L")
        elif prev[1] == p[1] and prev[0] > p[0]:
            colors.append("R")
        else:  # Non-aligned edge, leave it alone
            colors.append("I")
    colors.append("E")  # End

    # TODO
    # result = []
    i = 0
    while i < len(waypoints):
        # URU/ULU/DRD/DLD -> L
        if 1:
            pass
        # URU/ULU/DRD/DLD -> L
        if 1:
            pass
        i+=1

    waypoints = _collapse_collinear(waypoints)
    return waypoints


def manhattan_route(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    obstacles: list[NodeRect] | None = None,
    *,
    first_axis: str = "vertical",
) -> list[float]:
    """Return a flat polyline that goes from (x1, y1) to (x2, y2) using
    only vertical and horizontal segments, detouring around any *obstacles*.

    *first_axis* controls the initial path shape:
    - ``"vertical"`` (default): down -> horizontal -> down (classic tree edge).
    - ``"horizontal"``: right -> vertical -> right (for side-to-side IOP edges).

    Obstacles that contain the start or end point are automatically
    excluded so that anchor points sitting on padded node boundaries
    do not trigger false detours.
    """
    if not obstacles:
        wp = _build_initial_waypoints(x1, y1, x2, y2, first_axis)
        return [c for pt in wp for c in pt]

    safe_obstacles = _filter_endpoint_obstacles(obstacles, x1, y1, x2, y2)
    waypoints = _build_initial_waypoints(x1, y1, x2, y2, first_axis, safe_obstacles)

    for _ in range(_MAX_DETOUR_PASSES):
        fixed = _detour_one_segment(waypoints, safe_obstacles)
        if not fixed:
            break

    waypoints = _optimize_path(waypoints, safe_obstacles)
    return [c for pt in waypoints for c in pt]


def _detour_one_segment(
    waypoints: list[tuple[float, float]],
    safe_obstacles: list[NodeRect],
) -> bool:
    """Scan *waypoints* for the first segment that hits an obstacle and splice a detour.

    Returns True if a detour was applied, False if all segments are clear.
    """
    for seg_idx in range(len(waypoints) - 1):
        ax, ay = waypoints[seg_idx]
        bx, by = waypoints[seg_idx + 1]

        is_horizontal = ay == by
        is_vertical = ax == bx
        if not is_horizontal and not is_vertical:
            continue

        for rect in safe_obstacles:
            if _detour_segment(waypoints, seg_idx, rect, horizontal=is_horizontal):
                return True

    return False


def nearest_side_anchors(
    source: VisualNode,
    target: VisualNode,
    op_by_id: dict,
    varnode_by_id: dict,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return (source_point, target_point) using the closest left/right side pair."""
    sw, _sh = node_size(source, op_by_id, varnode_by_id)
    tw, _th = node_size(target, op_by_id, varnode_by_id)
    s_left = (source.x - sw / 2.0, source.y)
    s_right = (source.x + sw / 2.0, source.y)
    t_left = (target.x - tw / 2.0, target.y)
    t_right = (target.x + tw / 2.0, target.y)
    pairs = [
        (s_left, t_right),
        (s_right, t_left),
        (s_left, t_left),
        (s_right, t_right),
    ]
    return min(pairs, key=lambda p: (p[0][0] - p[1][0]) ** 2 + (p[0][1] - p[1][1]) ** 2)


__all__ = [
    "deconflict_edge_segments",
    "manhattan_route",
    "nearest_side_anchors",
]
