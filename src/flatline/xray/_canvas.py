"""Canvas rendering helpers for the flatline.xray graph window.

All functions operate on a ``tk.Canvas`` passed as the first argument so that
the drawing logic is decoupled from the window class.  This module must remain
headless-safe: it imports tkinter lazily (only when the functions are called).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flatline.xray._theme as _theme
from flatline.xray._inputs import (
    _opcode_color,
    _varnode_color,
)
from flatline.xray._layout import (
    NodeRect,
    VisualNode,
    node_label_lines,
    node_pad,
    node_size,
)

if TYPE_CHECKING:
    import tkinter as tk


# ---------------------------------------------------------------------------
# Depth bands
# ---------------------------------------------------------------------------


def draw_depth_bands(
    canvas: tk.Canvas,
    max_depth: int,
    virtual_width: float,
    virtual_height: float,
    bottom_margin: float,
    level_gap: float,
) -> None:
    """Draw alternating background bands for op-rows and value-rows."""
    for depth in range(max_depth + 1):
        y = virtual_height - bottom_margin - depth * level_gap
        is_op_row = depth % 2 == 0
        fill = _theme.DEPTH_BAND_OP_FILL if is_op_row else _theme.DEPTH_BAND_INPUT_FILL
        outline = _theme.DEPTH_BAND_OP_OUTLINE if is_op_row else _theme.DEPTH_BAND_INPUT_OUTLINE
        label = "Ops" if is_op_row else "Inputs / values"
        canvas.create_rectangle(
            40,
            y - 56,
            virtual_width - 40,
            y + 56,
            fill=fill,
            outline=outline,
            width=1,
        )
        canvas.create_text(
            62,
            y - 40,
            text=f"{label} row {depth}",
            anchor="w",
            fill=_theme.TEXT_MUTED,
            font=_theme.BAND_FONT,
        )


# ---------------------------------------------------------------------------
# Edge routing helpers
# ---------------------------------------------------------------------------

# Small gap between an edge detour and the obstacle boundary it goes around.
_OBSTACLE_MARGIN = 6.0

# Safety limit: how many detour iterations before we give up and return
# the best path found so far.  Prevents runaway loops when obstacles are
# densely packed or overlapping.
_MAX_DETOUR_PASSES = 30


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


def manhattan_route(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    obstacles: list[NodeRect] | None = None,
) -> list[float]:
    """Return a flat polyline that goes from (x1, y1) to (x2, y2) using
    only vertical and horizontal segments, detouring around any *obstacles*.

    Without obstacles (or with an empty list) the result is the classic
    4-point down-horizontal-down path.
    """
    if not obstacles:
        mid_y = (y1 + y2) / 2.0
        return [x1, y1, x1, mid_y, x2, mid_y, x2, y2]

    mid_y = (y1 + y2) / 2.0
    waypoints: list[tuple[float, float]] = [
        (x1, y1),
        (x1, mid_y),
        (x2, mid_y),
        (x2, y2),
    ]

    # Iterative detour: when a horizontal segment overlaps an obstacle,
    # splice in a vertical-horizontal-vertical bypass and rescan.
    for _ in range(_MAX_DETOUR_PASSES):
        fixed = False
        for seg_idx in range(len(waypoints) - 1):
            ax, ay = waypoints[seg_idx]
            bx, by = waypoints[seg_idx + 1]
            if ay != by:
                continue
            seg_y = ay
            x_lo = min(ax, bx)
            x_hi = max(ax, bx)
            for rect in obstacles:
                if not _h_segment_hits(x_lo, x_hi, seg_y, rect):
                    continue
                dist_above = abs(seg_y - rect.y_min)
                dist_below = abs(rect.y_max - seg_y)
                if dist_above <= dist_below:
                    detour_y = rect.y_min - _OBSTACLE_MARGIN
                else:
                    detour_y = rect.y_max + _OBSTACLE_MARGIN

                new_points: list[tuple[float, float]] = [
                    (ax, ay),
                    (ax, detour_y),
                    (bx, detour_y),
                    (bx, by),
                ]
                waypoints[seg_idx : seg_idx + 2] = new_points
                fixed = True
                break
            if fixed:
                break
        if not fixed:
            break

    flat: list[float] = []
    for wx, wy in waypoints:
        flat.append(wx)
        flat.append(wy)
    return flat


def nearest_side_anchors(
    source: VisualNode,
    target: VisualNode,
    op_by_id: dict,
    varnode_by_id: dict,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return (source_point, target_point) using the closest left/right side pair."""
    sw, _sh = node_size(source, op_by_id, varnode_by_id)
    tw, _th = node_size(target, op_by_id, varnode_by_id)
    # Left midpoints: (x - half_w, y), right midpoints: (x + half_w, y)
    s_left = (source.x - sw / 2.0, source.y)
    s_right = (source.x + sw / 2.0, source.y)
    t_left = (target.x - tw / 2.0, target.y)
    t_right = (target.x + tw / 2.0, target.y)
    # Try all 4 pairs; return the pair with shortest Euclidean distance
    pairs = [
        (s_left, t_right),
        (s_right, t_left),
        (s_left, t_left),
        (s_right, t_right),
    ]
    return min(pairs, key=lambda p: (p[0][0] - p[1][0]) ** 2 + (p[0][1] - p[1][1]) ** 2)


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


def draw_edges(
    canvas: tk.Canvas,
    node: VisualNode,
    op_by_id: dict,
    varnode_by_id: dict,
    obstacles: list[NodeRect] | None = None,
) -> None:
    """Recursively draw all tree edges from *node* downward."""
    for child in node.children:
        draw_edge(canvas, child, node, op_by_id, varnode_by_id, obstacles)
        draw_edges(canvas, child, op_by_id, varnode_by_id, obstacles)


def draw_edge(
    canvas: tk.Canvas,
    source: VisualNode,
    target: VisualNode,
    op_by_id: dict,
    varnode_by_id: dict,
    obstacles: list[NodeRect] | None = None,
) -> None:
    """Draw a single orthogonal Manhattan edge from *source* to *target*."""
    import tkinter as tk

    sx = source.x
    sy = source.y + node_pad(source, op_by_id, varnode_by_id)
    tx = target.x
    ty = target.y - node_pad(target, op_by_id, varnode_by_id)
    color = _theme.EDGE_INACTIVE_COLOR
    width = _theme.EDGE_INACTIVE_WIDTH
    coords = manhattan_route(sx, sy, tx, ty, obstacles)
    canvas.create_line(
        *coords,
        fill=color,
        width=width,
        arrow=tk.LAST,
        arrowshape=(12, 14, 6),
    )


def draw_cross_edge(
    canvas: tk.Canvas,
    source: VisualNode,
    target: VisualNode,
    op_by_id: dict,
    varnode_by_id: dict,
    obstacles: list[NodeRect] | None = None,
) -> None:
    """Draw a dashed cross-tree edge between *source* and *target*."""
    import tkinter as tk

    sx = source.x
    sy = source.y + node_pad(source, op_by_id, varnode_by_id)
    tx = target.x
    ty = target.y - node_pad(target, op_by_id, varnode_by_id)
    coords = manhattan_route(sx, sy, tx, ty, obstacles)
    canvas.create_line(
        *coords,
        fill=_theme.EDGE_RELATED,
        width=1.4,
        dash=(6, 4),
        arrow=tk.LAST,
        arrowshape=(10, 12, 5),
    )


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def draw_nodes(
    canvas: tk.Canvas,
    node: VisualNode,
    op_by_id: dict,
    varnode_by_id: dict,
    on_click,
) -> None:
    """Recursively draw all nodes in the subtree rooted at *node*."""
    if node.actual[0] == "op":
        draw_op_node(canvas, node, op_by_id, varnode_by_id, on_click)
    else:
        draw_varnode_node(canvas, node, op_by_id, varnode_by_id, on_click)
    for child in node.children:
        draw_nodes(canvas, child, op_by_id, varnode_by_id, on_click)


def draw_op_node(
    canvas: tk.Canvas,
    node: VisualNode,
    op_by_id: dict,
    varnode_by_id: dict,
    on_click,
) -> None:
    """Draw a single op-node rectangle with shadow and click binding."""
    op = op_by_id[node.actual[1]]
    label_lines = node_label_lines(node, op_by_id, varnode_by_id)
    width, height = node_size(node, op_by_id, varnode_by_id)
    half_w = width / 2.0
    half_h = height / 2.0
    x = node.x
    y = node.y
    tag = f"node-{node.key}"
    canvas.create_rectangle(
        x - half_w + 4,
        y - half_h + 4,
        x + half_w + 4,
        y + half_h + 4,
        fill=_theme.NODE_SHADOW,
        outline="",
        tags=(tag,),
    )
    # Selection glow -- hidden by default, covers shadow when revealed.
    glow_pad = _theme.SELECTION_GLOW_PAD
    canvas.create_rectangle(
        x - half_w - glow_pad,
        y - half_h - glow_pad,
        x + half_w + glow_pad,
        y + half_h + glow_pad,
        fill=_theme.SELECTION_GLOW,
        outline="",
        state="hidden",
        tags=(f"glow-{node.key}", "glow"),
    )
    canvas.create_rectangle(
        x - half_w,
        y - half_h,
        x + half_w,
        y + half_h,
        fill=_opcode_color(op.opcode),
        outline=_theme.NODE_OUTLINE,
        width=2,
        tags=(tag, f"shape-{node.key}"),
    )
    canvas.create_text(
        x,
        y,
        text="\n".join(label_lines),
        fill=_theme.TEXT_ON_NODE,
        font=_theme.NODE_FONT,
        tags=(tag,),
    )
    canvas.tag_bind(
        tag,
        "<Button-1>",
        lambda _event, selected=node: on_click(selected),
    )


def draw_varnode_node(
    canvas: tk.Canvas,
    node: VisualNode,
    op_by_id: dict,
    varnode_by_id: dict,
    on_click,
) -> None:
    """Draw a single varnode oval (or triangle for constants) with click binding."""
    varnode = varnode_by_id[node.actual[1]]
    label_lines = node_label_lines(node, op_by_id, varnode_by_id)
    width, height = node_size(node, op_by_id, varnode_by_id)
    half_w = width / 2.0
    half_h = height / 2.0
    x = node.x
    y = node.y
    tag = f"node-{node.key}"
    fill = _varnode_color(varnode)
    if varnode.flags.is_constant:
        shadow_points = (
            x,
            y - half_h + 4,
            x - half_w + 4,
            y + half_h + 4,
            x + half_w + 4,
            y + half_h + 4,
        )
        points = (
            x,
            y - half_h,
            x - half_w,
            y + half_h,
            x + half_w,
            y + half_h,
        )
        canvas.create_polygon(
            shadow_points,
            fill=_theme.NODE_SHADOW,
            outline="",
            tags=(tag,),
        )
        # Selection glow -- hidden triangle, covers shadow when revealed.
        glow_pad = _theme.SELECTION_GLOW_PAD
        canvas.create_polygon(
            x,
            y - half_h - glow_pad,
            x - half_w - glow_pad,
            y + half_h + glow_pad,
            x + half_w + glow_pad,
            y + half_h + glow_pad,
            fill=_theme.SELECTION_GLOW,
            outline="",
            state="hidden",
            tags=(f"glow-{node.key}", "glow"),
        )
        canvas.create_polygon(
            points,
            fill=fill,
            outline=_theme.NODE_OUTLINE_ALT,
            width=2,
            tags=(tag, f"shape-{node.key}"),
        )
    else:
        canvas.create_oval(
            x - half_w + 4,
            y - half_h + 4,
            x + half_w + 4,
            y + half_h + 4,
            fill=_theme.NODE_SHADOW,
            outline="",
            tags=(tag,),
        )
        # Selection glow -- hidden oval, covers shadow when revealed.
        glow_pad = _theme.SELECTION_GLOW_PAD
        canvas.create_oval(
            x - half_w - glow_pad,
            y - half_h - glow_pad,
            x + half_w + glow_pad,
            y + half_h + glow_pad,
            fill=_theme.SELECTION_GLOW,
            outline="",
            state="hidden",
            tags=(f"glow-{node.key}", "glow"),
        )
        canvas.create_oval(
            x - half_w,
            y - half_h,
            x + half_w,
            y + half_h,
            fill=fill,
            outline=_theme.NODE_OUTLINE_ALT,
            width=2,
            tags=(tag, f"shape-{node.key}"),
        )
    canvas.create_text(
        x,
        y + (6 if varnode.flags.is_constant else 0),
        text="\n".join(label_lines),
        fill=_theme.TEXT_ON_NODE,
        font=_theme.VARNODE_FONT,
        tags=(tag,),
    )
    canvas.tag_bind(
        tag,
        "<Button-1>",
        lambda _event, selected=node: on_click(selected),
    )


# ---------------------------------------------------------------------------
# Selection glow helpers
# ---------------------------------------------------------------------------


def show_node_glow(canvas: tk.Canvas, key: str, color: str) -> None:
    """Reveal the pre-drawn glow halo behind a node and set its color."""
    canvas.itemconfigure(f"glow-{key}", fill=color, state="normal")


def hide_all_glows(canvas: tk.Canvas) -> None:
    """Hide every glow halo on the canvas."""
    canvas.itemconfigure("glow", state="hidden")
