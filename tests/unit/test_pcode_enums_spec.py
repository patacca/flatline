"""Unit tests for PcodeOpcode and VarnodeSpace StrEnums.

These tests verify:
- Correct member count matching Ghidra's active opcodes
- StrEnum backward compatibility with string APIs
- Construction from string values
- Membership testing
"""

from __future__ import annotations

import pytest

from flatline.models.enums import PcodeOpcode, VarnodeSpace


class TestPcodeOpcode:
    """Tests for PcodeOpcode StrEnum."""

    def test_member_count(self) -> None:
        """PcodeOpcode has exactly 72 members (active Ghidra opcodes)."""
        assert len(PcodeOpcode) == 72

    def test_strenum_backward_compat(self) -> None:
        """StrEnum members compare equal to their string values."""
        assert PcodeOpcode.INT_ADD == "INT_ADD"
        assert PcodeOpcode.CBRANCH == "CBRANCH"
        assert PcodeOpcode.COPY == "COPY"

    def test_construction_from_string(self) -> None:
        """PcodeOpcode can be constructed from string values."""
        assert PcodeOpcode("INT_ADD") is PcodeOpcode.INT_ADD
        assert PcodeOpcode("CBRANCH") is PcodeOpcode.CBRANCH
        assert PcodeOpcode("COPY") is PcodeOpcode.COPY

    def test_membership(self) -> None:
        """String values are in __members__ dict."""
        assert "INT_ADD" in PcodeOpcode.__members__
        assert "CBRANCH" in PcodeOpcode.__members__
        assert "COPY" in PcodeOpcode.__members__

    def test_unknown_opcode_raises(self) -> None:
        """Unknown opcode strings raise ValueError."""
        with pytest.raises(ValueError, match="UNKNOWN_OPCODE"):
            PcodeOpcode("UNKNOWN_OPCODE")

    def test_control_flow_opcodes(self) -> None:
        """Control flow opcodes are present."""
        assert PcodeOpcode.COPY is not None
        assert PcodeOpcode.LOAD is not None
        assert PcodeOpcode.STORE is not None
        assert PcodeOpcode.BRANCH is not None
        assert PcodeOpcode.CBRANCH is not None
        assert PcodeOpcode.BRANCHIND is not None
        assert PcodeOpcode.CALL is not None
        assert PcodeOpcode.CALLIND is not None
        assert PcodeOpcode.CALLOTHER is not None
        assert PcodeOpcode.RETURN is not None

    def test_integer_opcodes(self) -> None:
        """Integer operation opcodes are present."""
        assert PcodeOpcode.INT_ADD is not None
        assert PcodeOpcode.INT_SUB is not None
        assert PcodeOpcode.INT_MULT is not None
        assert PcodeOpcode.INT_DIV is not None
        assert PcodeOpcode.INT_SDIV is not None
        assert PcodeOpcode.INT_REM is not None
        assert PcodeOpcode.INT_SREM is not None

    def test_float_opcodes(self) -> None:
        """Floating-point operation opcodes are present."""
        assert PcodeOpcode.FLOAT_ADD is not None
        assert PcodeOpcode.FLOAT_SUB is not None
        assert PcodeOpcode.FLOAT_MULT is not None
        assert PcodeOpcode.FLOAT_DIV is not None
        assert PcodeOpcode.FLOAT_NEG is not None

    def test_dataflow_opcodes(self) -> None:
        """Data-flow operation opcodes are present."""
        assert PcodeOpcode.MULTIEQUAL is not None
        assert PcodeOpcode.INDIRECT is not None
        assert PcodeOpcode.PIECE is not None
        assert PcodeOpcode.SUBPIECE is not None

    def test_bit_opcodes(self) -> None:
        """Bit operation opcodes are present."""
        assert PcodeOpcode.INSERT is not None
        assert PcodeOpcode.EXTRACT is not None
        assert PcodeOpcode.POPCOUNT is not None
        assert PcodeOpcode.LZCOUNT is not None


class TestVarnodeSpace:
    """Tests for VarnodeSpace StrEnum."""

    def test_member_count(self) -> None:
        """VarnodeSpace has exactly 9 members."""
        assert len(VarnodeSpace) == 9

    def test_strenum_backward_compat(self) -> None:
        """StrEnum members compare equal to their string values."""
        assert VarnodeSpace.CONST == "const"
        assert VarnodeSpace.REGISTER == "register"
        assert VarnodeSpace.RAM == "ram"

    def test_construction_from_string(self) -> None:
        """VarnodeSpace can be constructed from string values."""
        assert VarnodeSpace("const") is VarnodeSpace.CONST
        assert VarnodeSpace("register") is VarnodeSpace.REGISTER
        assert VarnodeSpace("ram") is VarnodeSpace.RAM

    def test_membership(self) -> None:
        """String values are in __members__ dict."""
        assert "CONST" in VarnodeSpace.__members__
        assert "REGISTER" in VarnodeSpace.__members__
        assert "UNIQUE" in VarnodeSpace.__members__
        assert "RAM" in VarnodeSpace.__members__
        assert "FSPEC" in VarnodeSpace.__members__
        assert "IOP" in VarnodeSpace.__members__
        assert "JOIN" in VarnodeSpace.__members__
        assert "STACK" in VarnodeSpace.__members__

    def test_unknown_space_raises(self) -> None:
        """Unknown space strings raise ValueError."""
        with pytest.raises(ValueError, match="unknown"):
            VarnodeSpace("unknown")

    def test_all_spaces_present(self) -> None:
        """All 9 address spaces are present."""
        expected = {
            "CONST",
            "REGISTER",
            "UNIQUE",
            "RAM",
            "FSPEC",
            "IOP",
            "JOIN",
            "STACK",
            "PROCESSOR_CONTEXT",
        }
        actual = {member.name for member in VarnodeSpace}
        assert actual == expected


class TestPcodeOpInfoRetyped:
    """Tests for PcodeOpInfo.opcode typed as PcodeOpcode."""

    def test_opcode_is_pcodeopcode_instance(self) -> None:
        """PcodeOpInfo.opcode returns PcodeOpcode instance."""
        from flatline.models.types import PcodeOpInfo

        op = PcodeOpInfo(
            id=0,
            opcode="INT_ADD",
            instruction_address=0x1000,
            sequence_time=0,
            sequence_order=0,
            input_varnode_ids=[],
        )
        assert isinstance(op.opcode, PcodeOpcode)
        assert op.opcode is PcodeOpcode.INT_ADD

    def test_opcode_backward_compat_string_comparison(self) -> None:
        """StrEnum backward compat: op.opcode == "INT_ADD" still works."""
        from flatline.models.types import PcodeOpInfo

        op = PcodeOpInfo(
            id=0,
            opcode="INT_ADD",
            instruction_address=0x1000,
            sequence_time=0,
            sequence_order=0,
            input_varnode_ids=[],
        )
        assert op.opcode == "INT_ADD"
        assert op.opcode == PcodeOpcode.INT_ADD

    def test_opcode_construction_from_string(self) -> None:
        """PcodeOpInfo can be constructed with raw string opcode."""
        from flatline.models.types import PcodeOpInfo

        op = PcodeOpInfo(
            id=0,
            opcode="INT_ADD",
            instruction_address=0x1000,
            sequence_time=0,
            sequence_order=0,
            input_varnode_ids=[],
        )
        assert op.opcode == PcodeOpcode.INT_ADD

    def test_opcode_construction_from_enum(self) -> None:
        """PcodeOpInfo can be constructed with PcodeOpcode enum."""
        from flatline.models.types import PcodeOpInfo

        op = PcodeOpInfo(
            id=0,
            opcode=PcodeOpcode.INT_ADD,
            instruction_address=0x1000,
            sequence_time=0,
            sequence_order=0,
            input_varnode_ids=[],
        )
        assert op.opcode is PcodeOpcode.INT_ADD


class TestVarnodeInfoRetyped:
    """Tests for VarnodeInfo.space typed as VarnodeSpace."""

    def test_space_is_varnodespace_instance(self) -> None:
        """VarnodeInfo.space returns VarnodeSpace instance."""
        from flatline.models.types import VarnodeFlags, VarnodeInfo

        vn = VarnodeInfo(
            id=0,
            space="register",
            offset=0,
            size=8,
            flags=VarnodeFlags(
                is_constant=False,
                is_input=True,
                is_free=False,
                is_implied=False,
                is_explicit=False,
                is_read_only=False,
                is_persist=False,
                is_addr_tied=False,
            ),
            defining_op_id=None,
            use_op_ids=[],
        )
        assert isinstance(vn.space, VarnodeSpace)
        assert vn.space is VarnodeSpace.REGISTER

    def test_space_backward_compat_string_comparison(self) -> None:
        """StrEnum backward compat: vn.space == "register" still works."""
        from flatline.models.types import VarnodeFlags, VarnodeInfo

        vn = VarnodeInfo(
            id=0,
            space="register",
            offset=0,
            size=8,
            flags=VarnodeFlags(
                is_constant=False,
                is_input=True,
                is_free=False,
                is_implied=False,
                is_explicit=False,
                is_read_only=False,
                is_persist=False,
                is_addr_tied=False,
            ),
            defining_op_id=None,
            use_op_ids=[],
        )
        assert vn.space == "register"
        assert vn.space == VarnodeSpace.REGISTER

    def test_space_construction_from_string(self) -> None:
        """VarnodeInfo can be constructed with raw string space."""
        from flatline.models.types import VarnodeFlags, VarnodeInfo

        vn = VarnodeInfo(
            id=0,
            space="ram",
            offset=0x1000,
            size=4,
            flags=VarnodeFlags(
                is_constant=False,
                is_input=False,
                is_free=False,
                is_implied=False,
                is_explicit=False,
                is_read_only=False,
                is_persist=False,
                is_addr_tied=False,
            ),
            defining_op_id=None,
            use_op_ids=[],
        )
        assert vn.space == VarnodeSpace.RAM

    def test_space_construction_from_enum(self) -> None:
        """VarnodeInfo can be constructed with VarnodeSpace enum."""
        from flatline.models.types import VarnodeFlags, VarnodeInfo

        vn = VarnodeInfo(
            id=0,
            space=VarnodeSpace.STACK,
            offset=-8,
            size=8,
            flags=VarnodeFlags(
                is_constant=False,
                is_input=False,
                is_free=False,
                is_implied=False,
                is_explicit=False,
                is_read_only=False,
                is_persist=False,
                is_addr_tied=False,
            ),
            defining_op_id=None,
            use_op_ids=[],
        )
        assert vn.space is VarnodeSpace.STACK
