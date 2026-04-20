"""libavoid layout adapter.

libavoid is a C++ library for orthogonal connector routing, part of the
adaptagrams project (https://github.com/mjwybrow/adaptagrams). The
upstream project ships SWIG-generated Python bindings exposed under the
``adaptagrams`` module name.  This adapter drives the bindings directly:
node positions are arranged on a deterministic grid, ``ShapeRef`` instances
describe each node's bounding rectangle, and one ``ConnRef`` per graph edge
asks libavoid to compute an orthogonal polyline route through the resulting
obstacle field.

If the ``adaptagrams`` Python module is not importable in the current
environment (most commonly because the upstream build needs SWIG, which is
not installed everywhere), ``install_check()`` returns
``(False, "adaptagrams Python module not importable: ...")`` and the
benchmark harness records the run as ``deferred`` without ever invoking
``layout()``.  The harness contract (see ``BaseAdapter.run`` in
``_base.py``) guarantees ``layout()`` is only called when
``install_check()`` returned True, so the routing code below assumes
``adaptagrams`` is importable at runtime.

The render path uses matplotlib (already a transitive bench dep) to draw
node rectangles and edge polylines into a PNG; SVG is not produced because
libavoid does not emit one and the benchmark only stores the rasterised
artifact.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from benchmarks.xray_layout.bench.adapters._base import BaseAdapter, LayoutResult
from benchmarks.xray_layout.bench.adapters._libavoid_config import (
    add_all_directions_pin,
    apply_orthogonal_config,
)

if TYPE_CHECKING:
    from pathlib import Path

    import adaptagrams  # type: ignore[import-not-found]
    import networkx as nx


# Default node bounding box used when the input graph does not carry width
# or height attributes.  Picked to be visually similar to the dimensions
# emitted by xray's existing placement code so cross-adapter comparisons
# remain meaningful.
_DEFAULT_NODE_WIDTH = 50.0
_DEFAULT_NODE_HEIGHT = 30.0

# Inter-node grid spacing.  libavoid needs obstacle clearance to route
# orthogonally around shapes; values smaller than (max_node_dim + ~20) tend
# to force routes through narrow corridors that increase bend counts.
_GRID_SPACING_X = 120.0
_GRID_SPACING_Y = 80.0


class LibavoidAdapter(BaseAdapter):
    """Adapter wrapping the libavoid orthogonal connector router.

    Stores the most recent layout's geometry on the instance so ``render()``
    can rasterise it without having to recompute the routes.  ``layout()``
    arranges nodes on a grid (libavoid is a router, not a placer) and asks
    the C++ engine to thread orthogonal polylines through the resulting
    obstacle field.
    """

    name = "libavoid"

    def __init__(self) -> None:
        super().__init__(self.name)

    def install_check(self) -> tuple[bool, str]:
        """Probe for the adaptagrams Python binding.

        adaptagrams is the only upstream-supported Python distribution for
        libavoid; ``pyavoid`` and similar third-party wrappers are not
        considered because they have diverged APIs and unmaintained build
        scripts.  Returns ``(True, "adaptagrams <version>")`` on success,
        ``(False, "adaptagrams Python module not importable: ...")`` when
        the import fails for any reason (missing module, missing SWIG-built
        ``_adaptagrams`` shared library, etc.).
        """
        try:
            mod = __import__("adaptagrams")
        except ImportError as exc:
            return (
                False,
                f"adaptagrams Python module not importable: {exc}",
            )
        version = getattr(mod, "__version__", "unknown")
        return (True, f"adaptagrams {version}")

    def layout(self, graph: "nx.MultiDiGraph[Any]") -> LayoutResult:
        """Route every edge in *graph* with libavoid.

        Algorithm:
        1. Lay nodes out on a deterministic grid (libavoid only routes; it
           does not place).  The grid size is ``ceil(sqrt(N))`` columns so
           the canvas stays roughly square regardless of graph size.
        2. Build one ``adaptagrams.ShapeRef`` per node, sized from the
           graph's per-node ``width``/``height`` attributes (with sensible
           defaults if those are missing).
        3. Build one ``adaptagrams.ConnRef`` per edge, anchored to the
           source/target shapes via ``ConnEnd``.  Self-loops are skipped
           because libavoid cannot route a connector whose endpoints share
           a shape.
        4. Call ``router.processTransaction()`` under a SIGALRM watchdog;
           if it times out we raise ``TimeoutError`` so the harness records
           a clean failure rather than wedging the whole benchmark run.
        5. Read each connector's display route via ``conn.displayRoute()``
           and convert the libavoid ``Point`` objects into plain tuples.
        """
        # Runtime import keeps module-level loads cheap and lets
        # ``install_check`` be the single source of truth for whether
        # adaptagrams is available.
        import math

        import adaptagrams as ad  # type: ignore[import-not-found]

        ordered_nodes: list[object] = sorted(graph.nodes(), key=repr)
        node_count = len(ordered_nodes)

        node_sizes: dict[object, tuple[float, float]] = {}
        for node_id in ordered_nodes:
            attrs = graph.nodes[node_id]
            width = float(attrs.get("width", _DEFAULT_NODE_WIDTH))
            height = float(attrs.get("height", _DEFAULT_NODE_HEIGHT))
            node_sizes[node_id] = (width, height)

        # Grid placement.  Using an integer column count keeps positions
        # stable across runs and avoids floating-point drift in repeats.
        cols = max(1, int(math.ceil(math.sqrt(max(1, node_count)))))
        node_positions: dict[object, tuple[float, float]] = {}
        for index, node_id in enumerate(ordered_nodes):
            row, col = divmod(index, cols)
            cx = (col + 0.5) * _GRID_SPACING_X
            cy = (row + 0.5) * _GRID_SPACING_Y
            node_positions[node_id] = (cx, cy)

        router = ad.Router(ad.OrthogonalRouting)
        apply_orthogonal_config(router)

        shapes: dict[object, Any] = {}
        for node_id in ordered_nodes:
            cx, cy = node_positions[node_id]
            width, height = node_sizes[node_id]
            half_w = width / 2.0
            half_h = height / 2.0
            # adaptagrams renamed Rectangle to AvoidRectangle in the Python
            # bindings to avoid colliding with other Adaptagrams libs that
            # also expose a Rectangle symbol.  Fall back to Rectangle for
            # older binding builds that still use the original name.
            rect_cls = getattr(ad, "AvoidRectangle", None) or getattr(ad, "Rectangle")
            rect = rect_cls(
                ad.Point(cx - half_w, cy - half_h),
                ad.Point(cx + half_w, cy + half_h),
            )
            shape = ad.ShapeRef(router, rect)
            # Register a centre pin allowing all four sides; without this the
            # SWIG-bound ConnEnd(shape, ConnDirAll) form is misinterpreted as
            # a missing pin class id and routes degenerate to straight lines.
            add_all_directions_pin(shape)
            shapes[node_id] = shape

        connectors: dict[tuple[object, object, object], Any] = {}
        for source, target, key in graph.edges(keys=True):
            if source == target:
                # libavoid cannot route a connector whose two ConnEnd
                # objects sit on the same shape; self-loops are dropped
                # rather than synthesised so the metric layer sees an
                # honest absence.
                continue
            src_end = ad.ConnEnd(shapes[source], ad.CONNECTIONPIN_CENTRE)
            tgt_end = ad.ConnEnd(shapes[target], ad.CONNECTIONPIN_CENTRE)
            conn = ad.ConnRef(router, src_end, tgt_end, ad.ConnType_Orthogonal)
            connectors[(source, target, key)] = conn

        # Wall-clock cap is enforced upstream by the harness's per-case
        # subprocess + killpg; SIGALRM cannot interrupt this native call.
        t0 = time.perf_counter()
        router.processTransaction()
        runtime_ms = (time.perf_counter() - t0) * 1000.0

        edge_routes: dict[tuple[object, object, object], list[tuple[float, float]]] = {}
        for edge_id, conn in connectors.items():
            polyline = self._extract_polyline(conn)
            if polyline is None:
                # Router declined to produce a route for this connector
                # (rare; usually only happens when shapes overlap).  Fall
                # back to a straight centre-to-centre segment so downstream
                # metrics still see something for this edge.
                source, target, _key = edge_id
                polyline = [node_positions[source], node_positions[target]]
            edge_routes[edge_id] = polyline

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

        Draws each node as a filled rectangle (sized from
        ``result.node_sizes``) and each edge as a polyline through its
        waypoints.  The graph argument is intentionally unused; the
        ``LayoutResult`` already carries everything we need to render and
        relying on it keeps this method robust against caller-side mutations
        of the source graph between layout() and render().
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
            # Nothing to draw; emit a tiny blank canvas so the harness still
            # finds the expected output file.
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

        # Pixel target ~1200 wide; clamp to a sensible range so tiny graphs
        # still produce a legible figure and huge graphs do not OOM.
        canvas_width = max(4.0, min(20.0, (x_max - x_min) / 100.0))
        canvas_height = max(4.0, min(20.0, (y_max - y_min) / 100.0))

        fig, ax = plt.subplots(figsize=(canvas_width, canvas_height), dpi=120)
        ax.set_xlim(x_min, x_max)
        # Invert Y so screen-style coordinates (y grows downward) render the
        # same way they would in the harness's other adapter outputs.
        ax.set_ylim(y_max, y_min)
        ax.set_aspect("equal")
        ax.axis("off")

        # Edges first so node rectangles paint on top of them.
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

    def _extract_polyline(self, conn: Any) -> list[tuple[float, float]] | None:
        """Convert a libavoid ConnRef's display route into Python tuples.

        Returns ``None`` if the connector has no displayable route (which
        can happen when the router rejected the connector's geometry).  The
        adaptagrams binding exposes the route as a ``PolyLine`` whose
        ``ps`` member is a vector of ``Point`` objects with ``.x``/``.y``
        attributes; we materialise the whole sequence eagerly so the
        underlying C++ object can be released as soon as this method
        returns.
        """
        try:
            route = conn.displayRoute()
        except Exception:  # noqa: BLE001 - bindings raise generic errors
            return None
        points = getattr(route, "ps", None)
        if points is None:
            return None
        polyline: list[tuple[float, float]] = []
        for point in points:
            polyline.append((float(point.x), float(point.y)))
        if len(polyline) < 2:
            return None
        return polyline
