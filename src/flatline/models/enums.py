"""StrEnums for pcode opcodes and varnode spaces.

These enums provide type-safe string constants matching Ghidra's p-code
representation. They are designed for backward compatibility with existing
string-based APIs.
"""

from __future__ import annotations

from enum import StrEnum


class PcodeOpcode(StrEnum):
    """P-code operation codes from Ghidra's decompiler.

    These 72 opcodes represent the active p-code operations used by Ghidra's
    decompiler. The values match Ghidra's ``CPUI_*`` constants from
    ``opcodes.hh``, with the ``CPUI_`` prefix stripped for member names.

    Reference:
        ``third_party/ghidra/Ghidra/Features/Decompiler/src/decompile/cpp/opcodes.hh``

    Note:
        ``CPUI_MAX`` (value 74) is excluded as it is a sentinel value marking
        the end of the opcode range, not an actual operation.
    """

    # Control flow
    COPY = "COPY"
    LOAD = "LOAD"
    STORE = "STORE"
    BRANCH = "BRANCH"
    CBRANCH = "CBRANCH"
    BRANCHIND = "BRANCHIND"
    CALL = "CALL"
    CALLIND = "CALLIND"
    CALLOTHER = "CALLOTHER"
    RETURN = "RETURN"

    # Integer comparison
    INT_EQUAL = "INT_EQUAL"
    INT_NOTEQUAL = "INT_NOTEQUAL"
    INT_SLESS = "INT_SLESS"
    INT_SLESSEQUAL = "INT_SLESSEQUAL"
    INT_LESS = "INT_LESS"
    INT_LESSEQUAL = "INT_LESSEQUAL"

    # Integer extension
    INT_ZEXT = "INT_ZEXT"
    INT_SEXT = "INT_SEXT"

    # Integer arithmetic
    INT_ADD = "INT_ADD"
    INT_SUB = "INT_SUB"
    INT_CARRY = "INT_CARRY"
    INT_SCARRY = "INT_SCARRY"
    INT_SBORROW = "INT_SBORROW"
    INT_2COMP = "INT_2COMP"
    INT_NEGATE = "INT_NEGATE"

    # Integer bitwise
    INT_XOR = "INT_XOR"
    INT_AND = "INT_AND"
    INT_OR = "INT_OR"

    # Integer shift
    INT_LEFT = "INT_LEFT"
    INT_RIGHT = "INT_RIGHT"
    INT_SRIGHT = "INT_SRIGHT"

    # Integer multiplication/division
    INT_MULT = "INT_MULT"
    INT_DIV = "INT_DIV"
    INT_SDIV = "INT_SDIV"
    INT_REM = "INT_REM"
    INT_SREM = "INT_SREM"

    # Boolean operations
    BOOL_NEGATE = "BOOL_NEGATE"
    BOOL_XOR = "BOOL_XOR"
    BOOL_AND = "BOOL_AND"
    BOOL_OR = "BOOL_OR"

    # Floating-point comparison
    FLOAT_EQUAL = "FLOAT_EQUAL"
    FLOAT_NOTEQUAL = "FLOAT_NOTEQUAL"
    FLOAT_LESS = "FLOAT_LESS"
    FLOAT_LESSEQUAL = "FLOAT_LESSEQUAL"
    FLOAT_NAN = "FLOAT_NAN"

    # Floating-point arithmetic
    FLOAT_ADD = "FLOAT_ADD"
    FLOAT_DIV = "FLOAT_DIV"
    FLOAT_MULT = "FLOAT_MULT"
    FLOAT_SUB = "FLOAT_SUB"
    FLOAT_NEG = "FLOAT_NEG"
    FLOAT_ABS = "FLOAT_ABS"
    FLOAT_SQRT = "FLOAT_SQRT"

    # Floating-point conversion
    FLOAT_INT2FLOAT = "FLOAT_INT2FLOAT"
    FLOAT_FLOAT2FLOAT = "FLOAT_FLOAT2FLOAT"
    FLOAT_TRUNC = "FLOAT_TRUNC"
    FLOAT_CEIL = "FLOAT_CEIL"
    FLOAT_FLOOR = "FLOAT_FLOOR"
    FLOAT_ROUND = "FLOAT_ROUND"

    # Data-flow operations
    MULTIEQUAL = "MULTIEQUAL"
    INDIRECT = "INDIRECT"
    PIECE = "PIECE"
    SUBPIECE = "SUBPIECE"

    # Pointer operations
    CAST = "CAST"
    PTRADD = "PTRADD"
    PTRSUB = "PTRSUB"
    SEGMENTOP = "SEGMENTOP"
    CPOOLREF = "CPOOLREF"
    NEW = "NEW"

    # Bit operations
    INSERT = "INSERT"
    EXTRACT = "EXTRACT"
    POPCOUNT = "POPCOUNT"
    LZCOUNT = "LZCOUNT"


class VarnodeSpace(StrEnum):
    """Address space names for varnodes in the p-code graph.

    These spaces determine the interpretation of a varnode's ``offset`` field:

    - ``CONST``: ``offset`` is the literal constant value.
    - ``REGISTER``: ``offset`` is the register number in the processor spec.
    - ``UNIQUE``: ``offset`` is an internal temporary allocation ID (opaque).
    - ``RAM``: ``offset`` is the virtual memory address.
    - ``FSPEC``: Call-spec reference; use ``call_site_index`` instead of ``offset``.
    - ``IOP``: Internal op pointer; use ``target_op_id`` instead of ``offset``.
    - ``JOIN``: Split/merged variable storage (opaque).
    - ``STACK``: ``offset`` is the stack-frame offset.
    - ``PROCESSOR_CONTEXT``: Processor context register space.
    """

    CONST = "const"
    REGISTER = "register"
    UNIQUE = "unique"
    RAM = "ram"
    FSPEC = "fspec"
    IOP = "iop"
    JOIN = "join"
    STACK = "stack"
    PROCESSOR_CONTEXT = "processor_context"


__all__ = ["PcodeOpcode", "VarnodeSpace"]
