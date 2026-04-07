"""High-level pcode operations (SEGMENTOP, INSERT, EXTRACT)."""

from __future__ import annotations

from dataclasses import dataclass

from flatline.models.pcode_ops._base import HighLevelOp


@dataclass(frozen=True)
class Segmentop(HighLevelOp):
    """Segment operation (SEGMENTOP)."""

    ...


@dataclass(frozen=True)
class Insert(HighLevelOp):
    """Bit insertion operation (INSERT)."""

    ...


@dataclass(frozen=True)
class Extract(HighLevelOp):
    """Bit extraction operation (EXTRACT)."""

    ...


__all__ = [
    "Extract",
    "Insert",
    "Segmentop",
]
