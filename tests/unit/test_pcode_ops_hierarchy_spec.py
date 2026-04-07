"""Tests for PcodeOpInfo category and leaf subclass hierarchy.

This module tests:
- All 72 leaf classes exist and are importable
- Liskov substitutability (issubclass(leaf, category) and issubclass(leaf, PcodeOpInfo))
- Frozen dataclass contract (mutation raises error)
- OPCODE_TO_CLASS dispatch table completeness
- No new fields on subclasses
"""

from __future__ import annotations

import dataclasses

import pytest

from flatline.models.enums import PcodeOpcode
from flatline.models.pcode_ops import (
    # Dispatch table
    OPCODE_TO_CLASS,
    ArithmeticOp,
    BitwiseOp,
    BoolAnd,
    BooleanOp,
    # Leaf classes - boolean
    BoolNegate,
    BoolOr,
    BoolXor,
    # Leaf classes - branch
    Branch,
    Branchind,
    BranchOp,
    # Leaf classes - call
    Call,
    Callind,
    CallOp,
    Callother,
    Cast,
    Cbranch,
    ComparisonOp,
    # Leaf classes - copy
    Copy,
    # Category classes
    CopyOp,
    Cpoolref,
    DataflowOp,
    Extract,
    FloatAbs,
    FloatAdd,
    FloatCeil,
    FloatDiv,
    FloatEqual,
    FloatFloat2float,
    FloatFloor,
    FloatInt2float,
    FloatLess,
    FloatLessequal,
    FloatMult,
    FloatNan,
    FloatNeg,
    FloatNotequal,
    FloatRound,
    FloatSqrt,
    FloatSub,
    FloatTrunc,
    HighLevelOp,
    Indirect,
    Insert,
    Int2comp,
    # Leaf classes - arithmetic
    IntAdd,
    IntAnd,
    IntCarry,
    IntDiv,
    # Leaf classes - comparison
    IntEqual,
    IntLeft,
    IntLess,
    IntLessequal,
    IntMult,
    # Leaf classes - bitwise
    IntNegate,
    IntNotequal,
    IntOr,
    IntRem,
    IntRight,
    IntSborrow,
    IntScarry,
    IntSdiv,
    IntSext,
    IntSless,
    IntSlessequal,
    IntSrem,
    IntSright,
    IntSub,
    IntXor,
    IntZext,
    # Leaf classes - memory
    Load,
    Lzcount,
    MemoryOp,
    # Leaf classes - dataflow
    Multiequal,
    New,
    Piece,
    Popcount,
    Ptradd,
    Ptrsub,
    Return,
    # Leaf classes - highlevel
    Segmentop,
    Store,
    Subpiece,
)
from flatline.models.types import PcodeOpInfo


class TestPcodeOpsHierarchy:
    """Tests for PcodeOpInfo subclass hierarchy."""

    def test_all_leaf_classes_importable(self) -> None:
        """All 72 leaf classes are importable from pcode_ops package."""
        # Arithmetic (18 classes)
        assert IntAdd is not None
        assert IntSub is not None
        assert Int2comp is not None
        assert IntCarry is not None
        assert IntScarry is not None
        assert IntSborrow is not None
        assert IntMult is not None
        assert IntDiv is not None
        assert IntSdiv is not None
        assert IntRem is not None
        assert IntSrem is not None
        assert FloatAdd is not None
        assert FloatSub is not None
        assert FloatMult is not None
        assert FloatDiv is not None
        assert FloatAbs is not None
        assert FloatSqrt is not None
        assert FloatNeg is not None

        # Bitwise (7 classes)
        assert IntNegate is not None
        assert IntAnd is not None
        assert IntOr is not None
        assert IntXor is not None
        assert IntLeft is not None
        assert IntRight is not None
        assert IntSright is not None

        # Boolean (4 classes)
        assert BoolNegate is not None
        assert BoolAnd is not None
        assert BoolOr is not None
        assert BoolXor is not None

        # Branch (3 classes)
        assert Branch is not None
        assert Cbranch is not None
        assert Branchind is not None

        # Call (4 classes)
        assert Call is not None
        assert Callind is not None
        assert Callother is not None
        assert Return is not None

        # Comparison (14 classes)
        assert IntEqual is not None
        assert IntNotequal is not None
        assert IntLess is not None
        assert IntSless is not None
        assert IntLessequal is not None
        assert IntSlessequal is not None
        assert FloatEqual is not None
        assert FloatNotequal is not None
        assert FloatLess is not None
        assert FloatLessequal is not None
        assert FloatNan is not None

        # Copy (16 classes)
        assert Copy is not None
        assert Subpiece is not None
        assert Piece is not None
        assert Popcount is not None
        assert Lzcount is not None
        assert IntZext is not None
        assert IntSext is not None
        assert FloatTrunc is not None
        assert FloatCeil is not None
        assert FloatFloor is not None
        assert FloatRound is not None
        assert FloatInt2float is not None
        assert FloatFloat2float is not None
        assert Cast is not None
        assert Cpoolref is not None
        assert New is not None

        # Dataflow (4 classes)
        assert Multiequal is not None
        assert Indirect is not None
        assert Ptradd is not None
        assert Ptrsub is not None

        # Highlevel (3 classes)
        assert Segmentop is not None
        assert Insert is not None
        assert Extract is not None

        # Memory (2 classes)
        assert Load is not None
        assert Store is not None

    def test_category_classes_importable(self) -> None:
        """All 10 category classes are importable."""
        assert CopyOp is not None
        assert MemoryOp is not None
        assert BranchOp is not None
        assert CallOp is not None
        assert ComparisonOp is not None
        assert ArithmeticOp is not None
        assert BitwiseOp is not None
        assert BooleanOp is not None
        assert DataflowOp is not None
        assert HighLevelOp is not None

    def test_liskov_substitutability_arithmetic(self) -> None:
        """Arithmetic leaf classes are subclasses of ArithmeticOp and PcodeOpInfo."""
        for cls in [
            IntAdd,
            IntSub,
            Int2comp,
            IntCarry,
            IntScarry,
            IntSborrow,
            IntMult,
            IntDiv,
            IntSdiv,
            IntRem,
            IntSrem,
            FloatAdd,
            FloatSub,
            FloatMult,
            FloatDiv,
            FloatAbs,
            FloatSqrt,
            FloatNeg,
        ]:
            assert issubclass(cls, ArithmeticOp), (
                f"{cls.__name__} is not a subclass of ArithmeticOp"
            )
            assert issubclass(cls, PcodeOpInfo), f"{cls.__name__} is not a subclass of PcodeOpInfo"

    def test_liskov_substitutability_bitwise(self) -> None:
        """Bitwise leaf classes are subclasses of BitwiseOp and PcodeOpInfo."""
        for cls in [IntNegate, IntAnd, IntOr, IntXor, IntLeft, IntRight, IntSright]:
            assert issubclass(cls, BitwiseOp), f"{cls.__name__} is not a subclass of BitwiseOp"
            assert issubclass(cls, PcodeOpInfo), f"{cls.__name__} is not a subclass of PcodeOpInfo"

    def test_liskov_substitutability_boolean(self) -> None:
        """Boolean leaf classes are subclasses of BooleanOp and PcodeOpInfo."""
        for cls in [BoolNegate, BoolAnd, BoolOr, BoolXor]:
            assert issubclass(cls, BooleanOp), f"{cls.__name__} is not a subclass of BooleanOp"
            assert issubclass(cls, PcodeOpInfo), f"{cls.__name__} is not a subclass of PcodeOpInfo"

    def test_liskov_substitutability_branch(self) -> None:
        """Branch leaf classes are subclasses of BranchOp and PcodeOpInfo."""
        for cls in [Branch, Cbranch, Branchind]:
            assert issubclass(cls, BranchOp), f"{cls.__name__} is not a subclass of BranchOp"
            assert issubclass(cls, PcodeOpInfo), f"{cls.__name__} is not a subclass of PcodeOpInfo"

    def test_liskov_substitutability_call(self) -> None:
        """Call leaf classes are subclasses of CallOp and PcodeOpInfo."""
        for cls in [Call, Callind, Callother, Return]:
            assert issubclass(cls, CallOp), f"{cls.__name__} is not a subclass of CallOp"
            assert issubclass(cls, PcodeOpInfo), f"{cls.__name__} is not a subclass of PcodeOpInfo"

    def test_liskov_substitutability_comparison(self) -> None:
        """Comparison leaf classes are subclasses of ComparisonOp and PcodeOpInfo."""
        for cls in [
            IntEqual,
            IntNotequal,
            IntLess,
            IntSless,
            IntLessequal,
            IntSlessequal,
            FloatEqual,
            FloatNotequal,
            FloatLess,
            FloatLessequal,
            FloatNan,
        ]:
            assert issubclass(cls, ComparisonOp), (
                f"{cls.__name__} is not a subclass of ComparisonOp"
            )
            assert issubclass(cls, PcodeOpInfo), f"{cls.__name__} is not a subclass of PcodeOpInfo"

    def test_liskov_substitutability_copy(self) -> None:
        """Copy leaf classes are subclasses of CopyOp and PcodeOpInfo."""
        for cls in [
            Copy,
            Subpiece,
            Piece,
            Popcount,
            Lzcount,
            IntZext,
            IntSext,
            FloatTrunc,
            FloatCeil,
            FloatFloor,
            FloatRound,
            FloatInt2float,
            FloatFloat2float,
            Cast,
            Cpoolref,
            New,
        ]:
            assert issubclass(cls, CopyOp), f"{cls.__name__} is not a subclass of CopyOp"
            assert issubclass(cls, PcodeOpInfo), f"{cls.__name__} is not a subclass of PcodeOpInfo"

    def test_liskov_substitutability_dataflow(self) -> None:
        """Dataflow leaf classes are subclasses of DataflowOp and PcodeOpInfo."""
        for cls in [Multiequal, Indirect, Ptradd, Ptrsub]:
            assert issubclass(cls, DataflowOp), f"{cls.__name__} is not a subclass of DataflowOp"
            assert issubclass(cls, PcodeOpInfo), f"{cls.__name__} is not a subclass of PcodeOpInfo"

    def test_liskov_substitutability_highlevel(self) -> None:
        """Highlevel leaf classes are subclasses of HighLevelOp and PcodeOpInfo."""
        for cls in [Segmentop, Insert, Extract]:
            assert issubclass(cls, HighLevelOp), f"{cls.__name__} is not a subclass of HighLevelOp"
            assert issubclass(cls, PcodeOpInfo), f"{cls.__name__} is not a subclass of PcodeOpInfo"

    def test_liskov_substitutability_memory(self) -> None:
        """Memory leaf classes are subclasses of MemoryOp and PcodeOpInfo."""
        for cls in [Load, Store]:
            assert issubclass(cls, MemoryOp), f"{cls.__name__} is not a subclass of MemoryOp"
            assert issubclass(cls, PcodeOpInfo), f"{cls.__name__} is not a subclass of PcodeOpInfo"

    def test_frozen_dataclass(self) -> None:
        """Leaf classes are frozen dataclasses (mutation raises error)."""
        op = IntAdd(
            id=0,
            opcode=PcodeOpcode.INT_ADD,
            instruction_address=0x1000,
            sequence_time=1,
            sequence_order=1,
            input_varnode_ids=[0, 1],
            output_varnode_id=2,
        )
        with pytest.raises(AttributeError):
            op.opcode = PcodeOpcode.COPY  # type: ignore[misc]

    def test_no_new_fields(self) -> None:
        """Leaf classes have no new stored fields beyond PcodeOpInfo."""
        base_fields = {f.name for f in dataclasses.fields(PcodeOpInfo)}
        for cls in [
            IntAdd,
            Load,
            Branch,
            Call,
            IntEqual,
            IntNegate,
            BoolAnd,
            Multiequal,
            Segmentop,
            Copy,
        ]:
            leaf_fields = {f.name for f in dataclasses.fields(cls)}
            assert leaf_fields == base_fields, (
                f"{cls.__name__} has extra fields: {leaf_fields - base_fields}"
            )

    def test_dispatch_table_completeness(self) -> None:
        """OPCODE_TO_CLASS has exactly 72 entries, one for each PcodeOpcode."""
        assert len(OPCODE_TO_CLASS) == 72, f"Expected 72 entries, got {len(OPCODE_TO_CLASS)}"

    def test_dispatch_table_covers_all_opcodes(self) -> None:
        """Every PcodeOpcode member is in OPCODE_TO_CLASS."""
        for opcode in PcodeOpcode:
            assert opcode.value in OPCODE_TO_CLASS, f"Missing opcode: {opcode.value}"

    def test_dispatch_table_values_are_leaf_classes(self) -> None:
        """All values in OPCODE_TO_CLASS are leaf subclasses of PcodeOpInfo."""
        for opcode_str, cls in OPCODE_TO_CLASS.items():
            assert issubclass(cls, PcodeOpInfo), f"{opcode_str} maps to non-PcodeOpInfo: {cls}"
            # Verify it's a leaf (not a category)
            assert cls not in [
                CopyOp,
                MemoryOp,
                BranchOp,
                CallOp,
                ComparisonOp,
                ArithmeticOp,
                BitwiseOp,
                BooleanOp,
                DataflowOp,
                HighLevelOp,
            ], f"{opcode_str} maps to category class: {cls}"

    def test_instance_construction(self) -> None:
        """Leaf class instances can be constructed with PcodeOpInfo fields."""
        op = IntAdd(
            id=0,
            opcode=PcodeOpcode.INT_ADD,
            instruction_address=0x1000,
            sequence_time=1,
            sequence_order=1,
            input_varnode_ids=[0, 1],
            output_varnode_id=2,
        )
        assert isinstance(op, IntAdd)
        assert isinstance(op, ArithmeticOp)
        assert isinstance(op, PcodeOpInfo)
        assert op.opcode == PcodeOpcode.INT_ADD
        assert op.id == 0
        assert op.instruction_address == 0x1000

    def test_instance_isinstance_checks(self) -> None:
        """isinstance() works correctly for leaf, category, and base checks."""
        op = Load(
            id=1,
            opcode=PcodeOpcode.LOAD,
            instruction_address=0x2000,
            sequence_time=2,
            sequence_order=1,
            input_varnode_ids=[0],
            output_varnode_id=1,
        )
        assert isinstance(op, Load)
        assert isinstance(op, MemoryOp)
        assert isinstance(op, PcodeOpInfo)
        assert not isinstance(op, ArithmeticOp)
        assert not isinstance(op, IntAdd)

    def test_dispatch_table_sample_mappings(self) -> None:
        """Sample opcode mappings are correct."""
        assert OPCODE_TO_CLASS["INT_ADD"] is IntAdd
        assert OPCODE_TO_CLASS["LOAD"] is Load
        assert OPCODE_TO_CLASS["BRANCH"] is Branch
        assert OPCODE_TO_CLASS["CALL"] is Call
        assert OPCODE_TO_CLASS["INT_EQUAL"] is IntEqual
        assert OPCODE_TO_CLASS["INT_NEGATE"] is IntNegate
        assert OPCODE_TO_CLASS["BOOL_AND"] is BoolAnd
        assert OPCODE_TO_CLASS["MULTIEQUAL"] is Multiequal
        assert OPCODE_TO_CLASS["SEGMENTOP"] is Segmentop
        assert OPCODE_TO_CLASS["COPY"] is Copy
