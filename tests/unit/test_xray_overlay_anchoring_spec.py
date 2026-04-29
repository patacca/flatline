from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from flatline.xray._layout import VisualNode

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reload_cpg_overlay() -> None:
    # test_xray_import_spec purges all flatline.xray.* modules from sys.modules
    # to test headless-safe import behaviour.  After that purge the module
    # objects referenced by our `patch()` calls are stale, so we force a
    # fresh import before every test in this file.
    importlib.import_module("flatline.xray._cpg_overlay")


def _make_node(key: str, x: float, y: float) -> VisualNode:
    return VisualNode(key=key, actual=("op", 0), depth=0, x=x, y=y)


def _extract_points(canvas: MagicMock) -> list[tuple[float, float]]:
    call_args = canvas.create_line.call_args
    coords = list(call_args[0])
    return [(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]


def _draw_cbranch_with_polyline(
    edges: list[tuple[VisualNode, VisualNode, str]],
    polyline: list[tuple[float, float]],
    visual_nodes: list[VisualNode],
) -> MagicMock:
    canvas = MagicMock()
    draw_cbranch_edges = sys.modules["flatline.xray._cpg_overlay"].draw_cbranch_edges
    with (
        patch("flatline.xray._cpg_overlay.route_overlay_edges", return_value=[polyline]),
        patch("flatline.xray._cpg_overlay.node_size", return_value=(20.0, 10.0)),
        patch("flatline.xray._cpg_routing.node_size", return_value=(20.0, 10.0)),
    ):
        draw_cbranch_edges(canvas, edges, {}, {}, visual_nodes=visual_nodes)
    return canvas


def test_cbranch_polyline_starts_vertical() -> None:
    src = _make_node("src", 100.0, 100.0)
    tgt = _make_node("tgt", 300.0, 300.0)
    fake_polyline = [(110.0, 100.0), (200.0, 100.0), (200.0, 310.0), (305.0, 295.0)]
    canvas = _draw_cbranch_with_polyline([(src, tgt, "true")], fake_polyline, [src, tgt])

    points = _extract_points(canvas)
    assert points[0][0] == points[1][0], f"Not vertical at start: {points[0]} -> {points[1]}"


def test_cbranch_polyline_ends_vertical() -> None:
    src = _make_node("src", 100.0, 100.0)
    tgt = _make_node("tgt", 300.0, 300.0)
    fake_polyline = [(110.0, 100.0), (200.0, 100.0), (200.0, 310.0), (305.0, 295.0)]
    canvas = _draw_cbranch_with_polyline([(src, tgt, "true")], fake_polyline, [src, tgt])

    points = _extract_points(canvas)
    assert points[-1][0] == points[-2][0], f"Not vertical at end: {points[-2]} -> {points[-1]}"


def test_cbranch_endpoint_clipped_to_bottom_top() -> None:
    src = _make_node("src", 100.0, 100.0)
    tgt = _make_node("tgt", 300.0, 300.0)
    fake_polyline = [(110.0, 100.0), (200.0, 100.0), (200.0, 310.0), (305.0, 295.0)]
    canvas = _draw_cbranch_with_polyline([(src, tgt, "true")], fake_polyline, [src, tgt])

    points = _extract_points(canvas)
    src_bottom = src.y + 10.0 / 2.0
    tgt_top = tgt.y - 10.0 / 2.0
    assert points[0][1] == pytest.approx(src_bottom)
    assert points[-1][1] == pytest.approx(tgt_top)


def test_cbranch_self_loop_falls_back_to_libavoid() -> None:
    src = _make_node("self", 100.0, 100.0)
    fake_polyline = [(110.0, 100.0), (200.0, 200.0), (105.0, 110.0)]
    canvas = _draw_cbranch_with_polyline([(src, src, "true")], fake_polyline, [src])

    points = _extract_points(canvas)
    assert points == list(fake_polyline)


def _draw_iop_with_polyline(
    edges: list[tuple[VisualNode, VisualNode]],
    polyline: list[tuple[float, float]],
    visual_nodes: list[VisualNode],
) -> MagicMock:
    canvas = MagicMock()
    draw_iop_edges = sys.modules["flatline.xray._cpg_overlay"].draw_iop_edges
    with (
        patch("flatline.xray._cpg_overlay.route_overlay_edges", return_value=[polyline]),
        patch("flatline.xray._cpg_overlay.node_size", return_value=(20.0, 10.0)),
        patch("flatline.xray._cpg_routing.node_size", return_value=(20.0, 10.0)),
    ):
        draw_iop_edges(canvas, edges, {}, {}, visual_nodes=visual_nodes)
    return canvas


def test_iop_polyline_starts_horizontal_when_target_right() -> None:
    src = _make_node("src", 100.0, 100.0)
    tgt = _make_node("tgt", 300.0, 100.0)
    fake_polyline = [(110.0, 100.0), (200.0, 100.0), (200.0, 100.0), (290.0, 100.0)]
    canvas = _draw_iop_with_polyline([(src, tgt)], fake_polyline, [src, tgt])

    points = _extract_points(canvas)
    src_right_edge = 100.0 + 20.0 / 2.0
    assert points[0][1] == points[1][1], f"Not horizontal at start: {points[0]} -> {points[1]}"
    assert points[0][0] == pytest.approx(src_right_edge)


def test_iop_polyline_ends_horizontal_when_target_right() -> None:
    src = _make_node("src", 100.0, 100.0)
    tgt = _make_node("tgt", 300.0, 100.0)
    fake_polyline = [(110.0, 100.0), (200.0, 100.0), (200.0, 100.0), (290.0, 100.0)]
    canvas = _draw_iop_with_polyline([(src, tgt)], fake_polyline, [src, tgt])

    points = _extract_points(canvas)
    tgt_left_edge = 300.0 - 20.0 / 2.0
    assert points[-1][1] == points[-2][1], f"Not horizontal at end: {points[-2]} -> {points[-1]}"
    assert points[-1][0] == pytest.approx(tgt_left_edge)


def test_iop_polyline_starts_horizontal_when_target_left() -> None:
    src = _make_node("src", 100.0, 100.0)
    tgt = _make_node("tgt", 50.0, 100.0)
    fake_polyline = [(90.0, 100.0), (70.0, 100.0), (70.0, 100.0), (60.0, 100.0)]
    canvas = _draw_iop_with_polyline([(src, tgt)], fake_polyline, [src, tgt])

    points = _extract_points(canvas)
    src_left_edge = 100.0 - 20.0 / 2.0
    assert points[0][1] == points[1][1], f"Not horizontal at start: {points[0]} -> {points[1]}"
    assert points[0][0] == pytest.approx(src_left_edge)


def test_iop_polyline_ends_horizontal_when_target_left() -> None:
    src = _make_node("src", 100.0, 100.0)
    tgt = _make_node("tgt", 50.0, 100.0)
    fake_polyline = [(90.0, 100.0), (70.0, 100.0), (70.0, 100.0), (60.0, 100.0)]
    canvas = _draw_iop_with_polyline([(src, tgt)], fake_polyline, [src, tgt])

    points = _extract_points(canvas)
    tgt_right_edge = 50.0 + 20.0 / 2.0
    assert points[-1][1] == points[-2][1], f"Not horizontal at end: {points[-2]} -> {points[-1]}"
    assert points[-1][0] == pytest.approx(tgt_right_edge)


def test_iop_self_loop_falls_back_to_libavoid() -> None:
    src = _make_node("self", 100.0, 100.0)
    fake_polyline = [(110.0, 100.0), (200.0, 200.0), (105.0, 110.0)]
    canvas = _draw_iop_with_polyline([(src, src)], fake_polyline, [src])

    points = _extract_points(canvas)
    assert points == list(fake_polyline)


def _draw_fspec_with_polyline(
    edges: list[tuple[VisualNode, str]],
    polyline: list[tuple[float, float]],
    visual_nodes: list[VisualNode],
    target_left: bool = False,
) -> MagicMock:
    canvas = MagicMock()
    draw_fspec_edges = sys.modules["flatline.xray._cpg_overlay"].draw_fspec_edges
    overlay_sizes = [(-60.0, 10.0), (20.0, 10.0)] if target_left else [(20.0, 10.0), (20.0, 10.0)]
    with (
        patch("flatline.xray._cpg_overlay.route_overlay_edges", return_value=[polyline]),
        patch("flatline.xray._cpg_overlay.node_size", side_effect=overlay_sizes),
        patch("flatline.xray._cpg_routing.node_size", return_value=(20.0, 10.0)),
    ):
        draw_fspec_edges(canvas, edges, {}, {}, visual_nodes=visual_nodes)
    return canvas


def test_fspec_polyline_starts_horizontal_when_target_right() -> None:
    src = _make_node("src", 100.0, 100.0)
    fake_polyline = [(110.0, 100.0), (200.0, 100.0), (200.0, 100.0), (290.0, 100.0)]
    canvas = _draw_fspec_with_polyline([(src, "0x401000")], fake_polyline, [src])

    points = _extract_points(canvas)
    src_right_edge = 100.0 + 20.0 / 2.0
    assert points[0][1] == points[1][1], f"Not horizontal at start: {points[0]} -> {points[1]}"
    assert points[0][0] == pytest.approx(src_right_edge)


def test_fspec_polyline_ends_horizontal_when_target_right() -> None:
    src = _make_node("src", 100.0, 100.0)
    fake_polyline = [(110.0, 100.0), (200.0, 100.0), (200.0, 100.0), (290.0, 100.0)]
    canvas = _draw_fspec_with_polyline([(src, "0x401000")], fake_polyline, [src])

    points = _extract_points(canvas)
    tgt_left_edge = (100.0 + 20.0 * 1.5) - 80.0 / 2.0
    assert points[-1][1] == points[-2][1], f"Not horizontal at end: {points[-2]} -> {points[-1]}"
    assert points[-1][0] == pytest.approx(tgt_left_edge)


def test_fspec_polyline_starts_horizontal_when_target_left() -> None:
    src = _make_node("src", 100.0, 100.0)
    fake_polyline = [(110.0, 100.0), (200.0, 100.0), (200.0, 100.0), (290.0, 100.0)]
    canvas = _draw_fspec_with_polyline([(src, "0x401000")], fake_polyline, [src], target_left=True)

    points = _extract_points(canvas)
    src_left_edge = 100.0 - 20.0 / 2.0
    assert points[0][1] == points[1][1], f"Not horizontal at start: {points[0]} -> {points[1]}"
    assert points[0][0] == pytest.approx(src_left_edge)


def test_fspec_polyline_ends_horizontal_when_target_left() -> None:
    src = _make_node("src", 100.0, 100.0)
    fake_polyline = [(110.0, 100.0), (200.0, 100.0), (200.0, 100.0), (290.0, 100.0)]
    canvas = _draw_fspec_with_polyline([(src, "0x401000")], fake_polyline, [src], target_left=True)

    points = _extract_points(canvas)
    tgt_right_edge = (100.0 + (-60.0) * 1.5) + 80.0 / 2.0
    assert points[-1][1] == points[-2][1], f"Not horizontal at end: {points[-2]} -> {points[-1]}"
    assert points[-1][0] == pytest.approx(tgt_right_edge)


def test_fspec_self_loop_falls_back_to_libavoid() -> None:
    src = _make_node("self", 100.0, 100.0)
    fake_polyline = [(110.0, 100.0), (200.0, 200.0), (105.0, 110.0)]
    with patch("flatline.xray._cpg_overlay.make_virtual_node_id", return_value="self"):
        canvas = _draw_fspec_with_polyline([(src, "0x401000")], fake_polyline, [src])

    points = _extract_points(canvas)
    assert points == list(fake_polyline)
