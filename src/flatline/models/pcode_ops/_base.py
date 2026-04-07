"""Category base classes for PcodeOpInfo subclass hierarchy.

This module defines 10 category subclasses that group the 72 pcode opcodes
into semantic categories. Each category inherits from PcodeOpInfo and adds
no new stored fields, preserving the frozen dataclass contract.

Categories:
- CopyOp: Data movement and conversion (COPY, SUBPIECE, PIECE, etc.)
- MemoryOp: Memory operations (LOAD, STORE)
- BranchOp: Control flow operations (BRANCH, CBRANCH, BRANCHIND)
- CallOp: Function call operations (CALL, CALLIND, CALLOTHER, RETURN)
- ComparisonOp: Comparison operations (INT_EQUAL, FLOAT_LESS, etc.)
- ArithmeticOp: Arithmetic operations (INT_ADD, FLOAT_MULT, etc.)
- BitwiseOp: Bitwise operations (INT_AND, INT_OR, INT_XOR, etc.)
- BooleanOp: Boolean operations (BOOL_AND, BOOL_OR, etc.)
- DataflowOp: Data flow operations (MULTIEQUAL, INDIRECT, etc.)
- HighLevelOp: High-level operations (SEGMENTOP, INSERT, EXTRACT)
"""

from __future__ import annotations

from dataclasses import dataclass

from flatline.models.types import PcodeOpInfo


@dataclass(frozen=True)
class CopyOp(PcodeOpInfo):
    """Data movement and conversion operations.

    Includes COPY, SUBPIECE, PIECE, POPCOUNT, LZCOUNT, INT_ZEXT, INT_SEXT,
    FLOAT_TRUNC, FLOAT_CEIL, FLOAT_FLOOR, FLOAT_ROUND, FLOAT_INT2FLOAT,
    FLOAT_FLOAT2FLOAT, CAST, CPOOLREF, NEW.
    """

    ...


@dataclass(frozen=True)
class MemoryOp(PcodeOpInfo):
    """Memory load and store operations.

    Includes LOAD, STORE.
    """

    ...


@dataclass(frozen=True)
class BranchOp(PcodeOpInfo):
    """Control flow branch operations.

    Includes BRANCH, CBRANCH, BRANCHIND.
    """

    ...


@dataclass(frozen=True)
class CallOp(PcodeOpInfo):
    """Function call and return operations.

    Includes CALL, CALLIND, CALLOTHER, RETURN.
    """

    ...


@dataclass(frozen=True)
class ComparisonOp(PcodeOpInfo):
    """Comparison operations for integers and floats.

    Includes INT_EQUAL, INT_NOTEQUAL, INT_LESS, INT_SLESS, INT_LESSEQUAL,
    INT_SLESSEQUAL, INT_CARRY, INT_SCARRY, INT_SBORROW, FLOAT_EQUAL,
    FLOAT_NOTEQUAL, FLOAT_LESS, FLOAT_LESSEQUAL, FLOAT_NAN.
    """

    ...


@dataclass(frozen=True)
class ArithmeticOp(PcodeOpInfo):
    """Arithmetic operations for integers and floats.

    Includes INT_ADD, INT_SUB, INT_2COMP, INT_CARRY, INT_SCARRY, INT_SBORROW,
    INT_MULT, INT_DIV, INT_SDIV, INT_REM, INT_SREM, FLOAT_ADD, FLOAT_SUB,
    FLOAT_MULT, FLOAT_DIV, FLOAT_ABS, FLOAT_SQRT, FLOAT_NEG.
    """

    ...


@dataclass(frozen=True)
class BitwiseOp(PcodeOpInfo):
    """Bitwise operations on integers.

    Includes INT_NEGATE, INT_AND, INT_OR, INT_XOR, INT_LEFT, INT_RIGHT,
    INT_SRIGHT.
    """

    ...


@dataclass(frozen=True)
class BooleanOp(PcodeOpInfo):
    """Boolean logic operations.

    Includes BOOL_NEGATE, BOOL_AND, BOOL_OR, BOOL_XOR.
    """

    ...


@dataclass(frozen=True)
class DataflowOp(PcodeOpInfo):
    """Data flow and pointer operations.

    Includes MULTIEQUAL, INDIRECT, PTRADD, PTRSUB.
    """

    ...


@dataclass(frozen=True)
class HighLevelOp(PcodeOpInfo):
    """High-level compound operations.

    Includes SEGMENTOP, INSERT, EXTRACT.
    """

    ...


__all__ = [
    "ArithmeticOp",
    "BitwiseOp",
    "BooleanOp",
    "BranchOp",
    "CallOp",
    "ComparisonOp",
    "CopyOp",
    "DataflowOp",
    "HighLevelOp",
    "MemoryOp",
]
