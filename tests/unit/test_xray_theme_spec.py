from __future__ import annotations

import importlib

import pytest

from flatline.xray import _inputs

from ._xray_support import fixture_bytes, fixture_target, make_sample_pcode

pytestmark = pytest.mark.unit


def test_theme_module_exports_tokens() -> None:
    module = importlib.import_module("flatline.xray._theme")
    target = fixture_target()
    pcode = make_sample_pcode()

    assert module.BACKGROUND == "#07111c"
    assert module.PANEL_BG == "#0d1726"
    assert module.SELECTION_OUTLINE == "#ffb703"
    assert module.TITLE_FONT == ("Helvetica", 24, "bold")
    assert module.NODE_FONT == ("Helvetica", 10, "bold")
    assert module.opcode_color_for("INT_ADD") == "#ff9f68"
    assert module.varnode_color_for(pcode.varnodes[3]) == "#ffd166"
    assert target.read_memory_image() == fixture_bytes()


def test_inputs_color_helpers_delegate_to_theme(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(  # pyright: ignore[reportPrivateUsage]
        _inputs._theme,
        "opcode_color_for",
        lambda opcode: f"opcode:{opcode}",
    )
    monkeypatch.setattr(  # pyright: ignore[reportPrivateUsage]
        _inputs._theme,
        "varnode_color_for",
        lambda varnode: f"varnode:{varnode.id}",
    )

    pcode = make_sample_pcode()
    assert _inputs._opcode_color("INT_ADD") == "opcode:INT_ADD"  # pyright: ignore[reportPrivateUsage]
    assert _inputs._varnode_color(pcode.varnodes[0]) == "varnode:0"  # pyright: ignore[reportPrivateUsage]


def test_theme_label_helpers_remain_stable() -> None:
    short_opcode = _inputs._short_opcode  # pyright: ignore[reportPrivateUsage]
    varnode_badge = _inputs._varnode_badge  # pyright: ignore[reportPrivateUsage]

    pcode = make_sample_pcode()
    assert short_opcode("INT_ADD") == "INT_ADD"
    assert short_opcode("RETURN") == "RETURN"
    assert varnode_badge(pcode.varnodes[3]) == "CONST"


def test_theme_has_depth_band_and_inactive_edge_tokens() -> None:
    module = importlib.import_module("flatline.xray._theme")

    assert hasattr(module, "DEPTH_BAND_COLOR"), "DEPTH_BAND_COLOR token missing from _theme"
    assert isinstance(module.DEPTH_BAND_COLOR, str) and module.DEPTH_BAND_COLOR.startswith("#")

    assert hasattr(module, "EDGE_INACTIVE_COLOR"), "EDGE_INACTIVE_COLOR token missing from _theme"
    inactive_color = module.EDGE_INACTIVE_COLOR
    assert isinstance(inactive_color, str) and inactive_color.startswith("#")

    assert hasattr(module, "EDGE_INACTIVE_WIDTH"), "EDGE_INACTIVE_WIDTH token missing from _theme"
    assert isinstance(module.EDGE_INACTIVE_WIDTH, (int, float))
    assert module.EDGE_INACTIVE_WIDTH > 0
