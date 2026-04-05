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
