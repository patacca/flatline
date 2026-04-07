"""Integration tests for isinstance/enum patterns with real decompilation (Task 11)."""

from __future__ import annotations

import networkx as nx
import pytest

from flatline.models.enums import PcodeOpcode, VarnodeSpace
from flatline.models.pcode_ops import (
    ArithmeticOp,
    CallOp,
    Copy,
    CopyOp,
    IntAdd,
    Return,
)
from flatline.models.types import PcodeOpInfo, VarnodeInfo
from flatline.models.varnodes import RegisterVarnode
from tests._native_fixtures import (
    assert_successful_result,
    get_native_fixture,
    open_native_session,
)

pytestmark = pytest.mark.requires_native


def test_pcode_ops_are_subclass_instances(native_runtime_data_dir: str) -> None:
    """I-TH01: Pcode ops from real decompilation are subclass instances, not bare PcodeOpInfo."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert result.enriched is not None
    assert result.enriched.pcode is not None

    pcode = result.enriched.pcode
    assert pcode.pcode_ops, "Expected at least one pcode op"

    for op in pcode.pcode_ops:
        # Every op should be a subclass instance, not bare PcodeOpInfo
        assert type(op) is not PcodeOpInfo, (
            f"op {op.id} with opcode {op.opcode} is bare PcodeOpInfo, not a subclass"
        )
        # Every op should be an instance of PcodeOpInfo (Liskov substitution)
        assert isinstance(op, PcodeOpInfo), (
            f"op {op.id} with opcode {op.opcode} is not a PcodeOpInfo instance"
        )
        # Every op.opcode should be a PcodeOpcode enum instance
        assert isinstance(op.opcode, PcodeOpcode), (
            f"op {op.id}.opcode is {type(op.opcode).__name__}, not PcodeOpcode"
        )


def test_varnodes_are_subclass_instances(native_runtime_data_dir: str) -> None:
    """I-TH02: Varnodes from real decompilation are subclass instances, not bare VarnodeInfo."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert result.enriched is not None
    assert result.enriched.pcode is not None

    pcode = result.enriched.pcode
    assert pcode.varnodes, "Expected at least one varnode"

    for vn in pcode.varnodes:
        # Every varnode should be a subclass instance, not bare VarnodeInfo
        assert type(vn) is not VarnodeInfo, (
            f"varnode {vn.id} in space '{vn.space}' is bare VarnodeInfo, not a subclass"
        )
        # Every varnode should be an instance of VarnodeInfo (Liskov substitution)
        assert isinstance(vn, VarnodeInfo), (
            f"varnode {vn.id} in space '{vn.space}' is not a VarnodeInfo instance"
        )
        # Every vn.space should be a VarnodeSpace enum instance
        assert isinstance(vn.space, VarnodeSpace), (
            f"varnode {vn.id}.space is {type(vn.space).__name__}, not VarnodeSpace"
        )


def test_isinstance_filtering_finds_ops(native_runtime_data_dir: str) -> None:
    """I-TH03: isinstance filtering works for real decompilation data."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert result.enriched is not None
    pcode = result.enriched.pcode

    # fx_add_elf64 has INT_ADD and RETURN ops
    arithmetic_ops = [op for op in pcode.pcode_ops if isinstance(op, ArithmeticOp)]
    assert len(arithmetic_ops) > 0, "Expected at least one ArithmeticOp"

    call_ops = [op for op in pcode.pcode_ops if isinstance(op, CallOp)]
    assert len(call_ops) > 0, "Expected at least one CallOp (RETURN)"

    # Verify specific leaf classes work
    int_add_ops = [op for op in pcode.pcode_ops if isinstance(op, IntAdd)]
    assert len(int_add_ops) > 0, "Expected at least one IntAdd op"

    return_ops = [op for op in pcode.pcode_ops if isinstance(op, Return)]
    assert len(return_ops) > 0, "Expected at least one Return op"


def test_enum_matching_finds_ops(native_runtime_data_dir: str) -> None:
    """I-TH04: Enum matching works for real decompilation data."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert result.enriched is not None
    pcode = result.enriched.pcode

    # Filter by enum value
    copy_ops = [op for op in pcode.pcode_ops if op.opcode == PcodeOpcode.COPY]
    # COPY ops are common in decompilation output
    if copy_ops:
        for op in copy_ops:
            assert isinstance(op, Copy), "op with COPY opcode should be Copy instance"

    # Filter by INT_ADD enum
    int_add_ops = [op for op in pcode.pcode_ops if op.opcode == PcodeOpcode.INT_ADD]
    assert len(int_add_ops) > 0, "Expected at least one INT_ADD op"
    for op in int_add_ops:
        assert isinstance(op, IntAdd), "op with INT_ADD opcode should be IntAdd instance"

    # Filter by RETURN enum
    return_ops = [op for op in pcode.pcode_ops if op.opcode == PcodeOpcode.RETURN]
    assert len(return_ops) > 0, "Expected at least one RETURN op"
    for op in return_ops:
        assert isinstance(op, Return), "op with RETURN opcode should be Return instance"


def test_varnode_space_filtering_works(native_runtime_data_dir: str) -> None:
    """I-TH05: Varnode space filtering works with subclass instances."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert result.enriched is not None
    pcode = result.enriched.pcode

    # Filter by space enum
    register_vns = [vn for vn in pcode.varnodes if vn.space == VarnodeSpace.REGISTER]
    assert len(register_vns) > 0, "Expected at least one register varnode"

    # Filter by isinstance
    register_vns_isinstance = [vn for vn in pcode.varnodes if isinstance(vn, RegisterVarnode)]
    assert len(register_vns_isinstance) > 0, "Expected at least one RegisterVarnode"

    # Both methods should find the same varnodes
    assert len(register_vns) == len(register_vns_isinstance), (
        "Enum filtering and isinstance filtering should find same register varnodes"
    )

    # Verify all register varnodes are RegisterVarnode instances
    for vn in register_vns:
        assert isinstance(vn, RegisterVarnode), (
            f"varnode {vn.id} with REGISTER space should be RegisterVarnode instance"
        )


def test_graph_works_with_subclass_instances(native_runtime_data_dir: str) -> None:
    """I-TH06: Graph generation works correctly with subclass instances."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert result.enriched is not None
    pcode = result.enriched.pcode

    # Generate graph
    graph = pcode.to_graph()
    assert isinstance(graph, nx.MultiDiGraph), "to_graph() should return MultiDiGraph"

    # Verify node count matches op + varnode count
    expected_node_count = len(pcode.pcode_ops) + len(pcode.varnodes)
    actual_node_count = graph.number_of_nodes()
    assert actual_node_count == expected_node_count, (
        f"Graph has {actual_node_count} nodes, expected {expected_node_count} "
        f"({len(pcode.pcode_ops)} ops + {len(pcode.varnodes)} varnodes)"
    )

    # Verify we can traverse from an op to its output varnode
    int_add_ops = [op for op in pcode.pcode_ops if isinstance(op, IntAdd)]
    assert len(int_add_ops) > 0, "Expected at least one IntAdd op"

    for op in int_add_ops:
        if op.output_varnode_id is not None:
            # The op should be a node in the graph
            op_node = ("op", op.id)
            assert op_node in graph.nodes, f"Op node {op_node} not in graph"

            # The output varnode should be a node in the graph
            vn_node = ("varnode", op.output_varnode_id)
            assert vn_node in graph.nodes, f"Varnode node {vn_node} not in graph"

            # There should be an edge from op to output varnode
            assert graph.has_edge(op_node, vn_node), f"Expected edge from {op_node} to {vn_node}"


def test_category_isinstance_filtering(native_runtime_data_dir: str) -> None:
    """I-TH07: Category isinstance filtering works for real decompilation data."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert result.enriched is not None
    pcode = result.enriched.pcode

    # Test category filtering
    copy_ops = [op for op in pcode.pcode_ops if isinstance(op, CopyOp)]
    # COPY ops are very common
    assert len(copy_ops) > 0, "Expected at least one CopyOp"

    # Verify all CopyOps have COPY opcode
    for op in copy_ops:
        assert op.opcode == PcodeOpcode.COPY, f"CopyOp should have COPY opcode, got {op.opcode}"

    # Test that leaf classes are instances of their category
    for op in pcode.pcode_ops:
        if isinstance(op, IntAdd):
            assert isinstance(op, ArithmeticOp), "IntAdd should be instance of ArithmeticOp"
        if isinstance(op, Return):
            assert isinstance(op, CallOp), "Return should be instance of CallOp"
        if isinstance(op, Copy):
            assert isinstance(op, CopyOp), "Copy should be instance of CopyOp"


def test_multiple_isa_subclass_instances(native_runtime_data_dir: str) -> None:
    """I-TH08: Subclass instances work across multiple ISAs."""
    # Test with ARM64 fixture
    fixture = get_native_fixture("fx_add_arm64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert result.enriched is not None
    pcode = result.enriched.pcode

    # Verify subclass instances for ARM64
    for op in pcode.pcode_ops:
        assert type(op) is not PcodeOpInfo, (
            f"ARM64 op {op.id} with opcode {op.opcode} is bare PcodeOpInfo"
        )
        assert isinstance(op.opcode, PcodeOpcode), (
            f"ARM64 op {op.id}.opcode is not PcodeOpcode enum"
        )

    for vn in pcode.varnodes:
        assert type(vn) is not VarnodeInfo, (
            f"ARM64 varnode {vn.id} in space '{vn.space}' is bare VarnodeInfo"
        )
        assert isinstance(vn.space, VarnodeSpace), (
            f"ARM64 varnode {vn.id}.space is not VarnodeSpace enum"
        )

    # Verify isinstance filtering works for ARM64
    arithmetic_ops = [op for op in pcode.pcode_ops if isinstance(op, ArithmeticOp)]
    assert len(arithmetic_ops) > 0, "Expected at least one ArithmeticOp in ARM64 output"
