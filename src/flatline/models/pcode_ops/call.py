"""Call pcode operations (CALL, CALLIND, CALLOTHER, RETURN)."""

from __future__ import annotations

from dataclasses import dataclass

from flatline.models.pcode_ops._base import CallOp


@dataclass(frozen=True)
class Call(CallOp):
    """Direct function call operation (CALL)."""

    ...


@dataclass(frozen=True)
class Callind(CallOp):
    """Indirect function call operation (CALLIND)."""

    ...


@dataclass(frozen=True)
class Callother(CallOp):
    """Other/unusual call operation (CALLOTHER)."""

    ...


@dataclass(frozen=True)
class Return(CallOp):
    """Function return operation (RETURN)."""

    ...


__all__ = [
    "Call",
    "Callind",
    "Callother",
    "Return",
]
