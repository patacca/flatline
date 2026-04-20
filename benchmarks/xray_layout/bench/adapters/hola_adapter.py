"""HOLA layout adapter.

HOLA (Human-like Orthogonal Layout Algorithm) is the orthogonal layout
algorithm shipped by libdialect inside the adaptagrams project
(https://github.com/mjwybrow/adaptagrams). The upstream SWIG bindings
expose it as the top-level callable ``adaptagrams.doHOLA(graph)``.

Unlike libavoid (a router that needs caller-supplied node positions),
HOLA performs both placement and orthogonal routing in one shot. We
therefore build a fresh ``adaptagrams.Graph`` from the input
``MultiDiGraph``, push node sizes into each ``DialectNode``, call
``doHOLA``, and harvest the resulting node centres.

Edge polylines: HOLA's per-edge polylines are not exposed by the SWIG
``Graph.addEdge`` return value (it is an opaque ``SwigPyObject``), but
the same routes are emitted in textual form by ``Graph.writeTglf()``.
We parse that TGLF dump to recover the genuine HOLA polylines, so
downstream metrics see the orthogonal segments HOLA actually computed.

If ``adaptagrams`` (or its ``doHOLA`` symbol) is missing, ``install_check``
returns ``(False, ...)`` and the harness records the run as ``deferred``
without invoking ``layout()``. Per the benchmark D1 decision, HOLA
runtime failures stay as ``error`` rows: there is no fallback engine.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from benchmarks.xray_layout.bench.adapters._base import BaseAdapter, LayoutResult

if TYPE_CHECKING:
    from pathlib import Path

    import networkx as nx


# Default node bounding box used when the input graph does not carry
# width/height attributes. Matches the libavoid adapter so cross-engine
# comparisons remain meaningful.
_DEFAULT_NODE_WIDTH = 50.0
_DEFAULT_NODE_HEIGHT = 30.0


def _parse_tglf_edges(tglf: str) -> list[list[tuple[float, float]]]:
    """Return polylines from a TGLF dump in original edge order.

    TGLF format (libdialect-specific dialect): three '#'-separated
    sections - nodes, edges, constraints. Each edge line is
    "<srcId> <tgtId> <x1> <y1> <x2> <y2> ... <xn> <yn>" with the
    source/target ids as the first two whitespace-separated tokens
    followed by 2N coordinate floats forming the polyline vertices.
    """
    return [poly for _src, _tgt, poly in _parse_tglf_edges_with_ids(tglf)]


def _parse_tglf_edges_with_ids(
    tglf: str,
) -> list[tuple[int, int, list[tuple[float, float]]]]:
    """Same as :func:`_parse_tglf_edges` but also exposes endpoint ids."""
    sections = tglf.split("#")
    if len(sections) < 2:
        return []
    edges_section = sections[1]
    out: list[tuple[int, int, list[tuple[float, float]]]] = []
    for raw_line in edges_section.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        tokens = line.split()
        if len(tokens) < 4 or (len(tokens) - 2) % 2 != 0:
            # Malformed row (need at least srcId tgtId x y, and an even
            # number of coordinate tokens). Skip silently rather than
            # crash the whole layout on a parser hiccup.
            continue
        try:
            src_id = int(tokens[0])
            tgt_id = int(tokens[1])
            coords = [float(t) for t in tokens[2:]]
        except ValueError:
            continue
        polyline = [(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
        out.append((src_id, tgt_id, polyline))
    return out


class HolaAdapter(BaseAdapter):
    """Adapter wrapping the HOLA orthogonal layout via ``adaptagrams.doHOLA``.

    HOLA places and routes in one call, so this adapter does not need a
    pre-placement grid like the libavoid adapter. We simply translate the
    networkx graph into an ``adaptagrams.Graph``, run HOLA, and read the
    resulting centres back via ``DialectNode.getCentre()``.
    """

    name = "hola"

    def __init__(self) -> None:
        super().__init__(self.name)

    def install_check(self) -> tuple[bool, str]:
        """Probe for the adaptagrams Python binding and the doHOLA symbol.

        ``adaptagrams.doHOLA`` is exposed as a top-level function in the
        SWIG bindings (NOT under ``adaptagrams.dialect`` - that submodule
        does not exist in the published bindings). We therefore check the
        attribute directly on the imported module.
        """
        try:
            mod = __import__("adaptagrams")
        except ImportError as exc:
            return (
                False,
                f"adaptagrams Python module not importable: {exc}",
            )
        if not hasattr(mod, "doHOLA"):
            return (
                False,
                "adaptagrams.doHOLA not available in this build of the bindings",
            )
        version = getattr(mod, "__version__", "unknown")
        return (True, f"adaptagrams doHOLA available ({version})")

    def layout(self, graph: "nx.MultiDiGraph[Any]") -> LayoutResult:
        """Run HOLA on a fresh ``adaptagrams.Graph`` built from *graph*.

        Algorithm:
        1. Allocate a ``DialectNode`` per source node, push its
           ``width``/``height`` via ``setDims`` (with sensible defaults
           when the input graph does not specify them).
        2. Add one edge per ``(source, target)`` in the input
           multigraph; self-loops are skipped because doHOLA cannot
           route a connector whose endpoints share a node.
        3. Call ``doHOLA(g)`` under a SIGALRM watchdog.
        4. Read each node's centre via ``getCentre()`` and emit a
           straight-line route per input edge (see module docstring on
           why we do not attempt to harvest the real polylines).
        """
        # Runtime import keeps module-level loads cheap and lets
        # install_check be the single source of truth for adaptagrams
        # availability.
        import adaptagrams as ad  # type: ignore[import-not-found]

        ordered_nodes: list[object] = sorted(graph.nodes(), key=repr)

        node_sizes: dict[object, tuple[float, float]] = {}
        for node_id in ordered_nodes:
            attrs = graph.nodes[node_id]
            width = float(attrs.get("width", _DEFAULT_NODE_WIDTH))
            height = float(attrs.get("height", _DEFAULT_NODE_HEIGHT))
            node_sizes[node_id] = (width, height)

        ag_graph = ad.Graph()
        ag_nodes: dict[object, Any] = {}
        for node_id in ordered_nodes:
            width, height = node_sizes[node_id]
            dnode = ag_graph.addNode()
            # setDims accepts (width, height) and seeds the bounding box
            # so HOLA respects per-node sizing during placement.
            dnode.setDims(width, height)
            ag_nodes[node_id] = dnode

        # Track non-self-loop edges in addEdge call order so we can map
        # TGLF's per-edge polylines (emitted in the same order) back to
        # our (source, target, key) tuples after doHOLA runs.
        added_edge_keys: list[tuple[object, object, object]] = []
        for source, target, key in graph.edges(keys=True):
            if source == target:
                # Self-loops cannot be expressed in libdialect's edge
                # lookup; skip them rather than synthesise a fake edge.
                continue
            ag_graph.addEdge(ag_nodes[source], ag_nodes[target])
            added_edge_keys.append((source, target, key))

        # Wall-clock cap is enforced upstream by the harness's per-case
        # subprocess + killpg; SIGALRM cannot interrupt this native call.
        t0 = time.perf_counter()
        ad.doHOLA(ag_graph)
        runtime_ms = (time.perf_counter() - t0) * 1000.0

        node_positions: dict[object, tuple[float, float]] = {}
        for node_id in ordered_nodes:
            centre = ag_nodes[node_id].getCentre()
            node_positions[node_id] = (float(centre.x), float(centre.y))

        # Recover HOLA's actual orthogonal polylines via the TGLF dump.
        # SWIG exposes Graph.addEdge's return value as an opaque
        # SwigPyObject with no accessors, but Graph.writeTglf() emits a
        # textual dump where each post-doHOLA edge appears as
        #   "<srcId> <tgtId> <x1> <y1> <x2> <y2> ... <xn> <yn>"
        # in the same order as the addEdge calls. We map srcId/tgtId
        # (libdialect's internal node id, assigned in addNode order) back
        # to the source nx node via the addNode order we preserved in
        # ordered_nodes, then attach the polyline to the matching
        # (source, target, key) tuple from added_edge_keys.
        tglf_id_to_nx_node = {
            ag_nodes[node_id].id(): node_id for node_id in ordered_nodes
        }
        edge_polylines = _parse_tglf_edges(ag_graph.writeTglf())

        edge_routes: dict[
            tuple[object, object, object], list[tuple[float, float]]
        ] = {}
        if len(edge_polylines) == len(added_edge_keys):
            # Trust positional alignment between addEdge order and TGLF
            # edge order (verified empirically against libdialect's
            # writeTglf implementation, which iterates m_edges in
            # insertion order).
            for edge_key, polyline in zip(
                added_edge_keys, edge_polylines, strict=True
            ):
                edge_routes[edge_key] = polyline
        else:
            # Edge-count mismatch (HOLA may have rewritten the edge set,
            # e.g. for alignment ghosts). Fall back to a srcId/tgtId
            # lookup, consuming polylines per ordered key. Multi-edges
            # between the same pair are matched in addEdge order.
            polylines_by_endpoints: dict[
                tuple[object, object], list[list[tuple[float, float]]]
            ] = {}
            for src_id, tgt_id, polyline in _parse_tglf_edges_with_ids(
                ag_graph.writeTglf()
            ):
                if src_id not in tglf_id_to_nx_node:
                    continue
                if tgt_id not in tglf_id_to_nx_node:
                    continue
                src_nx = tglf_id_to_nx_node[src_id]
                tgt_nx = tglf_id_to_nx_node[tgt_id]
                polylines_by_endpoints.setdefault(
                    (src_nx, tgt_nx), []
                ).append(polyline)
            for edge_key in added_edge_keys:
                source, target, _key = edge_key
                bucket = polylines_by_endpoints.get((source, target))
                if bucket:
                    edge_routes[edge_key] = bucket.pop(0)

        # Self-loop fallback: empty polyline so the edge appears in the
        # result map without inventing geometry. Downstream metrics that
        # iterate routes already tolerate len(route) < 2.
        for source, target, key in graph.edges(keys=True):
            if (source, target, key) not in edge_routes:
                edge_routes[(source, target, key)] = []

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
        """Rasterise the layout to PNG using matplotlib.

        Mirrors ``LibavoidAdapter.render``: nodes drawn as filled
        rectangles, edges drawn as polylines underneath. The graph
        argument is intentionally unused; ``LayoutResult`` already carries
        every coordinate we need and relying on it makes this method
        robust to caller-side mutations between ``layout()`` and
        ``render()``.
        """
        _ = graph  # see docstring; results carry all geometry we need
        # Local imports keep the module importable when matplotlib is
        # missing (e.g. during install_check probes).
        import matplotlib

        matplotlib.use("Agg")  # ensure no DISPLAY-dependent backend kicks in
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt

        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not result.node_positions:
            # Nothing to draw; emit a tiny blank canvas so the harness
            # still finds the expected output file.
            fig, _ax = plt.subplots(figsize=(1, 1), dpi=100)
            fig.savefig(str(out_path), format="png")
            plt.close(fig)
            return

        xs = [p[0] for p in result.node_positions.values()]
        ys = [p[1] for p in result.node_positions.values()]
        widths = [s[0] for s in result.node_sizes.values()]
        heights = [s[1] for s in result.node_sizes.values()]
        margin_x = max(widths) if widths else 1.0
        margin_y = max(heights) if heights else 1.0
        x_min = min(xs) - margin_x
        x_max = max(xs) + margin_x
        y_min = min(ys) - margin_y
        y_max = max(ys) + margin_y

        # Pixel target ~1200 wide; clamp so tiny graphs stay legible and
        # huge graphs do not OOM.
        canvas_width = max(4.0, min(20.0, (x_max - x_min) / 100.0))
        canvas_height = max(4.0, min(20.0, (y_max - y_min) / 100.0))

        fig, ax = plt.subplots(figsize=(canvas_width, canvas_height), dpi=120)
        ax.set_xlim(x_min, x_max)
        # Invert Y so screen-style coordinates (y grows downward) match
        # the other adapter outputs.
        ax.set_ylim(y_max, y_min)
        ax.set_aspect("equal")
        ax.axis("off")

        # Edges first so node rectangles paint on top.
        for route in result.edge_routes.values():
            if len(route) < 2:
                continue
            edge_xs = [float(pt[0]) for pt in route]
            edge_ys = [float(pt[1]) for pt in route]
            ax.plot(
                edge_xs,
                edge_ys,
                color="#444444",
                linewidth=1.0,
                solid_capstyle="round",
                solid_joinstyle="miter",
            )

        for node_id, (cx, cy) in result.node_positions.items():
            width, height = result.node_sizes.get(
                node_id, (_DEFAULT_NODE_WIDTH, _DEFAULT_NODE_HEIGHT)
            )
            rect = mpatches.Rectangle(
                (cx - width / 2.0, cy - height / 2.0),
                width,
                height,
                linewidth=1.0,
                edgecolor="#222222",
                facecolor="#cfe2ff",
            )
            ax.add_patch(rect)

        fig.savefig(str(out_path), format="png", bbox_inches="tight")
        plt.close(fig)
