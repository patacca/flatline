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

import re
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from benchmarks.xray_layout.bench.adapters._base import BaseAdapter, LayoutResult
from benchmarks.xray_layout.bench.render import svg_to_png

if TYPE_CHECKING:
    import networkx as nx


class HolaAdapter(BaseAdapter):
    """Adapter wrapping the HOLA orthogonal layout via hola-graph."""

    name: str = "hola"

    def __init__(self) -> None:
        super().__init__(self.name)
        self._last_svg: str | None = None

    def install_check(self) -> tuple[bool, str]:
        """Probe for the hola-graph pybind11 wrapper."""
        try:
            import hola_graph
        except ImportError as exc:
            return (False, f"hola_graph: {exc}")
        version = getattr(hola_graph, "__version__", "unknown")
        return (True, f"hola_graph {version}")

    def layout(self, graph: "nx.MultiDiGraph[Any]") -> LayoutResult:
        from hola_graph import HolaGraph

        seeded_graph = self._seed_cluster_positions(graph)
        hg = HolaGraph.from_networkx(seeded_graph)

        t0 = time.perf_counter()
        hg.layout()
        runtime_ms = (time.perf_counter() - t0) * 1000.0

        svg_text = self._sanitize_svg(hg.to_svg())
        self._last_svg = svg_text

        node_positions: dict[object, tuple[float, float]] = {}
        node_sizes: dict[object, tuple[float, float]] = {}
        for node_id in graph.nodes():
            hola_node = hg.node(str(node_id))
            node_positions[node_id] = (float(hola_node.x), float(hola_node.y))
            node_sizes[node_id] = (float(hola_node.width), float(hola_node.height))

        raw_routes = self._extract_svg_routes(svg_text)
        edge_ids = list(graph.edges(keys=True))
        if len(raw_routes) != len(edge_ids):
            msg = (
                f"HOLA emitted {len(raw_routes)} SVG paths for {len(edge_ids)} graph edges; "
                "cannot build canonical edge_routes"
            )
            raise RuntimeError(msg)

        edge_routes = {
            edge_id: route for edge_id, route in zip(edge_ids, raw_routes, strict=True)
        }
        return LayoutResult(
            node_positions=node_positions,
            edge_routes=edge_routes,
            runtime_ms=runtime_ms,
            node_sizes=node_sizes,
        )

    def render(
        self,
        result: LayoutResult,
        graph: "nx.MultiDiGraph[Any]",
        out_path: Path,
    ) -> None:
        if self._last_svg is None:
            msg = "HOLA render() requires a preceding layout() call that produced SVG"
            raise RuntimeError(msg)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".svg",
            encoding="utf-8",
            delete=False,
        ) as handle:
            handle.write(self._last_svg)
            svg_path = Path(handle.name)
        try:
            svg_to_png(svg_path, out_path)
        finally:
            svg_path.unlink(missing_ok=True)

    def _seed_cluster_positions(
        self,
        graph: "nx.MultiDiGraph[Any]",
    ) -> "nx.MultiDiGraph[Any]":
        """Seed nodes so same-instruction groups start close together.

        hola_graph 0.1.5 exposes node positions but not explicit cluster
        constraints through its Python API.  We therefore seed the input graph
        with a deterministic grouped placement keyed on ``instruction_addr`` so
        HOLA starts from clustered instruction bands before refining the layout.
        """
        seeded = cast("nx.MultiDiGraph[Any]", graph.copy())

        groups: dict[object, list[object]] = {}
        singleton_index = 0
        for node_id, data in seeded.nodes(data=True):
            addr = data.get("instruction_addr")
            if addr is None:
                addr = ("singleton", singleton_index)
                singleton_index += 1
            groups.setdefault(addr, []).append(node_id)

        band_pitch = 80.0
        cluster_pitch = 30.0
        sorted_groups = sorted(groups.items(), key=lambda item: repr(item[0]))
        for band_index, (_, members) in enumerate(sorted_groups):
            y = float(band_index * band_pitch)
            start_x = -((len(members) - 1) * cluster_pitch) / 2.0
            for member_index, node_id in enumerate(sorted(members, key=repr)):
                x = start_x + member_index * cluster_pitch
                seeded.nodes[node_id]["pos"] = (float(x), y)
                seeded.nodes[node_id].setdefault("width", 20.0)
                seeded.nodes[node_id].setdefault("height", 20.0)
        return seeded

    def _sanitize_svg(self, svg_text: str) -> str:
        """Normalise HOLA's SVG so downstream rasterisers accept it."""
        return svg_text.replace("%%", "%")

    def _extract_svg_routes(self, svg_text: str) -> list[list[tuple[float, float]]]:
        """Parse polyline waypoints from HOLA's SVG <path d="..."> entries."""
        routes: list[list[tuple[float, float]]] = []
        path_data = re.findall(r'<path[^>]*\sd="([^"]+)"', svg_text)
        point_pattern = re.compile(r"[ML]\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)")
        for d_attr in path_data:
            route = [
                (float(x_str), float(y_str))
                for x_str, y_str in point_pattern.findall(d_attr)
            ]
            if len(route) >= 2:
                routes.append(route)
        return routes
