from __future__ import annotations

import importlib
import inspect
from dataclasses import replace

import pytest

from ._xray_support import make_sample_pcode

pytestmark = pytest.mark.unit

_layout = importlib.import_module("flatline.xray._layout")


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


def test_node_label_lines_fit_within_computed_node_widths() -> None:
    pcode = make_sample_pcode()
    op_by_id = {op.id: op for op in pcode.pcode_ops}
    varnode_by_id = {varnode.id: varnode for varnode in pcode.varnodes}

    for node in [
        _layout.VisualNode(key="op-0", actual=("op", 0), depth=0),
        _layout.VisualNode(key="op-1", actual=("op", 1), depth=0),
        _layout.VisualNode(key="var-2", actual=("varnode", 2), depth=0),
        _layout.VisualNode(key="const-3", actual=("varnode", 3), depth=0),
    ]:
        label_lines = _layout.node_label_lines(node, op_by_id, varnode_by_id)
        width, _height = _layout.node_size(node, op_by_id, varnode_by_id)
        if node.actual[0] == "op":
            char_width = _layout.OPCODE_CHAR_WIDTH
            pad = _layout.OPCODE_WIDTH_PAD
        else:
            char_width = _layout.VARNODE_CHAR_WIDTH
            pad = _layout.VARNODE_WIDTH_PAD
        label_width = max(len(line) for line in label_lines) * char_width
        assert label_width <= width - pad


def test_canvas_draw_helpers_use_layout_label_contract() -> None:
    canvas = importlib.import_module("flatline.xray._canvas")

    op_source = inspect.getsource(canvas.draw_op_node)
    varnode_source = inspect.getsource(canvas.draw_varnode_node)

    assert "node_label_lines(" in op_source
    assert '"\\n".join(label_lines)' in op_source
    assert "_short_opcode" not in op_source

    assert "node_label_lines(" in varnode_source
    assert '"\\n".join(label_lines)' in varnode_source
    assert "_varnode_badge" not in varnode_source
