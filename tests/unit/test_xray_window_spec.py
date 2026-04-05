from __future__ import annotations

import ast
import importlib
import inspect
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast

import pytest

from ._xray_support import fixture_request, import_graph_window, make_sample_result

pytestmark = pytest.mark.unit


class _CanvasStub:
    def __init__(self) -> None:
        self.configured: dict[str, dict[str, object]] = {}

    def itemconfigure(self, tag: str, **kwargs: object) -> None:
        self.configured.setdefault(tag, {}).update(kwargs)


class _ListboxStub:
    def __init__(self) -> None:
        self.selected: list[int] = []
        self.seen: list[int] = []

    def curselection(self) -> tuple[int, ...]:
        return tuple(self.selected)

    def selection_clear(self, _start: object, _end: object) -> None:
        self.selected.clear()

    def selection_set(self, index: int) -> None:
        if index not in self.selected:
            self.selected.append(index)

    def see(self, index: int) -> None:
        self.seen.append(index)


def _make_window(monkeypatch: pytest.MonkeyPatch):
    graph_window = import_graph_window(monkeypatch)
    layout = importlib.import_module("flatline.xray._layout")
    XrayWindow = graph_window.XrayWindow
    build_visual_forest = layout.build_visual_forest
    collect_visual_nodes = layout.collect_visual_nodes
    sorted_ops = layout.sorted_ops

    result = make_sample_result()
    pcode = result.enriched.pcode if result.enriched is not None else None
    assert pcode is not None
    op_by_id = {op.id: op for op in pcode.pcode_ops}
    varnode_by_id = {varnode.id: varnode for varnode in pcode.varnodes}
    ordered_ops = sorted_ops(pcode.pcode_ops)
    visual_roots, _cross_edges = build_visual_forest(op_by_id, varnode_by_id, ordered_ops)
    visual_nodes = collect_visual_nodes(visual_roots)

    window = object.__new__(XrayWindow)
    window.window_title = "Sample Xray"
    window.result = result
    window.request = fixture_request()
    window.source_label = "fixture"
    window.result_label = "x86:LE:64:default / gcc"
    window.pcode = pcode
    window.op_by_id = op_by_id
    window.varnode_by_id = varnode_by_id
    window.sorted_ops = ordered_ops
    window.visual_roots = visual_roots
    window.visual_nodes = visual_nodes
    window.max_depth = 0
    window.virtual_width = 0
    window.virtual_height = 0
    window._node_by_key = {node.key: node for node in visual_nodes}
    window._disasm = [(0x1000, "0x1000: ADD EAX, EBX"), (0x1003, "0x1003: RET")]
    window._highlighted_keys = set()
    window._selected_key = None
    window.canvas = _CanvasStub()
    window.asm_listbox = _ListboxStub()
    window._inspector_value = ""
    window._related_keys = set()
    window._muted_keys = set()

    def set_inspector_text(text: str) -> None:
        window._inspector_value = text

    window._set_inspector_text = set_inspector_text
    return window, XrayWindow


def _node_for(window: Any, actual: tuple[str, int]):
    for node in window.visual_nodes:
        if node.actual == actual:
            return node
    raise AssertionError(f"missing visual node for {actual!r}")


def test_window_helpers_work_without_creating_a_tk_root(monkeypatch: pytest.MonkeyPatch) -> None:
    graph_window = import_graph_window(monkeypatch)
    XrayWindow = graph_window.XrayWindow

    result = make_sample_result()
    request = fixture_request()
    enriched = result.enriched
    assert enriched is not None
    require_pcode = cast(Callable[[object, object], object], XrayWindow._require_pcode)  # pyright: ignore[reportPrivateUsage]
    result_label = cast(Callable[[object], str], XrayWindow._result_label)  # pyright: ignore[reportPrivateUsage]
    fallback_address = cast(Callable[[object], int | None], XrayWindow._fallback_address)  # pyright: ignore[reportPrivateUsage]
    disassemble = cast(Callable[[object], list[tuple[int, str]]], XrayWindow._disassemble)  # pyright: ignore[reportPrivateUsage]

    window = object.__new__(XrayWindow)
    window.result = result
    window.request = request
    window.pcode = enriched.pcode
    assert window.pcode is not None

    assert require_pcode(window, result) is window.pcode
    assert result_label(window) == "x86:LE:64:default / gcc"
    assert fallback_address(window) == 0x1000
    assert [address for address, _ in disassemble(window)] == [0x1000, 0x1003]


def test_window_helper_rejects_unenriched_results(monkeypatch: pytest.MonkeyPatch) -> None:
    graph_window = import_graph_window(monkeypatch)
    XrayWindow = graph_window.XrayWindow

    require_pcode = cast(Callable[[object, object], object], XrayWindow._require_pcode)  # pyright: ignore[reportPrivateUsage]
    window = object.__new__(XrayWindow)
    window.result = SimpleNamespace(error=None, enriched=None, metadata={})

    with pytest.raises(ValueError, match="enriched=True"):
        _ = require_pcode(window, window.result)


def test_graph_pane_default_proportions_give_graph_expand_priority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_window = import_graph_window(monkeypatch)
    XrayWindow = graph_window.XrayWindow

    total_fixed = XrayWindow._asm_default_width + XrayWindow._inspector_default_width
    window_width = 1500
    graph_budget = window_width - total_fixed
    assert graph_budget > total_fixed, (
        "graph pane should have more horizontal budget than combined side panels "
        "at default 1500px width"
    )


def test_minimum_asm_pane_width_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    graph_window = import_graph_window(monkeypatch)
    XrayWindow = graph_window.XrayWindow

    assert XrayWindow._asm_min_width >= 180, (
        f"asm minimum width {XrayWindow._asm_min_width} is below usable threshold 180"
    )
    assert XrayWindow._asm_min_width <= XrayWindow._asm_default_width, (
        "asm minimum width must not exceed default width"
    )


def test_minimum_inspector_pane_width_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    graph_window = import_graph_window(monkeypatch)
    XrayWindow = graph_window.XrayWindow

    assert XrayWindow._inspector_min_width >= 180, (
        f"inspector minimum width {XrayWindow._inspector_min_width} is below usable threshold 180"
    )
    assert XrayWindow._inspector_min_width <= XrayWindow._inspector_default_width, (
        "inspector minimum width must not exceed default width"
    )


def test_narrow_window_panels_retain_minimums(monkeypatch: pytest.MonkeyPatch) -> None:
    graph_window = import_graph_window(monkeypatch)
    XrayWindow = graph_window.XrayWindow

    narrow_width = 500
    asm_min = XrayWindow._asm_min_width
    inspector_min = XrayWindow._inspector_min_width
    graph_remaining = narrow_width - asm_min - inspector_min
    assert asm_min >= 180, "asm pane must retain minimum even in narrow window"
    assert inspector_min >= 180, "inspector pane must retain minimum even in narrow window"
    assert graph_remaining >= 0, (
        f"sum of minimums ({asm_min + inspector_min}) must not exceed narrow window "
        f"width {narrow_width}"
    )


def test_selection_graph_node_click_syncs_inspector_and_assembly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, XrayWindow = _make_window(monkeypatch)

    show_node = cast(Callable[[object, object], None], XrayWindow._show_node)  # pyright: ignore[reportPrivateUsage]
    node = _node_for(window, ("op", 0))
    show_node(window, node)

    assert "Op #0 - INT_ADD" in window._inspector_value
    assert window.asm_listbox.selected == [0]
    assert window.canvas.configured[f"shape-{node.key}"]["outline"] == "#ffb703"


def test_selection_assembly_select_highlights_related_nodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, XrayWindow = _make_window(monkeypatch)

    on_asm_select = cast(Callable[[object, object], None], XrayWindow._on_asm_select)  # pyright: ignore[reportPrivateUsage]
    window.asm_listbox.selected = [0]
    on_asm_select(window, None)

    op_node = _node_for(window, ("op", 0))
    related_node = _node_for(window, ("varnode", 2))
    assert "Assembly selection" in window._inspector_value
    assert window.canvas.configured[f"shape-{op_node.key}"]["outline"] == "#ffb703"
    assert window.canvas.configured[f"shape-{related_node.key}"]["outline"] == "#a07cdc"


def test_selection_state_clears_on_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    window, XrayWindow = _make_window(monkeypatch)

    show_node = cast(Callable[[object, object], None], XrayWindow._show_node)  # pyright: ignore[reportPrivateUsage]
    clear_state = cast(Callable[[object], None], XrayWindow._clear_selection_state)  # pyright: ignore[reportPrivateUsage]
    related_node = _node_for(window, ("varnode", 2))
    node = _node_for(window, ("op", 0))
    show_node(window, node)
    clear_state(window)

    assert window._selected_key is None
    assert window._highlighted_keys == set()
    assert window._related_keys == set()
    assert window._muted_keys == set()
    assert window.canvas.configured[f"shape-{node.key}"]["width"] == 2
    assert window.canvas.configured[f"shape-{related_node.key}"]["width"] == 2


def test_selection_selected_and_related_states_are_visually_distinct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, XrayWindow = _make_window(monkeypatch)

    show_node = cast(Callable[[object, object], None], XrayWindow._show_node)  # pyright: ignore[reportPrivateUsage]
    node = _node_for(window, ("op", 0))
    related_node = _node_for(window, ("varnode", 2))
    muted_node = _node_for(window, ("op", 1))
    show_node(window, node)

    assert window.canvas.configured[f"shape-{node.key}"] == {"outline": "#ffb703", "width": 4}
    assert window.canvas.configured[f"shape-{related_node.key}"] == {
        "outline": "#a07cdc",
        "width": 3,
    }
    assert window.canvas.configured[f"shape-{muted_node.key}"] == {
        "outline": "#93a7c1",
        "width": 1,
    }


def test_layout_integration_positions_nodes_within_canvas_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    window, XrayWindow = _make_window(monkeypatch)
    layout = importlib.import_module("flatline.xray._layout")

    max_depth = layout.measure_forest(
        window.visual_roots,
        lambda node: layout.node_size(node, window.op_by_id, window.varnode_by_id),
        child_gap=XrayWindow._child_gap,
    )
    width, height = layout.compute_canvas_size(
        window.visual_roots,
        max_depth,
        root_gap=XrayWindow._root_gap,
        top_margin=XrayWindow._top_margin,
        bottom_margin=XrayWindow._bottom_margin,
        side_margin=XrayWindow._side_margin,
        level_gap=XrayWindow._level_gap,
    )
    layout.assign_forest_positions(
        window.visual_roots,
        height,
        side_margin=XrayWindow._side_margin,
        bottom_margin=XrayWindow._bottom_margin,
        root_gap=XrayWindow._root_gap,
        child_gap=XrayWindow._child_gap,
        level_gap=XrayWindow._level_gap,
    )

    for node in window.visual_nodes:
        node_width, node_height = layout.node_size(node, window.op_by_id, window.varnode_by_id)
        assert node_width / 2.0 <= node.x <= width - node_width / 2.0
        assert node_height / 2.0 <= node.y <= height - node_height / 2.0


def test_graph_window_and_canvas_do_not_bypass_layout_node_size_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_window = import_graph_window(monkeypatch)
    canvas = importlib.import_module("flatline.xray._canvas")

    graph_source = inspect.getsource(graph_window)
    assert ".create_rectangle(" not in graph_source
    assert ".create_text(" not in graph_source

    canvas_source = inspect.getsource(canvas)
    tree = ast.parse(canvas_source)
    for function_name in ("draw_op_node", "draw_varnode_node"):
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == function_name
        )
        names = {node.id for node in ast.walk(function) if isinstance(node, ast.Name)}
        assert "node_size" in names
        assert "node_label_lines" in names


def test_initial_zoom_constant_defined(monkeypatch: pytest.MonkeyPatch) -> None:
    graph_window = import_graph_window(monkeypatch)
    XrayWindow = graph_window.XrayWindow

    assert hasattr(XrayWindow, "_INITIAL_ZOOM"), "_INITIAL_ZOOM class constant is missing"
    assert isinstance(XrayWindow._INITIAL_ZOOM, float), "_INITIAL_ZOOM must be a float"
    assert XrayWindow._INITIAL_ZOOM > 0.0, "_INITIAL_ZOOM must be a positive value"


def test_viewport_reset_method_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    graph_window = import_graph_window(monkeypatch)
    XrayWindow = graph_window.XrayWindow

    assert callable(getattr(XrayWindow, "reset_view", None)), (
        "XrayWindow must expose a callable reset_view() method"
    )
