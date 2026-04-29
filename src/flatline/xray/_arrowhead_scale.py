"""Arrowhead scaling utilities for flatline.xray."""

from __future__ import annotations


def _clamp_arrowshape(
    base: tuple[float, float, float],
    zoom: float,
    lo: tuple[float, float, float],
    hi: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Scale base by zoom and clamp each element to [lo[i], hi[i]]."""
    return tuple(max(lo[i], min(hi[i], v * zoom)) for i, v in enumerate(base))
