"""Canvas rendering helpers for the flatline.xray graph window.

All functions operate on a ``tk.Canvas`` passed as the first argument so that
the drawing logic is decoupled from the window class.  This module must remain
headless-safe: it imports tkinter lazily (only when the functions are called).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from . import _theme
from ._edge_routing import (
    manhattan_route as manhattan_route,
)
from ._inputs import (
    _opcode_color,
    _varnode_color,
)
from ._layout import (
    VisualNode,
    node_label_lines,
    node_size,
)

if TYPE_CHECKING:
    import tkinter as tk

    from ..models import PcodeOpInfo, VarnodeInfo


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
# Edges
# ---------------------------------------------------------------------------


def draw_routed_edges(
    canvas: tk.Canvas,
    routes: dict[tuple[object, object, object], list[tuple[float, float]]],
) -> None:
    """Draw libavoid-routed graph edges from polyline points."""
    import tkinter as tk

    for source, target, _edge_key in sorted(routes, key=repr):
        polyline = routes[(source, target, _edge_key)]
        coords = [coord for point in polyline for coord in point]
        canvas.create_line(
            *coords,
            fill=_theme.EDGE_INACTIVE_COLOR,
            width=_theme.EDGE_INACTIVE_WIDTH,
            arrow=tk.LAST,
            arrowshape=(12, 14, 6),
            tags=("tree_edge", "arrow_edge"),
        )


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def draw_nodes(
    canvas: tk.Canvas,
    node: VisualNode,
    op_by_id: Mapping[int, PcodeOpInfo],
    varnode_by_id: Mapping[int, VarnodeInfo],
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
    op_by_id: Mapping[int, PcodeOpInfo],
    varnode_by_id: Mapping[int, VarnodeInfo],
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
    op_by_id: Mapping[int, PcodeOpInfo],
    varnode_by_id: Mapping[int, VarnodeInfo],
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
