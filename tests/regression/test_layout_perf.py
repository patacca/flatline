"""Latency budget guard for the layout/routing pipeline (T21)."""

from __future__ import annotations

from math import ceil
from time import perf_counter

import pytest

from flatline.xray._edge_routing import route_edges
from flatline.xray._layout import compute_layout
from tests.regression._layout_helpers import get_fixture, pcode_graph_for

_RUNS = 10
_PERF_FIXTURE_ID = "fx_switch_elf64"


def _percentile(samples: list[float], pct: float) -> float:
    index = max(0, ceil(len(samples) * pct) - 1)
    return sorted(samples)[index]


@pytest.mark.slow
def test_layout_perf_budget(native_runtime_data_dir: str) -> None:
    fixture = get_fixture(_PERF_FIXTURE_ID)
    pcode_graph = pcode_graph_for(fixture, native_runtime_data_dir)

    samples: list[float] = []
    for _ in range(_RUNS):
        start = perf_counter()
        layout = compute_layout(pcode_graph)
        route_edges(layout, pcode_graph)
        samples.append(perf_counter() - start)

    median = _percentile(samples, 0.5)
    p95 = _percentile(samples, 0.95)
    worst = max(samples)

    print(
        f"\n[layout_perf {_PERF_FIXTURE_ID}] runs={_RUNS} "
        f"median={median * 1000:.1f}ms p95={p95 * 1000:.1f}ms max={worst * 1000:.1f}ms"
    )

    assert median <= 0.200, f"median {median:.3f}s exceeds 200ms budget"
    assert p95 <= 1.000, f"p95 {p95:.3f}s exceeds 1s budget"
    assert worst <= 5.000, f"max {worst:.3f}s exceeds 5s budget"
