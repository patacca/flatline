"""Dataflow pcode operations (MULTIEQUAL, INDIRECT, PTRADD, PTRSUB)."""

from __future__ import annotations

from dataclasses import dataclass

from flatline.models.pcode_ops._base import DataflowOp


@dataclass(frozen=True)
class Multiequal(DataflowOp):
    """Multiple equal inputs operation (MULTIEQUAL)."""

    ...


@dataclass(frozen=True)
class Indirect(DataflowOp):
    """Indirect operation (INDIRECT)."""

    ...


@dataclass(frozen=True)
class Ptradd(DataflowOp):
    """Pointer addition operation (PTRADD)."""

    ...


@dataclass(frozen=True)
class Ptrsub(DataflowOp):
    """Pointer subtraction operation (PTRSUB)."""

    ...


__all__ = [
    "Indirect",
    "Multiequal",
    "Ptradd",
    "Ptrsub",
]
