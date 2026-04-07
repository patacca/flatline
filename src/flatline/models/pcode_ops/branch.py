"""Branch pcode operations (BRANCH, CBRANCH, BRANCHIND)."""

from __future__ import annotations

from dataclasses import dataclass

from flatline.models.pcode_ops._base import BranchOp


@dataclass(frozen=True)
class Branch(BranchOp):
    """Unconditional branch operation (BRANCH)."""

    ...


@dataclass(frozen=True)
class Cbranch(BranchOp):
    """Conditional branch operation (CBRANCH)."""

    ...


@dataclass(frozen=True)
class Branchind(BranchOp):
    """Indirect branch operation (BRANCHIND)."""

    ...


__all__ = [
    "Branch",
    "Branchind",
    "Cbranch",
]
