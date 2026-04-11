from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from flatline import VarnodeFlags
from flatline.models.enums import PcodeOpcode
from flatline.models.pcode_ops import Cbranch, IntAdd, Return
from flatline.xray._layout import VisualNode

if TYPE_CHECKING:
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

    source_root = _node("src-root", ("op", 70), 0)
    target_root = _node("tgt-root", ("op", 71), 0)

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

    edges = collect_iop_edges({1000: iop_vn}, {70: object(), 71: object()}, {70: source_root, 71: target_root})

    assert edges == [(source_root, target_root)]


def test_collect_iop_edges_skips_when_target_op_id_is_none() -> None:
    from flatline.models.enums import VarnodeSpace
    from flatline.models.varnodes import IopVarnode
    from flatline.xray._cpg_overlay import collect_iop_edges

    source_root = _node("src-root", ("op", 72), 0)

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

    edges = collect_iop_edges({1001: iop_vn}, {72: object()}, {72: source_root})

    assert edges == []


def test_collect_iop_edges_skips_when_use_op_ids_is_empty() -> None:
    from flatline.models.enums import VarnodeSpace
    from flatline.models.varnodes import IopVarnode
    from flatline.xray._cpg_overlay import collect_iop_edges

    target_root = _node("tgt-root", ("op", 73), 0)

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

    edges = collect_iop_edges({1002: iop_vn}, {73: object()}, {73: target_root})

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

    edges = collect_iop_edges({1003: non_iop_vn}, {74: object()}, {74: source_root})

    assert edges == []
