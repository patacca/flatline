from __future__ import annotations

import pytest

from flatline.xray import _layout

from ._xray_support import make_sample_pcode

pytestmark = pytest.mark.unit


def test_layout_orders_and_positions_fixture_pcode() -> None:
    pcode = make_sample_pcode()
    varnode_by_id = {varnode.id: varnode for varnode in pcode.varnodes}
    shuffled = [pcode.pcode_ops[1], pcode.pcode_ops[0]]

    ordered = _layout.sorted_ops(shuffled)
    assert [op.id for op in ordered] == [0, 1]
    assert [op.id for op in _layout.sink_ops(ordered, varnode_by_id)] == [1]

    roots, cross_edges = _layout.build_visual_forest(
        {op.id: op for op in pcode.pcode_ops},
        varnode_by_id,
        ordered,
    )
    assert cross_edges == []
    assert [root.actual for root in roots] == [("op", 1)]

    const_node = _layout.VisualNode(key="const", actual=("varnode", 3), depth=0)
    assert _layout.node_size(const_node, varnode_by_id) == (74.0, 68.0)
    assert _layout.node_pad(const_node, varnode_by_id) == 34.0

    max_depth = _layout.measure_forest(roots, lambda node: _layout.node_size(node, varnode_by_id))
    width, height = _layout.compute_canvas_size(roots, max_depth)
    _layout.assign_forest_positions(roots, height)

    assert max_depth == 3
    assert width >= 1400
    assert height >= 940
    assert roots[0].x > 0
    assert roots[0].children[0].y < roots[0].y
