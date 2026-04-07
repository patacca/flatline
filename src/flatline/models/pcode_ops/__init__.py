"""PcodeOpInfo subclass hierarchy for typed pcode operations.

This package provides a typed hierarchy for pcode operations:
- 10 category classes (CopyOp, MemoryOp, BranchOp, etc.)
- 72 leaf classes (IntAdd, Load, Branch, etc.)
- OPCODE_TO_CLASS dispatch table for opcode → class lookup

Usage:
    from flatline.models.pcode_ops import IntAdd, ArithmeticOp, OPCODE_TO_CLASS

    # Category matching
    if isinstance(op, ArithmeticOp):
        ...

    # Leaf matching
    if isinstance(op, IntAdd):
        ...

    # Dispatch table
    cls = OPCODE_TO_CLASS["INT_ADD"]
"""

from __future__ import annotations

# Category classes
from flatline.models.pcode_ops._base import (
    ArithmeticOp,
    BitwiseOp,
    BooleanOp,
    BranchOp,
    CallOp,
    ComparisonOp,
    CopyOp,
    DataflowOp,
    HighLevelOp,
    MemoryOp,
)

# Leaf classes - arithmetic
from flatline.models.pcode_ops.arithmetic import (
    FloatAbs,
    FloatAdd,
    FloatDiv,
    FloatMult,
    FloatNeg,
    FloatSqrt,
    FloatSub,
    Int2comp,
    IntAdd,
    IntCarry,
    IntDiv,
    IntMult,
    IntRem,
    IntSborrow,
    IntScarry,
    IntSdiv,
    IntSrem,
    IntSub,
)

# Leaf classes - bitwise
from flatline.models.pcode_ops.bitwise import (
    IntAnd,
    IntLeft,
    IntNegate,
    IntOr,
    IntRight,
    IntSright,
    IntXor,
)

# Leaf classes - boolean
from flatline.models.pcode_ops.boolean import (
    BoolAnd,
    BoolNegate,
    BoolOr,
    BoolXor,
)

# Leaf classes - branch
from flatline.models.pcode_ops.branch import (
    Branch,
    Branchind,
    Cbranch,
)

# Leaf classes - call
from flatline.models.pcode_ops.call import (
    Call,
    Callind,
    Callother,
    Return,
)

# Leaf classes - comparison
from flatline.models.pcode_ops.comparison import (
    FloatEqual,
    FloatLess,
    FloatLessequal,
    FloatNan,
    FloatNotequal,
    IntEqual,
    IntLess,
    IntLessequal,
    IntNotequal,
    IntSless,
    IntSlessequal,
)

# Leaf classes - copy
from flatline.models.pcode_ops.copy import (
    Cast,
    Copy,
    Cpoolref,
    FloatCeil,
    FloatFloat2float,
    FloatFloor,
    FloatInt2float,
    FloatRound,
    FloatTrunc,
    IntSext,
    IntZext,
    Lzcount,
    New,
    Piece,
    Popcount,
    Subpiece,
)

# Leaf classes - dataflow
from flatline.models.pcode_ops.dataflow import (
    Indirect,
    Multiequal,
    Ptradd,
    Ptrsub,
)

# Leaf classes - highlevel
from flatline.models.pcode_ops.highlevel import (
    Extract,
    Insert,
    Segmentop,
)

# Leaf classes - memory
from flatline.models.pcode_ops.memory import (
    Load,
    Store,
)

# Build dispatch table: opcode string → leaf class
OPCODE_TO_CLASS: dict[str, type] = {
    # Control flow
    "COPY": Copy,
    "LOAD": Load,
    "STORE": Store,
    "BRANCH": Branch,
    "CBRANCH": Cbranch,
    "BRANCHIND": Branchind,
    "CALL": Call,
    "CALLIND": Callind,
    "CALLOTHER": Callother,
    "RETURN": Return,
    # Integer comparison
    "INT_EQUAL": IntEqual,
    "INT_NOTEQUAL": IntNotequal,
    "INT_SLESS": IntSless,
    "INT_SLESSEQUAL": IntSlessequal,
    "INT_LESS": IntLess,
    "INT_LESSEQUAL": IntLessequal,
    # Integer extension
    "INT_ZEXT": IntZext,
    "INT_SEXT": IntSext,
    # Integer arithmetic
    "INT_ADD": IntAdd,
    "INT_SUB": IntSub,
    "INT_CARRY": IntCarry,
    "INT_SCARRY": IntScarry,
    "INT_SBORROW": IntSborrow,
    "INT_2COMP": Int2comp,
    "INT_NEGATE": IntNegate,
    # Integer bitwise
    "INT_XOR": IntXor,
    "INT_AND": IntAnd,
    "INT_OR": IntOr,
    # Integer shift
    "INT_LEFT": IntLeft,
    "INT_RIGHT": IntRight,
    "INT_SRIGHT": IntSright,
    # Integer multiplication/division
    "INT_MULT": IntMult,
    "INT_DIV": IntDiv,
    "INT_SDIV": IntSdiv,
    "INT_REM": IntRem,
    "INT_SREM": IntSrem,
    # Boolean operations
    "BOOL_NEGATE": BoolNegate,
    "BOOL_XOR": BoolXor,
    "BOOL_AND": BoolAnd,
    "BOOL_OR": BoolOr,
    # Floating-point comparison
    "FLOAT_EQUAL": FloatEqual,
    "FLOAT_NOTEQUAL": FloatNotequal,
    "FLOAT_LESS": FloatLess,
    "FLOAT_LESSEQUAL": FloatLessequal,
    "FLOAT_NAN": FloatNan,
    # Floating-point arithmetic
    "FLOAT_ADD": FloatAdd,
    "FLOAT_DIV": FloatDiv,
    "FLOAT_MULT": FloatMult,
    "FLOAT_SUB": FloatSub,
    "FLOAT_NEG": FloatNeg,
    "FLOAT_ABS": FloatAbs,
    "FLOAT_SQRT": FloatSqrt,
    # Floating-point conversion
    "FLOAT_INT2FLOAT": FloatInt2float,
    "FLOAT_FLOAT2FLOAT": FloatFloat2float,
    "FLOAT_TRUNC": FloatTrunc,
    "FLOAT_CEIL": FloatCeil,
    "FLOAT_FLOOR": FloatFloor,
    "FLOAT_ROUND": FloatRound,
    # Data-flow operations
    "MULTIEQUAL": Multiequal,
    "INDIRECT": Indirect,
    "PIECE": Piece,
    "SUBPIECE": Subpiece,
    # Pointer operations
    "CAST": Cast,
    "PTRADD": Ptradd,
    "PTRSUB": Ptrsub,
    "SEGMENTOP": Segmentop,
    "CPOOLREF": Cpoolref,
    "NEW": New,
    # Bit operations
    "INSERT": Insert,
    "EXTRACT": Extract,
    "POPCOUNT": Popcount,
    "LZCOUNT": Lzcount,
}

__all__ = [
    "OPCODE_TO_CLASS",
    "ArithmeticOp",
    "BitwiseOp",
    "BoolAnd",
    "BoolNegate",
    "BoolOr",
    "BoolXor",
    "BooleanOp",
    "Branch",
    "BranchOp",
    "Branchind",
    "Call",
    "CallOp",
    "Callind",
    "Callother",
    "Cbranch",
    "ComparisonOp",
    "Copy",
    "CopyOp",
    "Cpoolref",
    "DataflowOp",
    "Extract",
    "FloatAbs",
    "FloatAdd",
    "FloatCeil",
    "FloatDiv",
    "FloatEqual",
    "FloatFloat2float",
    "FloatFloor",
    "FloatInt2float",
    "FloatLess",
    "FloatLessequal",
    "FloatMult",
    "FloatNan",
    "FloatNeg",
    "FloatNotequal",
    "FloatRound",
    "FloatSqrt",
    "FloatSub",
    "FloatTrunc",
    "HighLevelOp",
    "Indirect",
    "Insert",
    "Int2comp",
    "IntAdd",
    "IntAnd",
    "IntCarry",
    "IntDiv",
    "IntEqual",
    "IntLeft",
    "IntLess",
    "IntLessequal",
    "IntMult",
    "IntNegate",
    "IntNotequal",
    "IntOr",
    "IntRem",
    "IntRight",
    "IntSborrow",
    "IntScarry",
    "IntSdiv",
    "IntSext",
    "IntSless",
    "IntSlessequal",
    "IntSrem",
    "IntSright",
    "IntSub",
    "IntXor",
    "IntZext",
    "Load",
    "Lzcount",
    "MemoryOp",
    "Multiequal",
    "New",
    "Piece",
    "Popcount",
    "Ptradd",
    "Ptrsub",
    "Return",
    "Segmentop",
    "Store",
    "Subpiece",
]
