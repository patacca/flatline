"""Edge anchoring helpers for the flatline.xray graph window.

Keeps libavoid's interior routing intact but rewrites the two endpoints
(and prepends/appends short stubs when needed) so every non-self-loop edge
visually exits/arrives at the expected node boundary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._layout import Position

__all__ = ["anchor_polyline_endpoints"]


def anchor_polyline_endpoints(
    polyline: list[tuple[float, float]],
    src_pos: Position,
    tgt_pos: Position,
    axis: str,
) -> list[tuple[float, float]]:
    """Force the polyline to leave/enter along the requested axis.

    * ``vertical``   - exits source bottom, enters target top.
    * ``horizontal`` - exits source side, enters opposite target side.
    """
    if len(polyline) < 2:
        return polyline
    fixed = list(polyline)

    if axis == "vertical":
        src_bottom = src_pos.y + src_pos.h / 2.0
        src_left = src_pos.x - src_pos.w / 2.0
        src_right = src_pos.x + src_pos.w / 2.0
        tgt_top = tgt_pos.y - tgt_pos.h / 2.0
        tgt_left = tgt_pos.x - tgt_pos.w / 2.0
        tgt_right = tgt_pos.x + tgt_pos.w / 2.0

        # Source endpoint: anchor on the bottom edge of the source node.
        first_x, _first_y = fixed[0]
        next_x, next_y = fixed[1]
        src_x = min(max(first_x, src_left), src_right)
        fixed[0] = (src_x, src_bottom)
        if next_x != src_x and next_y != src_bottom:
            # libavoid gave a diagonal first segment after we moved the
            # endpoint.  Insert a bend so the departure from the bottom pin
            # stays vertical then horizontal.
            fixed.insert(1, (src_x, next_y))

        # Target endpoint: anchor on the top edge of the target node.
        last_x, _last_y = fixed[-1]
        prev_x, prev_y = fixed[-2]
        tgt_x = min(max(last_x, tgt_left), tgt_right)
        fixed[-1] = (tgt_x, tgt_top)
        if prev_x != tgt_x and prev_y != tgt_top:
            # Same fix for the target end: keep the final approach vertical.
            fixed.insert(-1, (tgt_x, prev_y))

    elif axis == "horizontal":
        src_top = src_pos.y - src_pos.h / 2.0
        src_bottom = src_pos.y + src_pos.h / 2.0
        src_left = src_pos.x - src_pos.w / 2.0
        src_right = src_pos.x + src_pos.w / 2.0
        tgt_top = tgt_pos.y - tgt_pos.h / 2.0
        tgt_bottom = tgt_pos.y + tgt_pos.h / 2.0
        tgt_left = tgt_pos.x - tgt_pos.w / 2.0
        tgt_right = tgt_pos.x + tgt_pos.w / 2.0

        if tgt_pos.x >= src_pos.x:
            src_x = src_right
            tgt_x = tgt_left
        else:
            src_x = src_left
            tgt_x = tgt_right

        # Source endpoint: anchor on the side edge of the source node.
        _first_x, first_y = fixed[0]
        next_x, next_y = fixed[1]
        src_y = min(max(first_y, src_top), src_bottom)
        fixed[0] = (src_x, src_y)
        if next_x != src_x and next_y != src_y:
            # libavoid gave a diagonal first segment after we moved the
            # endpoint.  Insert a bend so the departure from the side pin
            # stays horizontal then vertical.
            fixed.insert(1, (next_x, src_y))

        # Target endpoint: anchor on the opposite side edge of the target node.
        _last_x, last_y = fixed[-1]
        prev_x, prev_y = fixed[-2]
        tgt_y = min(max(last_y, tgt_top), tgt_bottom)
        fixed[-1] = (tgt_x, tgt_y)
        if prev_x != tgt_x and prev_y != tgt_y:
            # Same fix for the target end: keep the final approach horizontal.
            fixed.insert(-1, (prev_x, tgt_y))

    else:
        raise ValueError(f"Unknown axis {axis!r}; expected 'vertical' or 'horizontal'")
    return fixed
