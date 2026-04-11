from __future__ import annotations

import inspect

import pytest

from flatline.xray.__main__ import _build_parser

from ._xray_support import import_graph_window

pytestmark = pytest.mark.unit


def test_cpg_flag_defaults_to_false() -> None:
    parser = _build_parser()
    args = parser.parse_args(["dummy"])
    assert args.cpg is False


def test_cpg_flag_activates_when_passed() -> None:
    parser = _build_parser()
    args = parser.parse_args(["--cpg", "dummy"])
    assert args.cpg is True


def test_xray_window_accepts_cpg_param(monkeypatch: pytest.MonkeyPatch) -> None:
    gw = import_graph_window(monkeypatch)
    sig = inspect.signature(gw.XrayWindow.__init__)
    params = list(sig.parameters.keys())

    assert "cpg" in params
    assert "function_info" in params


def test_xray_window_cpg_param_has_default_false(monkeypatch: pytest.MonkeyPatch) -> None:
    gw = import_graph_window(monkeypatch)
    sig = inspect.signature(gw.XrayWindow.__init__)
    cpg_param = sig.parameters["cpg"]

    assert cpg_param.default is False


def test_xray_window_function_info_param_accepts_none(monkeypatch: pytest.MonkeyPatch) -> None:
    gw = import_graph_window(monkeypatch)
    sig = inspect.signature(gw.XrayWindow.__init__)
    function_info_param = sig.parameters["function_info"]

    assert function_info_param.default is None
