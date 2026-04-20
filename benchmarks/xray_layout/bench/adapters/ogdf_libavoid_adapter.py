"""OGDF + libavoid combo layout adapter.

The combo strategy plays each engine to its strength: OGDF computes
node positions (its planarisation/Sugiyama pipelines produce mature,
well-spaced placements) and libavoid re-routes every edge as an
orthogonal polyline through those positions (its router is the
de-facto reference for orthogonal connector routing).

Pipeline:
    1. Delegate to ``OgdfAdapter.layout(graph)`` for node positions /
       sizes.  We discard OGDF's own edge polylines: they are the output
       of OGDF's bend-minimiser, but the whole point of this combo is
       that libavoid handles routing.
    2. Build one libavoid ``ShapeRef`` per node anchored at the OGDF
       position with the OGDF size.  Self-loops are skipped at the
       ConnRef stage (libavoid cannot route a connector whose endpoints
       share a shape) and back-filled with a degenerate 2-point route so
       downstream metrics still see an entry per edge.
    3. Run ``router.processTransaction()`` under a SIGALRM watchdog,
       matching the libavoid adapter's per-layout timeout policy.
    4. Extract ``conn.displayRoute()`` polylines and return a
       ``LayoutResult`` whose positions/sizes come from OGDF and whose
       edge routes come from libavoid.

``install_check()`` succeeds only when both component adapters are
runnable; failures are concatenated so the harness records the union of
missing dependencies.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from benchmarks.xray_layout.bench.adapters._base import BaseAdapter, LayoutResult
from benchmarks.xray_layout.bench.adapters._libavoid_config import apply_orthogonal_config
from benchmarks.xray_layout.bench.adapters.libavoid_adapter import LibavoidAdapter
from benchmarks.xray_layout.bench.adapters.ogdf_adapter import OgdfAdapter

if TYPE_CHECKING:
    from pathlib import Path

    import networkx as nx


# Default node bounding box used when OGDF returned a node without size
# data (defence in depth; OgdfAdapter currently always emits sizes).
_DEFAULT_NODE_WIDTH = 50.0
_DEFAULT_NODE_HEIGHT = 30.0


class OgdfLibavoidAdapter(BaseAdapter):
    """Combo adapter: OGDF places nodes, libavoid routes edges."""

    name = "ogdf_libavoid"

    def __init__(self) -> None:
        super().__init__(self.name)
        # Hold component adapter instances so install_check() and
        # layout() can delegate without re-importing the modules.
        self._ogdf = OgdfAdapter()
        self._libavoid = LibavoidAdapter()

    def install_check(self) -> tuple[bool, str]:
        """Both component engines must be installed for the combo to run."""
        ogdf_ok, ogdf_msg = self._ogdf.install_check()
        libavoid_ok, libavoid_msg = self._libavoid.install_check()
        if ogdf_ok and libavoid_ok:
            return (True, f"OGDF [{ogdf_msg}] + libavoid [{libavoid_msg}]")
        missing = []
        if not ogdf_ok:
            missing.append(f"ogdf({ogdf_msg})")
        if not libavoid_ok:
            missing.append(f"libavoid({libavoid_msg})")
        return (False, "; ".join(missing))

    def layout(self, graph: "nx.MultiDiGraph[Any]") -> LayoutResult:
        """Run OGDF for placement, then libavoid for orthogonal routing."""
        # Runtime import keeps module load cheap; install_check has
        # already proven the binding is importable when we reach here.
        import adaptagrams as ad  # type: ignore[import-not-found]

        # Step 1: OGDF placement.  Any error here propagates -- the combo
        # cannot run without node positions, and the harness contract
        # already wraps this call in time_budget().
        ogdf_result = self._ogdf.layout(graph)
        node_positions = dict(ogdf_result.node_positions)
        node_sizes: dict[object, tuple[float, float]] = {}
        for node_id in node_positions:
            width, height = ogdf_result.node_sizes.get(
                node_id, (_DEFAULT_NODE_WIDTH, _DEFAULT_NODE_HEIGHT)
            )
            node_sizes[node_id] = (float(width), float(height))

        # Step 2: build libavoid obstacle field anchored at OGDF positions.
        router = ad.Router(ad.OrthogonalRouting)
        apply_orthogonal_config(router)
        # adaptagrams renamed Rectangle to AvoidRectangle in newer
        # bindings (collision with other adaptagrams libs).  Fall back
        # to Rectangle for older builds.
        rect_cls = getattr(ad, "AvoidRectangle", None) or getattr(ad, "Rectangle")

        shapes: dict[object, Any] = {}
        for node_id, (cx, cy) in node_positions.items():
            width, height = node_sizes[node_id]
            half_w = width / 2.0
            half_h = height / 2.0
            rect = rect_cls(
                ad.Point(cx - half_w, cy - half_h),
                ad.Point(cx + half_w, cy + half_h),
            )
            shapes[node_id] = ad.ShapeRef(router, rect)

        # Step 3: connectors per edge.  Self-loops are skipped here; we
        # synthesise a degenerate 2-point route after routing so the
        # edge_routes dict still has one entry per input edge.
        connectors: dict[tuple[object, object, object], Any] = {}
        self_loops: list[tuple[object, object, object]] = []
        for source, target, key in graph.edges(keys=True):
            if source == target:
                self_loops.append((source, target, key))
                continue
            if source not in shapes or target not in shapes:
                # Defence: OGDF should have placed every node, but if a
                # node was dropped we cannot route an edge to it.  Skip
                # rather than crash; a straight fallback is added below.
                continue
            # ConnEnd REQUIRES the ConnDirAll second arg in current
            # adaptagrams bindings; calling ConnEnd(shape) alone raises
            # TypeError.  ConnDirAll = 15 lets libavoid pick any side.
            src_end = ad.ConnEnd(shapes[source], ad.ConnDirAll)
            tgt_end = ad.ConnEnd(shapes[target], ad.ConnDirAll)
            connectors[(source, target, key)] = ad.ConnRef(router, src_end, tgt_end)

        # Step 4: route. Wall-clock cap is enforced upstream by the
        # harness's per-case subprocess + killpg; SIGALRM cannot interrupt
        # this native call.
        t0 = time.perf_counter()
        router.processTransaction()
        routing_ms = (time.perf_counter() - t0) * 1000.0

        # Step 5: harvest routes.  Combo runtime is the sum of the two
        # engine timings so the metric reflects the full pipeline cost.
        edge_routes: dict[tuple[object, object, object], list[tuple[float, float]]] = {}
        for edge_id, conn in connectors.items():
            polyline = self._extract_polyline(conn)
            if polyline is None:
                # Router declined to produce a route; fall back to a
                # straight centre-to-centre segment so downstream metrics
                # still see something for this edge.
                source, target, _key = edge_id
                polyline = [node_positions[source], node_positions[target]]
            edge_routes[edge_id] = polyline

        # Self-loops: degenerate 2-point route at the node centre so the
        # metric layer sees the edge without any geometry surprises.
        for edge_id in self_loops:
            source, _target, _key = edge_id
            cx, cy = node_positions[source]
            edge_routes[edge_id] = [(cx, cy), (cx, cy)]

        runtime_ms = float(ogdf_result.runtime_ms) + routing_ms

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
        """Rasterise the combo layout to PNG using matplotlib.

        Mirrors ``libavoid_adapter.render`` so cross-adapter PNGs sit at
        the same visual scale: filled rectangles for nodes, polylines
        for edges, equal aspect ratio with an inverted Y axis.  The
        graph argument is intentionally unused; ``LayoutResult`` already
        carries every coordinate we need to render and relying on it
        keeps render() robust against caller-side mutations of the
        source graph between layout() and render().
        """
        _ = graph  # results carry all geometry we need
        # Local imports keep the module importable when matplotlib is
        # missing (e.g. during install_check probes that only need to
        # answer "is the binding importable?").
        import matplotlib

        matplotlib.use("Agg")  # ensure no DISPLAY-dependent backend kicks in
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt

        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not result.node_positions:
            # Nothing to draw; emit a tiny blank canvas so the harness
            # still finds the expected output file on disk.
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

        # Match the other adapters' canvas sizing so PNG diffs across
        # candidates remain meaningful.
        canvas_width = max(4.0, min(20.0, (x_max - x_min) / 100.0))
        canvas_height = max(4.0, min(20.0, (y_max - y_min) / 100.0))

        fig, ax = plt.subplots(figsize=(canvas_width, canvas_height), dpi=120)
        ax.set_xlim(x_min, x_max)
        # Invert Y so screen-style coordinates (y grows downward) match
        # the other adapters' rendering convention.
        ax.set_ylim(y_max, y_min)
        ax.set_aspect("equal")
        ax.axis("off")

        # Edges first so node rectangles paint on top of edge endpoints.
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
        can happen when the router rejected the connector's geometry).
        Materialises the whole sequence eagerly so the underlying C++
        object can be released as soon as this method returns.
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
