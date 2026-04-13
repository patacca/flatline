"""Port-slot assignment for distributing multiple edges along a shared node side.

Groups edges by shared anchor points and applies small offsets so parallel
edges never overlap.
"""

from __future__ import annotations

_SLOT_SPACING = 5.0
_SLOT_CORNER_INSET = 8.0


def assign_edge_slots(
    edges: list[tuple[float, float, float, float]],
    source_sizes: list[tuple[float, float]],
    target_sizes: list[tuple[float, float]],
    *,
    source_side: str = "bottom",
    target_side: str = "top",
) -> list[tuple[float, float, float, float]]:
    """Distribute *edges* so that no two share the exact same anchor point.

    Each entry in *edges* is ``(sx, sy, tx, ty)`` — the raw center-based
    anchor for one edge.  *source_sizes* / *target_sizes* give the
    ``(width, height)`` of the source/target node for each edge (parallel
    lists).

    Edges sharing the same source ``(sx, sy)`` are grouped and spread along
    the source side; likewise for targets.  Offsets are applied along the
    axis parallel to the side (x for top/bottom, y for left/right).

    Returns a new list of ``(sx', sy', tx', ty')`` with offsets applied.
    """
    source_groups: dict[tuple[float, float], list[int]] = {}
    for i, (sx, sy, _tx, _ty) in enumerate(edges):
        source_groups.setdefault((sx, sy), []).append(i)

    target_groups: dict[tuple[float, float], list[int]] = {}
    for i, (_sx, _sy, tx, ty) in enumerate(edges):
        target_groups.setdefault((tx, ty), []).append(i)

    result = list(edges)

    for (sx, sy), indices in source_groups.items():
        if len(indices) <= 1:
            continue
        indices.sort(key=lambda i: edges[i][2])
        _apply_slot_offsets(result, indices, sx, sy, source_sizes, source_side, is_source=True)

    for (tx, ty), indices in target_groups.items():
        if len(indices) <= 1:
            continue
        indices.sort(key=lambda i: edges[i][0])
        _apply_slot_offsets(result, indices, tx, ty, target_sizes, target_side, is_source=False)

    return result


def _apply_slot_offsets(
    result: list[tuple[float, float, float, float]],
    indices: list[int],
    anchor_x: float,
    anchor_y: float,
    sizes: list[tuple[float, float]],
    side: str,
    *,
    is_source: bool,
) -> None:
    """Mutate *result* in-place, spreading *indices* around *anchor*."""
    n = len(indices)
    first_idx = indices[0]
    w, h = sizes[first_idx]
    if side in ("top", "bottom"):
        available = w - 2 * _SLOT_CORNER_INSET
        spread = min(_SLOT_SPACING * (n - 1), available)
        start_offset = -spread / 2.0
        for rank, idx in enumerate(indices):
            offset = start_offset + (spread * rank / max(n - 1, 1))
            sx, sy, tx, ty = result[idx]
            if is_source:
                result[idx] = (sx + offset, sy, tx, ty)
            else:
                result[idx] = (sx, sy, tx + offset, ty)
    else:
        available = h - 2 * _SLOT_CORNER_INSET
        spread = min(_SLOT_SPACING * (n - 1), available)
        start_offset = -spread / 2.0
        for rank, idx in enumerate(indices):
            offset = start_offset + (spread * rank / max(n - 1, 1))
            sx, sy, tx, ty = result[idx]
            if is_source:
                result[idx] = (sx, sy + offset, tx, ty)
            else:
                result[idx] = (sx, sy, tx, ty + offset)


__all__ = ["assign_edge_slots"]
