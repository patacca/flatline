from __future__ import annotations

import pytest

from flatline.xray._arrowhead_scale import _clamp_arrowshape
from flatline.xray._graph_window import XrayWindow

pytestmark = pytest.mark.unit


def test_clamp_at_unit_zoom_returns_base_unchanged() -> None:
    result = _clamp_arrowshape((12, 14, 6), 1.0, (6, 7, 3), (24, 28, 12))
    assert result == (12.0, 14.0, 6.0)


def test_clamp_at_low_zoom_floors_to_min() -> None:
    result = _clamp_arrowshape((10, 12, 5), 0.05, (6, 7, 3), (24, 28, 12))
    assert result == (6.0, 7.0, 3.0)


def test_clamp_at_high_zoom_ceils_to_max() -> None:
    result = _clamp_arrowshape((12, 14, 6), 10.0, (6, 7, 3), (24, 28, 12))
    assert result == (24.0, 28.0, 12.0)


def test_arrowshape_min_max_constants_are_sane() -> None:
    for base in XrayWindow._ARROW_SHAPES.values():
        for i in range(3):
            assert XrayWindow._ARROWSHAPE_MIN[i] <= base[i] <= XrayWindow._ARROWSHAPE_MAX[i]
