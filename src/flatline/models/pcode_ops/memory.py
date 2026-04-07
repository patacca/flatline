"""Memory pcode operations (LOAD, STORE)."""

from __future__ import annotations

from dataclasses import dataclass

from flatline.models.pcode_ops._base import MemoryOp


@dataclass(frozen=True)
class Load(MemoryOp):
    """Memory load operation (LOAD)."""

    ...


@dataclass(frozen=True)
class Store(MemoryOp):
    """Memory store operation (STORE)."""

    ...


__all__ = [
    "Load",
    "Store",
]
