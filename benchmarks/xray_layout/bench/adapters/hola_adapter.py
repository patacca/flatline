"""HOLA layout adapter (Wave 1 stub).

HOLA (Human-like Orthogonal Layout Algorithm) is part of the adaptagrams
project. The `hola-graph` PyPI package is a pybind11 wrapper exposing
HolaGraph, HolaNode, HolaEdge from the upstream C++ implementation.

Wave 1 status: install gate succeeds (`hola-graph 0.1.5` installed in
the bench venv). The stub layout()/render() implementations return
trivial 2-node geometry; Wave 2 will translate the input MultiDiGraph
into a HolaGraph, run the layout, and project node positions back.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from benchmarks.xray_layout.bench.adapters._base import BaseAdapter, LayoutResult

if TYPE_CHECKING:
    from pathlib import Path

    import networkx as nx


class HolaAdapter(BaseAdapter):
    """Adapter wrapping the HOLA orthogonal layout via hola-graph."""

    name = "hola"

    def __init__(self) -> None:
        super().__init__(self.name)

    def install_check(self) -> tuple[bool, str]:
        """Probe for the hola-graph pybind11 wrapper."""
        try:
            import hola_graph
        except ImportError as exc:
            return (False, f"hola_graph: {exc}")
        version = getattr(hola_graph, "__version__", "unknown")
        return (True, f"hola_graph {version}")

    def layout(self, graph: nx.MultiDiGraph) -> LayoutResult:
        nodes = list(graph.nodes())[:2]
        positions = {n: (float(i * 10), 0.0) for i, n in enumerate(nodes)}
        sizes = {n: (4.0, 4.0) for n in nodes}
        return LayoutResult(
            node_positions=positions,
            edge_routes={},
            runtime_ms=0.0,
            node_sizes=sizes,
        )

    def render(
        self, result: LayoutResult, graph: nx.MultiDiGraph, out_path: Path
    ) -> None:
        from PIL import Image

        img = Image.new("RGB", (1, 1), color=(200, 200, 200))
        img.save(str(out_path))
