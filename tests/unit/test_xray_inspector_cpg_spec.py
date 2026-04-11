from __future__ import annotations

import pytest

from flatline.models.pcode_ops.branch import Cbranch
from flatline.models.pcode_ops import IntAdd
from flatline.models.varnodes import FspecVarnode, IopVarnode, RegisterVarnode
from flatline.models.types import VarnodeFlags
from flatline.xray import _inspector  # pyright: ignore[reportMissingImports]

pytestmark = pytest.mark.unit


def _make_varnode_flags() -> VarnodeFlags:
    """Create default varnode flags for testing."""
    return VarnodeFlags(
        is_constant=False,
        is_input=True,
        is_free=False,
        is_implied=False,
        is_explicit=True,
        is_read_only=False,
        is_persist=False,
        is_addr_tied=False,
    )


def test_op_text_shows_branch_targets_for_cbranch() -> None:
    """Test that op_text() shows branch targets for Cbranch ops."""
    cbranch = Cbranch(
        id=1,
        opcode="CBRANCH",
        instruction_address=0x2000,
        sequence_time=2,
        sequence_order=2,
        input_varnode_ids=[2],
        output_varnode_id=None,
        true_target_address=0x2010,
        false_target_address=0x2020,
    )
    varnode_by_id: dict[int, RegisterVarnode] = {}

    result = _inspector.op_text(cbranch, varnode_by_id, depth=1)

    assert "--- Branch Targets ---" in result
    assert "True target:  0x2010" in result
    assert "False target: 0x2020" in result


def test_op_text_shows_none_for_cbranch_without_targets() -> None:
    """Test that op_text() shows 'none' for Cbranch ops without target addresses."""
    cbranch = Cbranch(
        id=1,
        opcode="CBRANCH",
        instruction_address=0x2000,
        sequence_time=2,
        sequence_order=2,
        input_varnode_ids=[2],
        output_varnode_id=None,
        true_target_address=None,
        false_target_address=None,
    )
    varnode_by_id: dict[int, RegisterVarnode] = {}

    result = _inspector.op_text(cbranch, varnode_by_id, depth=1)

    assert "--- Branch Targets ---" in result
    assert "True target:  none" in result
    assert "False target: none" in result


def test_op_text_does_not_show_branch_targets_for_non_cbranch() -> None:
    """Test that op_text() does not show branch targets for non-CBRANCH ops."""
    int_add = IntAdd(
        id=0,
        opcode="INT_ADD",
        instruction_address=0x1000,
        sequence_time=1,
        sequence_order=1,
        input_varnode_ids=[0, 1],
        output_varnode_id=2,
    )
    varnode_by_id: dict[int, RegisterVarnode] = {}

    result = _inspector.op_text(int_add, varnode_by_id, depth=1)

    assert "--- Branch Targets ---" not in result
    assert "True target:" not in result
    assert "False target:" not in result


def test_varnode_text_shows_iop_target_for_iop_varnode() -> None:
    """Test that varnode_text() shows IOP target for IopVarnode."""
    iop_varnode = IopVarnode(
        id=5,
        space="iop",
        offset=0,
        size=4,
        flags=_make_varnode_flags(),
        defining_op_id=3,
        use_op_ids=[4],
        target_op_id=10,
    )
    op_by_id: dict[int, IntAdd] = {
        3: IntAdd(
            id=3,
            opcode="INT_ADD",
            instruction_address=0x1000,
            sequence_time=1,
            sequence_order=1,
            input_varnode_ids=[],
            output_varnode_id=5,
        )
    }

    result = _inspector.varnode_text(iop_varnode, op_by_id, depth=1)

    assert "--- IOP Target ---" in result
    assert "Target op:   #10" in result


def test_varnode_text_shows_none_for_iop_varnode_without_target() -> None:
    """Test that varnode_text() shows 'none' for IopVarnode without target."""
    iop_varnode = IopVarnode(
        id=5,
        space="iop",
        offset=0,
        size=4,
        flags=_make_varnode_flags(),
        defining_op_id=3,
        use_op_ids=[4],
        target_op_id=None,
    )
    op_by_id: dict[int, IntAdd] = {
        3: IntAdd(
            id=3,
            opcode="INT_ADD",
            instruction_address=0x1000,
            sequence_time=1,
            sequence_order=1,
            input_varnode_ids=[],
            output_varnode_id=5,
        )
    }

    result = _inspector.varnode_text(iop_varnode, op_by_id, depth=1)

    assert "--- IOP Target ---" in result
    assert "Target op:   none" in result


def test_varnode_text_shows_call_site_for_fspec_varnode() -> None:
    """Test that varnode_text() shows call site for FspecVarnode."""
    fspec_varnode = FspecVarnode(
        id=6,
        space="fspec",
        offset=0,
        size=4,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[7],
        call_site_index=3,
    )
    op_by_id: dict[int, IntAdd] = {
        7: IntAdd(
            id=7,
            opcode="INT_ADD",
            instruction_address=0x1000,
            sequence_time=1,
            sequence_order=1,
            input_varnode_ids=[],
            output_varnode_id=6,
        )
    }

    result = _inspector.varnode_text(fspec_varnode, op_by_id, depth=1)

    assert "--- Call Site ---" in result
    assert "Site index:  3" in result


def test_varnode_text_shows_none_for_fspec_varnode_without_call_site() -> None:
    """Test that varnode_text() shows 'none' for FspecVarnode without call site."""
    fspec_varnode = FspecVarnode(
        id=6,
        space="fspec",
        offset=0,
        size=4,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[7],
        call_site_index=None,
    )
    op_by_id: dict[int, IntAdd] = {
        7: IntAdd(
            id=7,
            opcode="INT_ADD",
            instruction_address=0x1000,
            sequence_time=1,
            sequence_order=1,
            input_varnode_ids=[],
            output_varnode_id=6,
        )
    }

    result = _inspector.varnode_text(fspec_varnode, op_by_id, depth=1)

    assert "--- Call Site ---" in result
    assert "Site index:  none" in result


def test_varnode_text_does_not_show_cpg_fields_for_regular_varnode() -> None:
    """Test that varnode_text() does not show CPG fields for regular varnodes."""
    reg_varnode = RegisterVarnode(
        id=0,
        space="register",
        offset=0x0,
        size=4,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[0],
    )
    op_by_id: dict[int, IntAdd] = {
        0: IntAdd(
            id=0,
            opcode="INT_ADD",
            instruction_address=0x1000,
            sequence_time=1,
            sequence_order=1,
            input_varnode_ids=[],
            output_varnode_id=0,
        )
    }

    result = _inspector.varnode_text(reg_varnode, op_by_id, depth=1)

    assert "--- IOP Target ---" not in result
    assert "--- Call Site ---" not in result
    assert "Target op:" not in result
    assert "Site index:" not in result
