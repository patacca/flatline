"""Sugiyama + libavoid baseline adapter (Baseline A).

Pipeline (independent from ogdf_libavoid_adapter, no cross-import):
    1. Convert NetworkX MultiDiGraph -> ogdf.Graph; we keep node handles for
       position read-back and edge handles keyed by (u, v, key) so we can map
       libavoid routes back to the original graph keys.
    2. Run ``ogdf.SugiyamaLayout`` (top-to-bottom by construction: the default
       OptimalRanking + FastHierarchyLayout combination places successor ranks
       below predecessors).  Sugiyama internally computes a feedback arc set
       via its ranking module (``OptimalRanking``/``LongestPathRanking``), so
       we do not need manual cycle reversal -- back-edges are routed through
       the standard hierarchical drawing with virtual nodes.
    3. Read centre positions from ``GraphAttributes.x/y`` and discard OGDF's
       edge bend polylines (libavoid will route).
    4. Build a libavoid orthogonal Router with ``apply_orthogonal_config``,
       register one ShapeRef per node, and attach side-specific
       ``ShapeConnectionPin``s:
          * sources: three pins on the bottom edge (BOTTOM = propY 1.0,
            ConnDirDown), classIDs 1/2/3 at propX 0.25/0.75/0.5 for
            true/false/default branches.
          * targets: one pin on the top edge (TOP = propY 0.0, ConnDirUp),
            classID 10 at propX 0.5 (centre).
       Note: the public adaptagrams binding has ``ATTACH_POS_TOP=0.0`` /
       ``ATTACH_POS_BOTTOM=1.0`` as plain float aliases for propY, NOT enum
       values for the ShapeConnectionPin direction argument.  The 6th
       constructor arg is a ``ConnDirFlags`` (``ConnDirUp``/``ConnDirDown``).
    5. For each non-self-loop edge, build a ``ConnRef`` whose endpoints are
       ``ConnEnd(shape, classID)`` -- the second arg form selects a specific
       pin by classID, which is what gives us the per-side anchoring.
    6. Self-loops (u == u) cannot be routed by libavoid (endpoints share a
       shape); we record an empty polyline for those edges so downstream
       metrics still see one entry per input edge but no geometry.

install_check() runs a tiny fixture that exercises self-loop, back-edge
(cycle), and true/false split, asserting the full pipeline succeeds.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from benchmarks.xray_layout.bench.adapters._base import BaseAdapter, LayoutResult
from benchmarks.xray_layout.bench.adapters._libavoid_config import apply_orthogonal_config

if TYPE_CHECKING:
    import networkx as nx


# Default node bounding box -- matches ogdf_adapter / ogdf_libavoid_adapter
# so cross-adapter renders sit at comparable scales.
_DEFAULT_NODE_WIDTH = 50.0
_DEFAULT_NODE_HEIGHT = 30.0

# Repo-relative path to the locally built OGDF tree.  Mirrors ogdf_adapter
# rather than importing it so this adapter remains standalone (per the
# T6 "no cross-adapter import" constraint).
_OGDF_BUILD_DIR = (
    Path(__file__).resolve().parents[2] / "third_party" / "ogdf" / "build"
)

# Pin classIDs.  Source-side IDs 1/2/3 line up with edge ``kind`` strings
# (true/false/default); target-side ID 10 is the single top-centre pin.
_PIN_TRUE = 1
_PIN_FALSE = 2
_PIN_DEFAULT = 3
_PIN_TARGET = 10

# propX positions for source-side pins on the bottom edge.  0.25 / 0.75
# split the bottom into thirds so true/false branches fan out naturally
# without overlapping the default centre pin at 0.5.
_PROPX_TRUE = 0.25
_PROPX_FALSE = 0.75
_PROPX_DEFAULT = 0.5
_PROPX_TARGET = 0.5

# ATTACH_POS_TOP/BOTTOM in adaptagrams are plain float aliases (0.0/1.0)
# for the propY argument; we hard-code them here for clarity rather than
# pulling them off the adaptagrams module at call sites.
_PROPY_TOP = 0.0
_PROPY_BOTTOM = 1.0


def _bootstrap_ogdf_env() -> None:
    """Set ``OGDF_BUILD_DIR`` and ``LD_LIBRARY_PATH`` for ogdf-python.

    Replicated from ogdf_adapter so this adapter stays self-contained --
    the task contract forbids cross-adapter imports.  Safe to call
    repeatedly; environment mutations are idempotent.
    """
    build_dir = str(_OGDF_BUILD_DIR)
    os.environ.setdefault("OGDF_BUILD_DIR", build_dir)
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    parts = existing.split(os.pathsep) if existing else []
    if build_dir not in parts:
        parts.insert(0, build_dir)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(parts)


def _kind_to_pin(kind: object) -> int:
    """Map an edge ``kind`` attribute to the source-side pin classID.

    Unknown / missing kinds fall back to the default centre pin so the
    adapter never crashes on graphs that lack branch annotations.
    """
    if kind == "true":
        return _PIN_TRUE
    if kind == "false":
        return _PIN_FALSE
    return _PIN_DEFAULT


class SugiyamaLibavoidAdapter(BaseAdapter):
    """Baseline A: OGDF Sugiyama placement + libavoid orthogonal routing.

    Distinguished from ``ogdf_libavoid`` (the existing combo adapter) by:
        * Hard pin to ``SugiyamaLayout`` -- no planarisation primary path.
        * Side-specific ShapeConnectionPin encoding so true/false branches
          leave the bottom of source nodes from distinct positions, and
          all incoming edges enter the top centre of target nodes.
    """

    name = "sugiyama_libavoid"

    def __init__(self) -> None:
        super().__init__(self.name)

    def install_check(self) -> tuple[bool, str]:
        """Probe both OGDF (ogdf_python) and libavoid (adaptagrams).

        We additionally run a tiny end-to-end fixture (self-loop +
        back-edge + true/false split) so the gate fails loudly if any
        of: SugiyamaLayout, ShapeConnectionPin, ConnEnd-by-classID, or
        the routing transaction is broken at runtime.  Returning a
        truthy result without exercising the pipeline once would let
        signature regressions (e.g. SWIG re-overloading the pin ctor)
        slip through to the benchmark runner.
        """
        # 1) OGDF availability (mirrors ogdf_adapter.install_check).
        if not _OGDF_BUILD_DIR.exists():
            return (False, f"ogdf_python: build dir not found at {_OGDF_BUILD_DIR}")
        _bootstrap_ogdf_env()
        try:
            import ogdf_python  # noqa: F401
        except Exception as exc:  # noqa: BLE001 - cppyy raises diverse types
            return (False, f"ogdf_python: {exc}")

        # 2) libavoid availability.
        try:
            import adaptagrams  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            return (False, f"adaptagrams: {exc}")

        # 3) End-to-end smoke run on a tiny fixture.  Built lazily so a
        # missing networkx dep surfaces here rather than at module load.
        try:
            import networkx as nx
            graph: nx.MultiDiGraph[Any] = nx.MultiDiGraph()
            for node_id in ("n0", "n1", "n2"):
                graph.add_node(node_id, width=_DEFAULT_NODE_WIDTH, height=_DEFAULT_NODE_HEIGHT)
            # Self-loop on n0 -- exercises the skip-but-record path.
            graph.add_edge("n0", "n0", kind="default")
            # True / false split out of n0 -- exercises pin classIDs 1+2.
            graph.add_edge("n0", "n1", kind="true")
            graph.add_edge("n0", "n2", kind="false")
            # Back-edge n2 -> n0 -- exercises Sugiyama's feedback-arc
            # handling (cycle preprocessing).
            graph.add_edge("n2", "n0", kind="default")

            result = self.layout(graph)
        except Exception as exc:  # noqa: BLE001 - report any pipeline error
            return (False, f"sugiyama_libavoid pipeline: {exc}")

        # Sanity: every input edge must appear in edge_routes (self-loop
        # included, possibly with empty polyline).
        if len(result.edge_routes) != graph.number_of_edges():
            return (
                False,
                f"sugiyama_libavoid pipeline: edge count mismatch "
                f"({len(result.edge_routes)} != {graph.number_of_edges()})",
            )
        return (True, f"ogdf_python + adaptagrams; smoke ok ({len(result.node_positions)} nodes)")

    def layout(self, graph: "nx.MultiDiGraph[Any]") -> LayoutResult:
        """Sugiyama placement -> libavoid pin-anchored orthogonal routing."""
        _bootstrap_ogdf_env()
        # Local imports keep module load cheap for ``bench check``.
        from ogdf_python import cppinclude, ogdf
        import adaptagrams as A  # type: ignore[import-not-found]

        cppinclude("ogdf/layered/SugiyamaLayout.h")

        # Stable node ordering so re-running the layout produces
        # bit-identical OGDF handles -- critical for reproducible metrics.
        ordered_nodes: list[object] = sorted(graph.nodes(), key=repr)

        # Per-node sizes, applied to OGDF and re-emitted in LayoutResult so
        # downstream metrics see the same dimensions Sugiyama saw.
        node_sizes: dict[object, tuple[float, float]] = {}
        for node_id in ordered_nodes:
            attrs = graph.nodes[node_id]
            width = float(attrs.get("width", _DEFAULT_NODE_WIDTH))
            height = float(attrs.get("height", _DEFAULT_NODE_HEIGHT))
            node_sizes[node_id] = (width, height)

        # ---- Step 1: Build OGDF graph ----
        g = ogdf.Graph()
        node_handles: dict[object, Any] = {}
        for node_id in ordered_nodes:
            node_handles[node_id] = g.newNode()
        edge_handles: dict[tuple[object, object, object], Any] = {}
        self_loops: list[tuple[object, object, object]] = []
        for source, target, key in graph.edges(keys=True):
            if source == target:
                # OGDF Sugiyama handles self-loops awkwardly (virtual node
                # spam); skip them at OGDF level and record at routing time.
                self_loops.append((source, target, key))
                continue
            edge_handles[(source, target, key)] = g.newEdge(
                node_handles[source], node_handles[target]
            )

        ga = ogdf.GraphAttributes(
            g,
            ogdf.GraphAttributes.nodeGraphics | ogdf.GraphAttributes.edgeGraphics,
        )
        ga.setAllWidth(_DEFAULT_NODE_WIDTH)
        ga.setAllHeight(_DEFAULT_NODE_HEIGHT)
        # Per-node size override via the array-form lvalue accessors.
        # The single-arg ga.width(node) returns a value copy in cppyy and
        # cannot be assigned to.  See ogdf_adapter for the same pattern.
        width_arr = ga.width()
        height_arr = ga.height()
        for node_id, (width, height) in node_sizes.items():
            handle = node_handles[node_id]
            width_arr[handle] = width
            height_arr[handle] = height

        # ---- Step 2: Sugiyama (top-to-bottom by construction) ----
        t0 = time.perf_counter()
        sugiyama = ogdf.SugiyamaLayout()
        # Detach from cppyy GC -- OGDF destructor ordering vs. interpreter
        # shutdown causes double-frees otherwise (documented in ogdf_adapter).
        sugiyama.__python_owns__ = False
        # SugiyamaLayout's default modules (OptimalRanking + BarycenterHeuristic
        # + FastHierarchyLayout) compute a feedback arc set internally to
        # break cycles; back-edges are drawn as virtual paths through ranks.
        # No manual cycle preprocessing required.
        sugiyama.call(ga)
        ogdf_runtime_ms = (time.perf_counter() - t0) * 1000.0

        # ---- Step 3: Extract node centres ----
        node_positions: dict[object, tuple[float, float]] = {}
        for node_id, handle in node_handles.items():
            node_positions[node_id] = (float(ga.x(handle)), float(ga.y(handle)))

        # ---- Step 4: libavoid router + shapes + side-specific pins ----
        router = A.Router(A.OrthogonalRouting)
        apply_orthogonal_config(router)
        rect_cls = getattr(A, "AvoidRectangle", None) or getattr(A, "Rectangle")

        shapes: dict[object, Any] = {}
        # Pin objects are intentionally retained on the adapter call frame
        # via this dict: libavoid takes ownership of the C++ pointer when
        # the pin is constructed against a ShapeRef, but holding a Python
        # reference avoids any premature swig-side proxy collection during
        # the routing transaction.
        pins: list[Any] = []
        for node_id, (cx, cy) in node_positions.items():
            width, height = node_sizes[node_id]
            half_w = width / 2.0
            half_h = height / 2.0
            rect = rect_cls(
                A.Point(cx - half_w, cy - half_h),
                A.Point(cx + half_w, cy + half_h),
            )
            shape = A.ShapeRef(router, rect)
            shapes[node_id] = shape

            # Source-side: three pins on the bottom edge (propY = 1.0,
            # ConnDirDown).  classID encodes branch semantics so the
            # routing engine can distinguish true/false/default per side.
            # We register all three on every node unconditionally; unused
            # pins cost a tiny amount of router state but keep the code
            # uniform and predictable.
            pins.append(A.ShapeConnectionPin(
                shape, _PIN_TRUE, _PROPX_TRUE, _PROPY_BOTTOM, 0.0, A.ConnDirDown
            ))
            pins.append(A.ShapeConnectionPin(
                shape, _PIN_FALSE, _PROPX_FALSE, _PROPY_BOTTOM, 0.0, A.ConnDirDown
            ))
            pins.append(A.ShapeConnectionPin(
                shape, _PIN_DEFAULT, _PROPX_DEFAULT, _PROPY_BOTTOM, 0.0, A.ConnDirDown
            ))
            # Target-side: single pin at top centre (propY = 0.0, ConnDirUp).
            pins.append(A.ShapeConnectionPin(
                shape, _PIN_TARGET, _PROPX_TARGET, _PROPY_TOP, 0.0, A.ConnDirUp
            ))

        # ---- Step 5: Connectors with classID-anchored ConnEnds ----
        connectors: dict[tuple[object, object, object], Any] = {}
        for source, target, key, data in graph.edges(keys=True, data=True):
            if source == target:
                # Already recorded; libavoid cannot route same-shape ends.
                continue
            src_pin = _kind_to_pin(data.get("kind"))
            # ConnEnd(ShapeRef, unsigned classID) selects a specific pin by
            # classID, which is exactly the side-anchoring we configured.
            src_end = A.ConnEnd(shapes[source], src_pin)
            tgt_end = A.ConnEnd(shapes[target], _PIN_TARGET)
            connectors[(source, target, key)] = A.ConnRef(router, src_end, tgt_end)

        # ---- Step 6: Route ----
        t1 = time.perf_counter()
        router.processTransaction()
        routing_ms = (time.perf_counter() - t1) * 1000.0

        # ---- Step 7: Harvest polylines ----
        edge_routes: dict[tuple[object, object, object], list[tuple[float, float]]] = {}
        for edge_id, conn in connectors.items():
            polyline = self._extract_polyline(conn)
            if polyline is None:
                # Hard fail per task contract: no polyline fallback.  If
                # libavoid declined a route, surface it as a layout error
                # rather than papering over with a straight segment.
                source, target, key = edge_id
                msg = (
                    f"libavoid produced no display route for edge "
                    f"({source!r} -> {target!r}, key={key!r})"
                )
                raise RuntimeError(msg)
            edge_routes[edge_id] = polyline

        # Self-loops: empty polyline so the edge appears in the result map
        # without inventing geometry.  Downstream metrics that iterate
        # routes must tolerate len(route) < 2 (libavoid_adapter does the
        # same when a connector has no displayable route).
        for edge_id in self_loops:
            edge_routes[edge_id] = []

        runtime_ms = ogdf_runtime_ms + routing_ms

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
        """Rasterise the layout to PNG via matplotlib (Agg backend).

        Mirrors the rendering convention of ogdf_libavoid_adapter so PNG
        diffs across baselines stay meaningful: filled rectangles for
        nodes, polylines for edges, equal aspect with inverted Y.
        """
        _ = graph  # all geometry already lives in ``result``
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt

        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not result.node_positions:
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

        canvas_width = max(4.0, min(20.0, (x_max - x_min) / 100.0))
        canvas_height = max(4.0, min(20.0, (y_max - y_min) / 100.0))

        fig, ax = plt.subplots(figsize=(canvas_width, canvas_height), dpi=120)
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_max, y_min)  # inverted Y: screen-style coordinates
        ax.set_aspect("equal")
        ax.axis("off")

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
        """Materialise a libavoid ConnRef's display route as Python tuples.

        Returns ``None`` if the route is missing or degenerate (<2 pts);
        the caller decides whether that is fatal or recoverable.
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
