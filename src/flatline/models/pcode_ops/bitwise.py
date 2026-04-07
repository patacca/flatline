"""Bitwise pcode operations (INT_AND, INT_OR, INT_XOR, etc.)."""

from __future__ import annotations

from dataclasses import dataclass

from flatline.models.pcode_ops._base import BitwiseOp


@dataclass(frozen=True)
class IntNegate(BitwiseOp):
    """Integer bitwise negation operation (INT_NEGATE)."""

    ...


@dataclass(frozen=True)
class IntAnd(BitwiseOp):
    """Integer bitwise AND operation (INT_AND)."""

    ...


@dataclass(frozen=True)
class IntOr(BitwiseOp):
    """Integer bitwise OR operation (INT_OR)."""

    ...


@dataclass(frozen=True)
class IntXor(BitwiseOp):
    """Integer bitwise XOR operation (INT_XOR)."""

    ...


@dataclass(frozen=True)
class IntLeft(BitwiseOp):
    """Integer left shift operation (INT_LEFT)."""

    ...


@dataclass(frozen=True)
class IntRight(BitwiseOp):
    """Integer right shift operation (INT_RIGHT)."""

    ...


@dataclass(frozen=True)
class IntSright(BitwiseOp):
    """Integer signed right shift operation (INT_SRIGHT)."""

    ...


__all__ = [
    "IntAnd",
    "IntLeft",
    "IntNegate",
    "IntOr",
    "IntRight",
    "IntSright",
    "IntXor",
]
