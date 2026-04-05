from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import cast

import pytest

from flatline.xray import _inputs

from ._xray_support import fixture_bytes, fixture_target, make_sample_pcode

pytestmark = pytest.mark.unit


def test_theme_module_placeholder() -> None:
    module = importlib.import_module("flatline.xray")
    target = fixture_target()
    pcode = make_sample_pcode()
    opcode_color = cast(Callable[[str], str], _inputs._opcode_color)  # pyright: ignore[reportPrivateUsage]
    short_opcode = cast(Callable[[str], str], _inputs._short_opcode)  # pyright: ignore[reportPrivateUsage]
    varnode_badge = cast(Callable[[object], str], _inputs._varnode_badge)  # pyright: ignore[reportPrivateUsage]

    assert hasattr(module, "main")
    assert target.read_memory_image() == fixture_bytes()
    assert opcode_color("INT_ADD") == "#ff9f68"
    assert short_opcode("INT_ADD") == "INT\nADD"
    assert short_opcode("RETURN") == "RETURN"
    assert varnode_badge(pcode.varnodes[3]) == "CONST"
