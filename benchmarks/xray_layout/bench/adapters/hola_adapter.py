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

Edge polylines: the SWIG bindings expose libdialect's edge-lookup
container as an opaque ``SwigPyObject``, so reaching into the routed
polylines from Python is not supported by upstream. We therefore use
straight-line centre-to-centre routes for every edge - that keeps the
metric layer fed without claiming routing fidelity we cannot verify.

If ``adaptagrams`` (or its ``doHOLA`` symbol) is missing, ``install_check``
returns ``(False, ...)`` and the harness records the run as ``deferred``
without invoking ``layout()``. Per the benchmark D1 decision, HOLA
runtime failures stay as ``error`` rows: there is no fallback engine.
"""

from __future__ import annotations

import signal
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

# Hard wall-clock cap for ``adaptagrams.doHOLA``. Mirrors the 60-second
# per-layout budget enforced by ``BaseAdapter.run`` so we surface a clean
# TimeoutError before the harness's outer SIGALRM fires.
_LAYOUT_TIMEOUT_SECONDS = 60


class _LayoutTimeout(Exception):
    """Raised by the SIGALRM handler when doHOLA exceeds the budget."""


def _alarm_handler(signum: int, frame: object) -> None:
    """SIGALRM handler that converts the timeout into a Python exception.

    Using ``signal.alarm`` (rather than a watchdog thread) keeps the
    timeout cheap and avoids the GIL pitfalls of trying to interrupt a
    blocking C++ call from another thread. doHOLA runs synchronously on
    the main thread so the signal is delivered as soon as control returns
    to the Python interpreter loop.
    """
    _ = (signum, frame)
    raise _LayoutTimeout(
        f"adaptagrams.doHOLA exceeded {_LAYOUT_TIMEOUT_SECONDS}s"
    )


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

        for source, target, _key in graph.edges(keys=True):
            if source == target:
                # Self-loops cannot be expressed in libdialect's edge
                # lookup; skip them rather than synthesise a fake edge.
                continue
            ag_graph.addEdge(ag_nodes[source], ag_nodes[target])

        # Wrap the C++ call in a SIGALRM watchdog. Restore the previous
        # handler in finally so we never leak signal state into the
        # caller (the harness installs its own outer time_budget).
        previous_handler = signal.signal(signal.SIGALRM, _alarm_handler)
        signal.alarm(_LAYOUT_TIMEOUT_SECONDS)
        t0 = time.perf_counter()
        try:
            ad.doHOLA(ag_graph)
        except _LayoutTimeout as exc:
            raise TimeoutError(str(exc)) from exc
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous_handler)
        runtime_ms = (time.perf_counter() - t0) * 1000.0

        node_positions: dict[object, tuple[float, float]] = {}
        for node_id in ordered_nodes:
            centre = ag_nodes[node_id].getCentre()
            node_positions[node_id] = (float(centre.x), float(centre.y))

        # Straight-line edge routes. SWIG exposes the routed-edge lookup
        # as an opaque SwigPyObject we cannot iterate from Python, so we
        # synthesise centre-to-centre polylines. Self-loops get a
        # degenerate two-point route at the node centre so downstream
        # metrics still see an entry per input edge.
        edge_routes: dict[
            tuple[object, object, object], list[tuple[float, float]]
        ] = {}
        for source, target, key in graph.edges(keys=True):
            src_centre = node_positions[source]
            tgt_centre = node_positions[target]
            edge_routes[(source, target, key)] = [src_centre, tgt_centre]

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
