from __future__ import annotations

from dataclasses import replace

import pytest

from flatline import decompile_function
from flatline.xray import _layout
from flatline.xray._inputs import build_decompile_request
from tests._native_fixtures import get_native_runtime_data_dir

from ._xray_support import fixture_target, make_sample_pcode

pytestmark = pytest.mark.unit


def test_layout_orders_and_positions_fixture_pcode() -> None:
    pcode = make_sample_pcode()
    op_by_id = {op.id: op for op in pcode.pcode_ops}
    varnode_by_id = {varnode.id: varnode for varnode in pcode.varnodes}
    shuffled = [pcode.pcode_ops[1], pcode.pcode_ops[0]]

    ordered = _layout.sorted_ops(shuffled)
    assert [op.id for op in ordered] == [0, 1]
    assert [op.id for op in _layout.sink_ops(ordered, varnode_by_id)] == [1]

    roots, cross_edges = _layout.build_visual_forest(
        op_by_id,
        varnode_by_id,
        ordered,
    )
    assert cross_edges == []
    assert [root.actual for root in roots] == [("op", 1)]

    const_node = _layout.VisualNode(key="const", actual=("varnode", 3), depth=0)
    assert _layout.node_size(const_node, op_by_id, varnode_by_id) == (74.0, 68.0)
    assert _layout.node_pad(const_node, op_by_id, varnode_by_id) == 34.0

    max_depth = _layout.measure_forest(
        roots,
        lambda node: _layout.node_size(node, op_by_id, varnode_by_id),
    )
    width, height = _layout.compute_canvas_size(roots, max_depth)
    _layout.assign_forest_positions(roots, height)

    assert max_depth == 3
    assert width >= 1400
    assert height >= 940
    assert roots[0].x > 0
    assert roots[0].children[0].y < roots[0].y


def test_short_opcode_label_fits_computed_node_width() -> None:
    pcode = make_sample_pcode()
    op_by_id = {op.id: op for op in pcode.pcode_ops}
    varnode_by_id = {varnode.id: varnode for varnode in pcode.varnodes}
    node = _layout.VisualNode(key="return", actual=("op", 1), depth=0)

    assert _layout.fit_opcode_label(op_by_id[1].opcode) == "RETURN"
    assert _layout.node_label_lines(node, op_by_id, varnode_by_id) == ("RETURN", "#1")
    assert _layout.node_size(node, op_by_id, varnode_by_id) == (76.0, 76.0)


def test_long_opcode_label_is_shortened_to_budget() -> None:
    pcode = make_sample_pcode()
    op_by_id = {op.id: op for op in pcode.pcode_ops}
    varnode_by_id = {varnode.id: varnode for varnode in pcode.varnodes}
    op_by_id[0] = replace(op_by_id[0], opcode="INT_ZEXT")
    node = _layout.VisualNode(key="op", actual=("op", 0), depth=0)

    assert _layout.fit_opcode_label("INT_ZEXT") == "INT_..."
    assert _layout.node_label_lines(node, op_by_id, varnode_by_id) == ("INT_...", "#0")
    assert _layout.node_size(node, op_by_id, varnode_by_id) == (84.0, 76.0)


def test_long_varnode_label_is_shortened_to_budget() -> None:
    pcode = make_sample_pcode()
    op_by_id = {op.id: op for op in pcode.pcode_ops}
    varnode_by_id = {varnode.id: varnode for varnode in pcode.varnodes}
    varnode_by_id[2] = replace(varnode_by_id[2], space="processor_context")
    node = _layout.VisualNode(key="varnode", actual=("varnode", 2), depth=0)

    assert _layout.varnode_badge(varnode_by_id[2]) == "PROCESSOR_CONTEXT"
    assert _layout.fit_varnode_badge(varnode_by_id[2]) == "PROCE..."
    assert _layout.node_label_lines(node, op_by_id, varnode_by_id) == ("PROCE...", "v2")
    assert _layout.node_size(node, op_by_id, varnode_by_id) == (84.0, 68.0)


def test_dense_switch_graph_stays_within_canvas_bounds() -> None:
    request = build_decompile_request(
        fixture_target("fx_switch_elf64.hex"),
        runtime_data_dir=get_native_runtime_data_dir(),
        enriched=True,
    )
    result = decompile_function(request)

    assert result.error is None
    assert result.enriched is not None

    pcode = result.enriched.pcode
    op_by_id = {op.id: op for op in pcode.pcode_ops}
    varnode_by_id = {varnode.id: varnode for varnode in pcode.varnodes}
    ordered = _layout.sorted_ops(pcode.pcode_ops)
    roots, _ = _layout.build_visual_forest(op_by_id, varnode_by_id, ordered)
    max_depth = _layout.measure_forest(
        roots,
        lambda node: _layout.node_size(node, op_by_id, varnode_by_id),
    )
    width, height = _layout.compute_canvas_size(roots, max_depth)

    assert len(pcode.pcode_ops) == 7
    assert len(pcode.varnodes) == 12
    assert max_depth == 9
    assert width <= 1600
    assert height <= 1600
