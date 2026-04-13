"""Canvas rendering helpers for the flatline.xray graph window.

All functions operate on a ``tk.Canvas`` passed as the first argument so that
the drawing logic is decoupled from the window class.  This module must remain
headless-safe: it imports tkinter lazily (only when the functions are called).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flatline.xray._theme as _theme
from flatline.xray._edge_routing import (
    deconflict_edge_segments,
    manhattan_route,
)
from flatline.xray._edge_slots import assign_edge_slots
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
# Edges
# ---------------------------------------------------------------------------


def _collect_tree_edges(
    node: VisualNode,
    op_by_id: dict,
    varnode_by_id: dict,
) -> list[tuple[VisualNode, VisualNode]]:
    """Return all (child, parent) pairs in the subtree rooted at *node*."""
    result: list[tuple[VisualNode, VisualNode]] = []
    for child in node.children:
        result.append((child, node))
        result.extend(_collect_tree_edges(child, op_by_id, varnode_by_id))
    return result


def draw_all_tree_edges(
    canvas: tk.Canvas,
    visual_roots: list[VisualNode],
    cross_edges: list[tuple[VisualNode, VisualNode]],
    op_by_id: dict,
    varnode_by_id: dict,
    obstacles: list[NodeRect] | None = None,
) -> None:
    """Batch-draw all tree edges and cross edges with port-slot offsets.

    Collects every (child→parent) tree edge and every cross edge, assigns
    slot offsets so edges sharing a node anchor are visually separated, then
    draws each with Manhattan routing.
    """
    import tkinter as tk

    all_pairs: list[tuple[VisualNode, VisualNode]] = []
    for root in visual_roots:
        all_pairs.extend(_collect_tree_edges(root, op_by_id, varnode_by_id))

    cross_pairs = [(child, parent) for parent, child in cross_edges]
    tree_count = len(all_pairs)
    all_pairs.extend(cross_pairs)

    if not all_pairs:
        return

    raw_edges: list[tuple[float, float, float, float]] = []
    src_sizes: list[tuple[float, float]] = []
    tgt_sizes: list[tuple[float, float]] = []
    for source, target in all_pairs:
        sx = source.x
        sy = source.y + node_pad(source, op_by_id, varnode_by_id)
        tx = target.x
        ty = target.y - node_pad(target, op_by_id, varnode_by_id)
        raw_edges.append((sx, sy, tx, ty))
        src_sizes.append(node_size(source, op_by_id, varnode_by_id))
        tgt_sizes.append(node_size(target, op_by_id, varnode_by_id))

    slotted = assign_edge_slots(
        raw_edges, src_sizes, tgt_sizes, source_side="bottom", target_side="top"
    )

    all_routed: list[list[float]] = [
        manhattan_route(sx, sy, tx, ty, obstacles) for sx, sy, tx, ty in slotted
    ]
    all_routed = deconflict_edge_segments(all_routed)

    for idx, coords in enumerate(all_routed):
        if idx < tree_count:
            canvas.create_line(
                *coords,
                fill=_theme.EDGE_INACTIVE_COLOR,
                width=_theme.EDGE_INACTIVE_WIDTH,
                arrow=tk.LAST,
                arrowshape=(12, 14, 6),
                tags=("tree_edge", "arrow_edge"),
            )
        else:
            canvas.create_line(
                *coords,
                fill=_theme.EDGE_RELATED,
                width=1.4,
                dash=(6, 4),
                arrow=tk.LAST,
                arrowshape=(10, 12, 5),
                tags=("cross_edge", "arrow_edge"),
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
