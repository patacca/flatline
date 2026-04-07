"""Boolean pcode operations (BOOL_AND, BOOL_OR, BOOL_XOR, etc.)."""

from __future__ import annotations

from dataclasses import dataclass

from flatline.models.pcode_ops._base import BooleanOp


@dataclass(frozen=True)
class BoolNegate(BooleanOp):
    """Boolean negation operation (BOOL_NEGATE)."""

    ...


@dataclass(frozen=True)
class BoolAnd(BooleanOp):
    """Boolean AND operation (BOOL_AND)."""

    ...


@dataclass(frozen=True)
class BoolOr(BooleanOp):
    """Boolean OR operation (BOOL_OR)."""

    ...


@dataclass(frozen=True)
class BoolXor(BooleanOp):
    """Boolean XOR operation (BOOL_XOR)."""

    ...


__all__ = [
    "BoolAnd",
    "BoolNegate",
    "BoolOr",
    "BoolXor",
]
