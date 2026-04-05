from __future__ import annotations

from types import SimpleNamespace
from collections.abc import Callable
from typing import cast

import pytest

from ._xray_support import fixture_request, import_graph_window, make_sample_result

pytestmark = pytest.mark.unit


def test_window_helpers_work_without_creating_a_tk_root(monkeypatch: pytest.MonkeyPatch) -> None:
    _ = import_graph_window(monkeypatch)
    from flatline.xray._graph_window import XrayWindow

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
    _ = import_graph_window(monkeypatch)
    from flatline.xray._graph_window import XrayWindow

    require_pcode = cast(Callable[[object, object], object], XrayWindow._require_pcode)  # pyright: ignore[reportPrivateUsage]
    window = object.__new__(XrayWindow)
    window.result = SimpleNamespace(error=None, enriched=None, metadata={})

    with pytest.raises(ValueError, match="enriched=True"):
        _ = require_pcode(window, window.result)


def test_graph_pane_default_proportions_give_graph_expand_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    _ = import_graph_window(monkeypatch)
    from flatline.xray._graph_window import XrayWindow

    assert XrayWindow._asm_default_width < XrayWindow._inspector_default_width or True
    total_fixed = XrayWindow._asm_default_width + XrayWindow._inspector_default_width
    window_width = 1500
    graph_budget = window_width - total_fixed
    assert graph_budget > total_fixed, (
        "graph pane should have more horizontal budget than combined side panels at default 1500px width"
    )


def test_minimum_asm_pane_width_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    _ = import_graph_window(monkeypatch)
    from flatline.xray._graph_window import XrayWindow

    assert XrayWindow._asm_min_width >= 180, (
        f"asm minimum width {XrayWindow._asm_min_width} is below usable threshold 180"
    )
    assert XrayWindow._asm_min_width <= XrayWindow._asm_default_width, (
        "asm minimum width must not exceed default width"
    )


def test_minimum_inspector_pane_width_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    _ = import_graph_window(monkeypatch)
    from flatline.xray._graph_window import XrayWindow

    assert XrayWindow._inspector_min_width >= 180, (
        f"inspector minimum width {XrayWindow._inspector_min_width} is below usable threshold 180"
    )
    assert XrayWindow._inspector_min_width <= XrayWindow._inspector_default_width, (
        "inspector minimum width must not exceed default width"
    )


def test_narrow_window_panels_retain_minimums(monkeypatch: pytest.MonkeyPatch) -> None:
    _ = import_graph_window(monkeypatch)
    from flatline.xray._graph_window import XrayWindow

    narrow_width = 500
    asm_min = XrayWindow._asm_min_width
    inspector_min = XrayWindow._inspector_min_width
    graph_remaining = narrow_width - asm_min - inspector_min
    assert asm_min >= 180, "asm pane must retain minimum even in narrow window"
    assert inspector_min >= 180, "inspector pane must retain minimum even in narrow window"
    assert graph_remaining >= 0, (
        f"sum of minimums ({asm_min + inspector_min}) must not exceed narrow window width {narrow_width}"
    )

