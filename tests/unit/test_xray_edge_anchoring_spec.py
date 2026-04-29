from __future__ import annotations

import pytest

from flatline.xray._edge_anchoring import anchor_polyline_endpoints
from flatline.xray._layout import Position

pytestmark = pytest.mark.unit


def test_short_polyline_returned_unchanged() -> None:
    src = Position(x=100.0, y=100.0, w=40.0, h=20.0)
    tgt = Position(x=300.0, y=300.0, w=40.0, h=20.0)
    for axis in ("vertical", "horizontal"):
        assert anchor_polyline_endpoints([], src, tgt, axis=axis) == []
        assert anchor_polyline_endpoints([(100.0, 100.0)], src, tgt, axis=axis) == [(100.0, 100.0)]


def test_vertical_axis_clips_to_bottom_top() -> None:
    src = Position(x=100.0, y=100.0, w=40.0, h=20.0)
    tgt = Position(x=300.0, y=300.0, w=40.0, h=20.0)
    poly = [(105.0, 105.0), (200.0, 200.0), (305.0, 305.0)]
    result = anchor_polyline_endpoints(poly, src, tgt, axis="vertical")
    assert result[0][1] == 110.0
    assert result[-1][1] == 290.0


def test_vertical_axis_inserts_bend_when_libavoid_exits_sideways() -> None:
    src = Position(x=100.0, y=100.0, w=40.0, h=20.0)
    tgt = Position(x=300.0, y=300.0, w=40.0, h=20.0)
    poly = [(105.0, 105.0), (50.0, 50.0), (305.0, 305.0)]
    result = anchor_polyline_endpoints(poly, src, tgt, axis="vertical")
    # First segment must be vertical after anchoring.
    assert result[0] == (105.0, 110.0)
    assert result[1] == (105.0, 50.0)
    assert result[2] == (50.0, 50.0)


def test_vertical_axis_inserts_bend_at_target() -> None:
    src = Position(x=100.0, y=100.0, w=40.0, h=20.0)
    tgt = Position(x=300.0, y=300.0, w=40.0, h=20.0)
    poly = [(105.0, 105.0), (350.0, 350.0), (305.0, 305.0)]
    result = anchor_polyline_endpoints(poly, src, tgt, axis="vertical")
    # Last segment must be vertical before the target.
    assert result[-1] == (305.0, 290.0)
    assert result[-2] == (305.0, 350.0)


def test_vertical_axis_no_bend_when_already_vertical() -> None:
    src = Position(x=100.0, y=100.0, w=40.0, h=20.0)
    tgt = Position(x=300.0, y=300.0, w=40.0, h=20.0)
    poly = [(105.0, 105.0), (105.0, 50.0), (305.0, 50.0), (305.0, 305.0)]
    result = anchor_polyline_endpoints(poly, src, tgt, axis="vertical")
    assert len(result) == 4
    assert result[1] == (105.0, 50.0)
    assert result[2] == (305.0, 50.0)


def test_horizontal_axis_clips_to_sides_when_target_right_of_source() -> None:
    src = Position(x=100.0, y=100.0, w=40.0, h=20.0)
    tgt = Position(x=300.0, y=100.0, w=40.0, h=20.0)
    poly = [(110.0, 105.0), (200.0, 100.0), (290.0, 105.0)]
    result = anchor_polyline_endpoints(poly, src, tgt, axis="horizontal")
    assert result[0][0] == 120.0
    assert result[-1][0] == 280.0


def test_horizontal_axis_clips_to_sides_when_target_left_of_source() -> None:
    src = Position(x=300.0, y=100.0, w=40.0, h=20.0)
    tgt = Position(x=100.0, y=100.0, w=40.0, h=20.0)
    poly = [(290.0, 105.0), (200.0, 100.0), (110.0, 105.0)]
    result = anchor_polyline_endpoints(poly, src, tgt, axis="horizontal")
    assert result[0][0] == 280.0
    assert result[-1][0] == 120.0


def test_horizontal_axis_inserts_bend_when_libavoid_exits_top_or_bottom() -> None:
    src = Position(x=100.0, y=100.0, w=40.0, h=20.0)
    tgt = Position(x=300.0, y=100.0, w=40.0, h=20.0)
    poly = [(110.0, 105.0), (50.0, 50.0), (290.0, 105.0)]
    result = anchor_polyline_endpoints(poly, src, tgt, axis="horizontal")
    # First segment must be horizontal after anchoring.
    assert result[0] == (120.0, 105.0)
    assert result[1] == (50.0, 105.0)
    assert result[2] == (50.0, 50.0)


def test_horizontal_axis_no_stub_when_already_horizontal() -> None:
    src = Position(x=100.0, y=100.0, w=40.0, h=20.0)
    tgt = Position(x=300.0, y=100.0, w=40.0, h=20.0)
    poly = [(110.0, 105.0), (200.0, 105.0), (290.0, 105.0)]
    result = anchor_polyline_endpoints(poly, src, tgt, axis="horizontal")
    assert len(result) == 3
    assert result[1] == (200.0, 105.0)


def test_invalid_axis_raises() -> None:
    src = Position(x=100.0, y=100.0, w=40.0, h=20.0)
    tgt = Position(x=300.0, y=300.0, w=40.0, h=20.0)
    with pytest.raises(
        ValueError, match="Unknown axis 'diagonal'; expected 'vertical' or 'horizontal'"
    ):
        anchor_polyline_endpoints([(0.0, 0.0), (1.0, 1.0)], src, tgt, axis="diagonal")


def test_interior_waypoints_preserved() -> None:
    src = Position(x=100.0, y=100.0, w=40.0, h=20.0)
    tgt = Position(x=300.0, y=300.0, w=40.0, h=20.0)
    poly = [
        (100.0, 100.0),
        (100.0, 150.0),
        (200.0, 200.0),
        (300.0, 250.0),
        (300.0, 300.0),
    ]
    result = anchor_polyline_endpoints(poly, src, tgt, axis="vertical")
    assert result[2] == (200.0, 200.0)
