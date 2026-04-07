"""Copy pcode operations (COPY, SUBPIECE, PIECE, etc.)."""

from __future__ import annotations

from dataclasses import dataclass

from flatline.models.pcode_ops._base import CopyOp


@dataclass(frozen=True)
class Copy(CopyOp):
    """Data copy operation (COPY)."""

    ...


@dataclass(frozen=True)
class Subpiece(CopyOp):
    """Extract subpiece operation (SUBPIECE)."""

    ...


@dataclass(frozen=True)
class Piece(CopyOp):
    """Concatenate pieces operation (PIECE)."""

    ...


@dataclass(frozen=True)
class Popcount(CopyOp):
    """Population count operation (POPCOUNT)."""

    ...


@dataclass(frozen=True)
class Lzcount(CopyOp):
    """Leading zero count operation (LZCOUNT)."""

    ...


@dataclass(frozen=True)
class IntZext(CopyOp):
    """Integer zero extension operation (INT_ZEXT)."""

    ...


@dataclass(frozen=True)
class IntSext(CopyOp):
    """Integer sign extension operation (INT_SEXT)."""

    ...


@dataclass(frozen=True)
class FloatTrunc(CopyOp):
    """Floating-point truncation operation (FLOAT_TRUNC)."""

    ...


@dataclass(frozen=True)
class FloatCeil(CopyOp):
    """Floating-point ceiling operation (FLOAT_CEIL)."""

    ...


@dataclass(frozen=True)
class FloatFloor(CopyOp):
    """Floating-point floor operation (FLOAT_FLOOR)."""

    ...


@dataclass(frozen=True)
class FloatRound(CopyOp):
    """Floating-point round operation (FLOAT_ROUND)."""

    ...


@dataclass(frozen=True)
class FloatInt2float(CopyOp):
    """Integer to floating-point conversion (FLOAT_INT2FLOAT)."""

    ...


@dataclass(frozen=True)
class FloatFloat2float(CopyOp):
    """Floating-point to floating-point conversion (FLOAT_FLOAT2FLOAT)."""

    ...


@dataclass(frozen=True)
class Cast(CopyOp):
    """Type cast operation (CAST)."""

    ...


@dataclass(frozen=True)
class Cpoolref(CopyOp):
    """Constant pool reference operation (CPOOLREF)."""

    ...


@dataclass(frozen=True)
class New(CopyOp):
    """Object allocation operation (NEW)."""

    ...


__all__ = [
    "Cast",
    "Copy",
    "Cpoolref",
    "FloatCeil",
    "FloatFloat2float",
    "FloatFloor",
    "FloatInt2float",
    "FloatRound",
    "FloatTrunc",
    "IntSext",
    "IntZext",
    "Lzcount",
    "New",
    "Piece",
    "Popcount",
    "Subpiece",
]
