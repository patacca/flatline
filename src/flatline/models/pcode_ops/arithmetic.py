"""Arithmetic pcode operations (INT_ADD, INT_SUB, INT_MULT, etc.)."""

from __future__ import annotations

from dataclasses import dataclass

from flatline.models.pcode_ops._base import ArithmeticOp


@dataclass(frozen=True)
class IntAdd(ArithmeticOp):
    """Integer addition operation (INT_ADD)."""

    ...


@dataclass(frozen=True)
class IntSub(ArithmeticOp):
    """Integer subtraction operation (INT_SUB)."""

    ...


@dataclass(frozen=True)
class Int2comp(ArithmeticOp):
    """Integer two's complement negation operation (INT_2COMP)."""

    ...


@dataclass(frozen=True)
class IntCarry(ArithmeticOp):
    """Integer carry operation (INT_CARRY)."""

    ...


@dataclass(frozen=True)
class IntScarry(ArithmeticOp):
    """Integer signed carry operation (INT_SCARRY)."""

    ...


@dataclass(frozen=True)
class IntSborrow(ArithmeticOp):
    """Integer signed borrow operation (INT_SBORROW)."""

    ...


@dataclass(frozen=True)
class IntMult(ArithmeticOp):
    """Integer multiplication operation (INT_MULT)."""

    ...


@dataclass(frozen=True)
class IntDiv(ArithmeticOp):
    """Integer division operation (INT_DIV)."""

    ...


@dataclass(frozen=True)
class IntSdiv(ArithmeticOp):
    """Integer signed division operation (INT_SDIV)."""

    ...


@dataclass(frozen=True)
class IntRem(ArithmeticOp):
    """Integer remainder operation (INT_REM)."""

    ...


@dataclass(frozen=True)
class IntSrem(ArithmeticOp):
    """Integer signed remainder operation (INT_SREM)."""

    ...


@dataclass(frozen=True)
class FloatAdd(ArithmeticOp):
    """Floating-point addition operation (FLOAT_ADD)."""

    ...


@dataclass(frozen=True)
class FloatSub(ArithmeticOp):
    """Floating-point subtraction operation (FLOAT_SUB)."""

    ...


@dataclass(frozen=True)
class FloatMult(ArithmeticOp):
    """Floating-point multiplication operation (FLOAT_MULT)."""

    ...


@dataclass(frozen=True)
class FloatDiv(ArithmeticOp):
    """Floating-point division operation (FLOAT_DIV)."""

    ...


@dataclass(frozen=True)
class FloatAbs(ArithmeticOp):
    """Floating-point absolute value operation (FLOAT_ABS)."""

    ...


@dataclass(frozen=True)
class FloatSqrt(ArithmeticOp):
    """Floating-point square root operation (FLOAT_SQRT)."""

    ...


@dataclass(frozen=True)
class FloatNeg(ArithmeticOp):
    """Floating-point negation operation (FLOAT_NEG)."""

    ...


__all__ = [
    "FloatAbs",
    "FloatAdd",
    "FloatDiv",
    "FloatMult",
    "FloatNeg",
    "FloatSqrt",
    "FloatSub",
    "Int2comp",
    "IntAdd",
    "IntCarry",
    "IntDiv",
    "IntMult",
    "IntRem",
    "IntSborrow",
    "IntScarry",
    "IntSdiv",
    "IntSrem",
    "IntSub",
]
