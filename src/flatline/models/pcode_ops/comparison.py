"""Comparison pcode operations (INT_EQUAL, FLOAT_LESS, etc.)."""

from __future__ import annotations

from dataclasses import dataclass

from flatline.models.pcode_ops._base import ComparisonOp


@dataclass(frozen=True)
class IntEqual(ComparisonOp):
    """Integer equality comparison (INT_EQUAL)."""

    ...


@dataclass(frozen=True)
class IntNotequal(ComparisonOp):
    """Integer inequality comparison (INT_NOTEQUAL)."""

    ...


@dataclass(frozen=True)
class IntLess(ComparisonOp):
    """Integer unsigned less-than comparison (INT_LESS)."""

    ...


@dataclass(frozen=True)
class IntSless(ComparisonOp):
    """Integer signed less-than comparison (INT_SLESS)."""

    ...


@dataclass(frozen=True)
class IntLessequal(ComparisonOp):
    """Integer unsigned less-than-or-equal comparison (INT_LESSEQUAL)."""

    ...


@dataclass(frozen=True)
class IntSlessequal(ComparisonOp):
    """Integer signed less-than-or-equal comparison (INT_SLESSEQUAL)."""

    ...


@dataclass(frozen=True)
class FloatEqual(ComparisonOp):
    """Floating-point equality comparison (FLOAT_EQUAL)."""

    ...


@dataclass(frozen=True)
class FloatNotequal(ComparisonOp):
    """Floating-point inequality comparison (FLOAT_NOTEQUAL)."""

    ...


@dataclass(frozen=True)
class FloatLess(ComparisonOp):
    """Floating-point less-than comparison (FLOAT_LESS)."""

    ...


@dataclass(frozen=True)
class FloatLessequal(ComparisonOp):
    """Floating-point less-than-or-equal comparison (FLOAT_LESSEQUAL)."""

    ...


@dataclass(frozen=True)
class FloatNan(ComparisonOp):
    """Floating-point NaN check (FLOAT_NAN)."""

    ...


__all__ = [
    "FloatEqual",
    "FloatLess",
    "FloatLessequal",
    "FloatNan",
    "FloatNotequal",
    "IntEqual",
    "IntLess",
    "IntLessequal",
    "IntNotequal",
    "IntSless",
    "IntSlessequal",
]
