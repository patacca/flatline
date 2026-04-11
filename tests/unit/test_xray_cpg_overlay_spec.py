from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from flatline import VarnodeFlags
from flatline.models.enums import PcodeOpcode
from flatline.models.pcode_ops import Cbranch, IntAdd, Return
from flatline.xray._layout import VisualNode

if TYPE_CHECKING:
    from flatline import FunctionInfo
    from flatline.models import PcodeOpInfo


pytestmark = pytest.mark.unit


def _make_op(
    op_cls: type[PcodeOpInfo],
    op_id: int,
    instruction_address: int,
    *,
    opcode: str,
    true_target_address: int | None = None,
    false_target_address: int | None = None,
) -> PcodeOpInfo:
    return op_cls(
        id=op_id,
        opcode=PcodeOpcode(opcode),
        instruction_address=instruction_address,
        sequence_time=op_id,
        sequence_order=op_id,
        input_varnode_ids=[],
        output_varnode_id=None,
        true_target_address=true_target_address,
        false_target_address=false_target_address,
    )


def _node(key: str, actual: tuple[str, int], depth: int, *children: VisualNode) -> VisualNode:
    return VisualNode(key=key, actual=actual, depth=depth, children=list(children))


def test_build_address_to_roots_indexes_ops_by_instruction_address() -> None:
    from flatline.xray._cpg_overlay import build_address_to_roots

    op_root = _node("root-op", ("op", 10), 0)
    varnode = _node("vn-1", ("varnode", 200), 1)
    nested_op = _node("nested-op", ("op", 11), 2)
    varnode.children.append(nested_op)
    op_root.children.append(varnode)
    op_by_id = {
        10: _make_op(Return, 10, 0x401000, opcode="RETURN"),
        11: _make_op(IntAdd, 11, 0x401004, opcode="INT_ADD"),
    }

    address_to_roots = build_address_to_roots([op_root], op_by_id)

    assert address_to_roots == {
        0x401000: [op_root],
        0x401004: [op_root],
    }


def test_build_address_to_roots_accumulates_multiple_roots_at_same_address() -> None:
    from flatline.xray._cpg_overlay import build_address_to_roots

    first_root = _node("root-a", ("op", 20), 0)
    second_root = _node("root-b", ("op", 21), 0)
    op_by_id = {
        20: _make_op(Return, 20, 0x401010, opcode="RETURN"),
        21: _make_op(IntAdd, 21, 0x401010, opcode="INT_ADD"),
    }

    address_to_roots = build_address_to_roots([first_root, second_root], op_by_id)

    assert address_to_roots[0x401010] == [first_root, second_root]


def test_build_opid_to_root_maps_nested_ops_to_their_subtree_root() -> None:
    from flatline.xray._cpg_overlay import build_opid_to_root

    nested_op = _node("nested-op", ("op", 31), 2)
    root = _node("root", ("op", 30), 0, _node("vn-1", ("varnode", 301), 1, nested_op))

    opid_to_root = build_opid_to_root(
        [root],
        {
            30: _make_op(Return, 30, 0x401020, opcode="RETURN"),
            31: _make_op(IntAdd, 31, 0x401024, opcode="INT_ADD"),
        },
    )

    assert opid_to_root[30] is root
    assert opid_to_root[31] is root


def test_collect_cbranch_edges_emits_true_and_false_edges_for_matching_roots() -> None:
    from flatline.xray._cpg_overlay import collect_cbranch_edges

    source_root = _node("source", ("op", 40), 0)
    true_root_a = _node("true-a", ("op", 41), 0)
    true_root_b = _node("true-b", ("op", 42), 0)
    false_root = _node("false", ("op", 43), 0)
    branch = _make_op(
        Cbranch,
        40,
        0x401030,
        opcode="CBRANCH",
        true_target_address=0x401040,
        false_target_address=0x401050,
    )

    edges = collect_cbranch_edges(
        [branch],
        {
            0x401040: [true_root_a, true_root_b],
            0x401050: [false_root],
        },
        {40: source_root},
    )

    assert edges == [
        (source_root, true_root_a, "true"),
        (source_root, true_root_b, "true"),
        (source_root, false_root, "false"),
    ]


def test_collect_cbranch_edges_skips_missing_source_and_missing_targets() -> None:
    from flatline.xray._cpg_overlay import collect_cbranch_edges

    missing_source_branch = _make_op(
        Cbranch,
        50,
        0x401060,
        opcode="CBRANCH",
        true_target_address=0x401070,
        false_target_address=0x401080,
    )
    partial_branch = _make_op(
        Cbranch,
        51,
        0x401064,
        opcode="CBRANCH",
        true_target_address=None,
        false_target_address=0x401090,
    )
    source_root = _node("source", ("op", 51), 0)
    target_root = _node("target", ("op", 52), 0)

    edges = collect_cbranch_edges(
        [missing_source_branch, partial_branch],
        {0x401090: [target_root]},
        {51: source_root},
    )

    assert edges == [(source_root, target_root, "false")]


def test_collect_cbranch_edges_ignores_non_cbranch_ops() -> None:
    from flatline.xray._cpg_overlay import collect_cbranch_edges

    source_root = _node("source", ("op", 60), 0)
    target_root = _node("target", ("op", 61), 0)
    not_a_branch = _make_op(Return, 60, 0x4010A0, opcode="RETURN", true_target_address=0x4010B0)

    edges = collect_cbranch_edges(
        [not_a_branch],
        {0x4010B0: [target_root]},
        {60: source_root},
    )

    assert edges == []


# ---------------------------------------------------------------------------
# Task 5 — IOP edge collection
# ---------------------------------------------------------------------------


def _make_varnode_flags() -> VarnodeFlags:
    return VarnodeFlags(
        is_constant=False,
        is_input=False,
        is_free=False,
        is_implied=False,
        is_explicit=True,
        is_read_only=False,
        is_persist=False,
        is_addr_tied=False,
    )


def test_collect_iop_edges_returns_edge_for_valid_iop_varnode() -> None:
    from flatline.models.enums import VarnodeSpace
    from flatline.models.varnodes import IopVarnode
    from flatline.xray._cpg_overlay import collect_iop_edges

    iop_vn_node = _node("iop-vn", ("varnode", 1000), 1)
    target_op_node = _node("tgt-op", ("op", 71), 0)

    iop_vn = IopVarnode(
        id=1000,
        space=VarnodeSpace.IOP,
        offset=0,
        size=8,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[70],
        target_op_id=71,
    )

    opid_to_node = {71: target_op_node}
    vnid_to_node = {1000: iop_vn_node}
    edges = collect_iop_edges({1000: iop_vn}, opid_to_node, vnid_to_node)

    assert edges == [(iop_vn_node, target_op_node)]


def test_collect_iop_edges_skips_when_target_op_id_is_none() -> None:
    from flatline.models.enums import VarnodeSpace
    from flatline.models.varnodes import IopVarnode
    from flatline.xray._cpg_overlay import collect_iop_edges

    iop_vn_node = _node("iop-vn", ("varnode", 1001), 1)

    iop_vn = IopVarnode(
        id=1001,
        space=VarnodeSpace.IOP,
        offset=0,
        size=8,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[72],
        target_op_id=None,
    )

    edges = collect_iop_edges({1001: iop_vn}, {}, {1001: iop_vn_node})

    assert edges == []


def test_collect_iop_edges_skips_when_iop_varnode_not_visualized() -> None:
    from flatline.models.enums import VarnodeSpace
    from flatline.models.varnodes import IopVarnode
    from flatline.xray._cpg_overlay import collect_iop_edges

    target_op_node = _node("tgt-op", ("op", 73), 0)

    iop_vn = IopVarnode(
        id=1002,
        space=VarnodeSpace.IOP,
        offset=0,
        size=8,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[],
        target_op_id=73,
    )

    edges = collect_iop_edges({1002: iop_vn}, {73: target_op_node}, {})

    assert edges == []


def test_collect_iop_edges_ignores_non_iop_varnodes() -> None:
    from flatline.models.enums import VarnodeSpace
    from flatline.models.varnodes import UniqueVarnode
    from flatline.xray._cpg_overlay import collect_iop_edges

    source_root = _node("src-root", ("op", 74), 0)

    non_iop_vn = UniqueVarnode(
        id=1003,
        space=VarnodeSpace.UNIQUE,
        offset=0x100,
        size=8,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[74],
    )

    edges = collect_iop_edges({1003: non_iop_vn}, {74: source_root}, {})

    assert edges == []


def test_collect_iop_edges_connects_varnode_node_to_target_op_node_not_roots() -> None:
    """Regression: IOP edges must connect the IOP varnode visual node to the
    target op visual node, not their subtree roots.  The old implementation
    resolved both endpoints via opid_to_root, which collapsed intra-subtree
    references into self-loops on the root."""
    from flatline.models.enums import VarnodeSpace
    from flatline.models.varnodes import IopVarnode
    from flatline.xray._cpg_overlay import collect_iop_edges

    # Build a subtree: root_op -> iop_vn_node -> nested_op
    nested_op = _node("nested-op", ("op", 91), 2)
    iop_vn_node = _node("iop-vn", ("varnode", 2000), 1, nested_op)
    root_op = _node("root-op", ("op", 90), 0, iop_vn_node)

    iop_vn = IopVarnode(
        id=2000,
        space=VarnodeSpace.IOP,
        offset=0,
        size=8,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[90],
        target_op_id=91,
    )

    opid_to_node = {90: root_op, 91: nested_op}
    vnid_to_node = {2000: iop_vn_node}
    edges = collect_iop_edges({2000: iop_vn}, opid_to_node, vnid_to_node)

    # The edge MUST go from the IOP varnode node to the nested op node,
    # NOT from root_op to root_op (which is what root-level resolution gives).
    assert edges == [(iop_vn_node, nested_op)]


# ---------------------------------------------------------------------------
# build_opid_to_node / build_vnid_to_node
# ---------------------------------------------------------------------------


def test_build_opid_to_node_maps_ops_to_their_own_visual_nodes() -> None:
    from flatline.xray._cpg_overlay import build_opid_to_node

    nested_op = _node("nested-op", ("op", 31), 2)
    root = _node("root", ("op", 30), 0, _node("vn-1", ("varnode", 301), 1, nested_op))

    opid_to_node = build_opid_to_node([root])

    assert opid_to_node[30] is root
    assert opid_to_node[31] is nested_op


def test_build_vnid_to_node_maps_varnodes_to_their_own_visual_nodes() -> None:
    from flatline.xray._cpg_overlay import build_vnid_to_node

    vn_node = _node("vn-1", ("varnode", 301), 1)
    root = _node("root", ("op", 30), 0, vn_node)

    vnid_to_node = build_vnid_to_node([root])

    assert vnid_to_node[301] is vn_node


# ---------------------------------------------------------------------------
# Task 6 — FSPEC edge collection and virtual node helper
# ---------------------------------------------------------------------------


def _make_function_info(call_sites: list) -> FunctionInfo:
    from flatline import (
        DiagnosticFlags,
        FunctionInfo as _FunctionInfo,
        FunctionPrototype,
        TypeInfo,
    )

    return _FunctionInfo(
        name="stub",
        entry_address=0x400000,
        size=64,
        is_complete=True,
        prototype=FunctionPrototype(
            calling_convention="__cdecl",
            parameters=[],
            return_type=TypeInfo(name="void", size=0, metatype="void"),
            is_noreturn=False,
            has_this_pointer=False,
            has_input_errors=False,
            has_output_errors=False,
        ),
        local_variables=[],
        call_sites=call_sites,
        jump_tables=[],
        diagnostics=DiagnosticFlags(
            is_complete=True,
            has_unreachable_blocks=False,
            has_unimplemented=False,
            has_bad_data=False,
            has_no_code=False,
        ),
        varnode_count=0,
    )


def test_make_virtual_node_id_returns_indexed_id() -> None:
    from flatline.xray._cpg_overlay import make_virtual_node_id

    assert make_virtual_node_id("0x401000", 0) == "fspec_virtual_0"
    assert make_virtual_node_id("0x402000", 7) == "fspec_virtual_7"


def test_collect_fspec_edges_returns_edge_for_valid_fspec_varnode() -> None:
    from flatline.models.enums import VarnodeSpace
    from flatline.models.types import CallSiteInfo
    from flatline.models.varnodes import FspecVarnode
    from flatline.xray._cpg_overlay import collect_fspec_edges

    source_root = _node("src-root", ("op", 80), 0)

    fspec_vn = FspecVarnode(
        id=2000,
        space=VarnodeSpace.FSPEC,
        offset=0,
        size=8,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[80],
        call_site_index=0,
    )

    fi = _make_function_info([CallSiteInfo(instruction_address=0x401000, target_address=0x402000)])

    edges = collect_fspec_edges({2000: fspec_vn}, {80: source_root}, fi)

    assert edges == [(source_root, "0x402000")]


def test_collect_fspec_edges_skips_indirect_call_with_no_target_address() -> None:
    from flatline.models.enums import VarnodeSpace
    from flatline.models.types import CallSiteInfo
    from flatline.models.varnodes import FspecVarnode
    from flatline.xray._cpg_overlay import collect_fspec_edges

    source_root = _node("src-root", ("op", 81), 0)

    fspec_vn = FspecVarnode(
        id=2001,
        space=VarnodeSpace.FSPEC,
        offset=0,
        size=8,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[81],
        call_site_index=0,
    )

    fi = _make_function_info([CallSiteInfo(instruction_address=0x401010, target_address=None)])

    edges = collect_fspec_edges({2001: fspec_vn}, {81: source_root}, fi)

    assert edges == []


def test_collect_fspec_edges_skips_out_of_range_call_site_index() -> None:
    from flatline.models.enums import VarnodeSpace
    from flatline.models.varnodes import FspecVarnode
    from flatline.xray._cpg_overlay import collect_fspec_edges

    source_root = _node("src-root", ("op", 82), 0)

    fspec_vn = FspecVarnode(
        id=2002,
        space=VarnodeSpace.FSPEC,
        offset=0,
        size=8,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[82],
        call_site_index=5,
    )

    fi = _make_function_info([])

    edges = collect_fspec_edges({2002: fspec_vn}, {82: source_root}, fi)

    assert edges == []


def test_collect_fspec_edges_skips_when_function_info_is_none() -> None:
    from flatline.models.enums import VarnodeSpace
    from flatline.models.varnodes import FspecVarnode
    from flatline.xray._cpg_overlay import collect_fspec_edges

    source_root = _node("src-root", ("op", 83), 0)

    fspec_vn = FspecVarnode(
        id=2003,
        space=VarnodeSpace.FSPEC,
        offset=0,
        size=8,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[83],
        call_site_index=0,
    )

    edges = collect_fspec_edges({2003: fspec_vn}, {83: source_root}, None)

    assert edges == []


def test_collect_fspec_edges_skips_when_use_op_ids_is_empty() -> None:
    from flatline.models.enums import VarnodeSpace
    from flatline.models.types import CallSiteInfo
    from flatline.models.varnodes import FspecVarnode
    from flatline.xray._cpg_overlay import collect_fspec_edges

    fspec_vn = FspecVarnode(
        id=2004,
        space=VarnodeSpace.FSPEC,
        offset=0,
        size=8,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[],
        call_site_index=0,
    )

    fi = _make_function_info([CallSiteInfo(instruction_address=0x401020, target_address=0x403000)])

    edges = collect_fspec_edges({2004: fspec_vn}, {}, fi)

    assert edges == []


def test_collect_fspec_edges_skips_when_source_root_not_in_opid_to_root() -> None:
    from flatline.models.enums import VarnodeSpace
    from flatline.models.types import CallSiteInfo
    from flatline.models.varnodes import FspecVarnode
    from flatline.xray._cpg_overlay import collect_fspec_edges

    fspec_vn = FspecVarnode(
        id=2005,
        space=VarnodeSpace.FSPEC,
        offset=0,
        size=8,
        flags=_make_varnode_flags(),
        defining_op_id=None,
        use_op_ids=[85],
        call_site_index=0,
    )

    fi = _make_function_info([CallSiteInfo(instruction_address=0x401030, target_address=0x404000)])

    edges = collect_fspec_edges({2005: fspec_vn}, {}, fi)

    assert edges == []
