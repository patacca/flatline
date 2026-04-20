"""Baseline B adapter: OGDF PlanarizationLayout + OrthoLayout (STRICT).

This adapter implements **Baseline B** of the orthogonal-layout benchmark:
the pure planarisation+orthogonal-drawing pipeline with no degraded path.

Pipeline:

1. Build an ``ogdf.Graph`` mirroring the input ``networkx.MultiDiGraph``.
2. Run a Boyer-Myrvold planarity test (``ogdf.BoyerMyrvold().isPlanar``).
   Non-planar inputs are rejected immediately with
   ``LayoutResult(error_class="non_planar", ...)`` -- no degraded result is
   produced.
3. Construct ``PlanarizationLayout`` and explicitly install ``OrthoLayout``
   as its planar drawing module via ``setPlanarLayouter(...)``.
   ``OrthoLayout`` produces orthogonal routes with bend points natively, so
   we do not need a post-processing router (no libavoid here).
4. Read back node centres and edge bend points from ``GraphAttributes``;
   sandwich the bends between source/target centres to form a polyline per
   edge.

**Strict contract:** any failure of the orthogonal pipeline -- non-planar
input, OGDF-side exception during ``call(...)``, etc. -- is returned as a
``LayoutResult`` with the corresponding ``error_class`` (``"non_planar"`` or
``"ortho_failed"``).  No hierarchical degradation path exists here; that
behaviour lives in the companion ``ogdf_adapter.py`` baseline, which is the
orthogonal-or-degrade variant intended for the contrasting sensitivity arm.

Library bootstrap notes mirror ``ogdf_adapter.py``:

* ``OGDF_BUILD_DIR`` and ``LD_LIBRARY_PATH`` are set lazily before the first
  ``import ogdf_python`` so callers do not have to export anything.
* ``OrthoLayout`` is only on the ``ogdf`` namespace once
  ``install_ogdf_planarization.sh`` has patched ``ogdf_python``'s
  ``loader.py`` to pre-include ``ogdf/orthogonal/OrthoLayout.h``; that
  install script is the hard gate for this adapter.
* OGDF algorithm objects held from Python have ``__python_owns__ = False``
  set so cppyy does not try to free them on shutdown -- the same double-free
  trap documented at length in ``ogdf_adapter.py`` applies verbatim.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from benchmarks.xray_layout.bench.adapters._base import BaseAdapter, LayoutResult

if TYPE_CHECKING:
    import networkx as nx


# Default node bounding box size; matches ``ogdf_adapter.py`` so cross-adapter
# PNG renders sit at comparable scales.
_DEFAULT_NODE_WIDTH = 50.0
_DEFAULT_NODE_HEIGHT = 30.0

# Repo-relative path to the locally built OGDF source tree.  Same layout as
# ``ogdf_adapter._OGDF_BUILD_DIR`` -- duplicated rather than imported to keep
# this adapter independently understandable.
_OGDF_BUILD_DIR = (
    Path(__file__).resolve().parents[2] / "third_party" / "ogdf" / "build"
)


def _bootstrap_ogdf_env() -> None:
    """Set ``OGDF_BUILD_DIR`` and ``LD_LIBRARY_PATH`` for ogdf-python.

    Mirrors ``ogdf_adapter._bootstrap_ogdf_env``; see that module for the
    full rationale.  Must run before the first ``import ogdf_python`` in the
    interpreter session.
    """
    build_dir = str(_OGDF_BUILD_DIR)
    os.environ.setdefault("OGDF_BUILD_DIR", build_dir)
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    parts = existing.split(os.pathsep) if existing else []
    if build_dir not in parts:
        parts.insert(0, build_dir)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(parts)


class OgdfPlanarizationAdapter(BaseAdapter):
    """Strict PlanarizationLayout + OrthoLayout adapter (Baseline B).

    Hard-fails on non-planar input with ``error_class="non_planar"``; no
    hierarchical degradation is attempted.  The harness reads ``error_class``
    to bucket failures separately from successful orthogonal layouts.
    """

    name = "ogdf_planarization"

    def __init__(self) -> None:
        super().__init__(self.name)

    def install_check(self) -> tuple[bool, str]:
        """Probe ``ogdf_python`` and verify ``OrthoLayout`` + ``BoyerMyrvold``.

        On top of the usual ``ogdf_python`` import, this also runs two tiny
        end-to-end smoke graphs:

        1. A 4-node planar DAG is laid out with PlanarizationLayout +
           OrthoLayout; the call must succeed and emit at least one node
           position.  This catches the case where the loader patch worked
           but the actual layout pipeline is broken (missing C++ symbol,
           OrthoLayout API mismatch, etc.) before any real benchmark run.
        2. K5 (the canonical non-planar graph) is fed through the public
           ``layout()`` method; the adapter must return
           ``error_class="non_planar"`` -- not raise, not fall back.  This
           pins the strict contract from the install gate onward.
        """
        if not _OGDF_BUILD_DIR.exists():
            return (False, f"ogdf_planarization: OGDF build dir not found at {_OGDF_BUILD_DIR}")
        _bootstrap_ogdf_env()
        try:
            import ogdf_python  # noqa: F401  -- import-only smoke test
            from ogdf_python import cppinclude, ogdf
        except Exception as exc:  # noqa: BLE001 - cppyy raises diverse types
            return (False, f"ogdf_planarization: ogdf_python import failed: {exc}")

        # Make sure the symbols this adapter actually needs are reachable.
        # ``OrthoLayout`` requires the loader.py patch from
        # install_ogdf_planarization.sh; missing it is the most likely cause
        # of a failed install_check on a fresh venv.
        try:
            cppinclude("ogdf/planarity/PlanarizationLayout.h")
            cppinclude("ogdf/planarity/BoyerMyrvold.h")
        except Exception as exc:  # noqa: BLE001 - cppyy include failures vary
            return (False, f"ogdf_planarization: cppinclude failed: {exc}")
        for sym in ("PlanarizationLayout", "OrthoLayout", "BoyerMyrvold"):
            if not hasattr(ogdf, sym):
                return (
                    False,
                    f"ogdf_planarization: ogdf.{sym} missing -- run "
                    "benchmarks/xray_layout/bench/adapters/install_ogdf_planarization.sh",
                )

        # Smoke 1: a 4-node planar DAG should lay out cleanly.
        try:
            import networkx as nx
        except Exception as exc:  # noqa: BLE001
            return (False, f"ogdf_planarization: networkx import failed: {exc}")
        planar = nx.MultiDiGraph()
        planar.add_edges_from([(0, 1), (1, 2), (2, 3), (0, 3)])
        try:
            res_ok = self.layout(planar)
        except Exception as exc:  # noqa: BLE001 - smoke must surface as deferred
            return (False, f"ogdf_planarization: planar smoke crashed: {exc}")
        if res_ok.error_class is not None or not res_ok.node_positions:
            return (
                False,
                f"ogdf_planarization: planar smoke failed (error_class={res_ok.error_class!r}, "
                f"positions={len(res_ok.node_positions)})",
            )

        # Smoke 2: K5 must trip the strict non-planar branch.
        k5 = nx.complete_graph(5, create_using=nx.MultiDiGraph)
        try:
            res_k5 = self.layout(k5)
        except Exception as exc:  # noqa: BLE001
            return (False, f"ogdf_planarization: K5 smoke crashed: {exc}")
        if res_k5.error_class != "non_planar":
            return (
                False,
                f"ogdf_planarization: K5 smoke did not surface non_planar "
                f"(got error_class={res_k5.error_class!r})",
            )

        version = "unknown"
        try:
            import ogdf_python as _op  # noqa: PLC0415
            version = getattr(_op, "__version__", "unknown")
        except Exception:  # noqa: BLE001 - version is best-effort
            pass
        return (True, f"ogdf_planarization: ogdf_python {version} (OrthoLayout + BoyerMyrvold OK)")

    def layout(self, graph: "nx.MultiDiGraph[Any]") -> LayoutResult:
        """Lay out *graph* with PlanarizationLayout + OrthoLayout (strict).

        Returns a ``LayoutResult`` with ``error_class="non_planar"`` if
        Boyer-Myrvold rejects the input, or ``error_class="ortho_failed"``
        if OGDF raises during the actual layout call.  In both error paths
        the position/route maps are empty and ``runtime_ms`` reflects the
        time spent up to the failure -- matching the schema the harness
        expects from ``LayoutResult`` for failed-but-non-crashing runs.
        """
        _bootstrap_ogdf_env()
        # Local imports keep module load cheap when only ``install_check``
        # runs (e.g. ``bench check``).
        from ogdf_python import cppinclude, ogdf

        cppinclude("ogdf/planarity/PlanarizationLayout.h")
        cppinclude("ogdf/planarity/BoyerMyrvold.h")
        # OrthoLayout's header is pulled in by install_ogdf_planarization.sh's
        # patch to ogdf_python/loader.py; we still cppinclude it defensively
        # so direct adapter use without the venv patch surfaces a clear
        # AttributeError on ``ogdf.OrthoLayout`` rather than a crash deep in
        # ``setPlanarLayouter``.
        cppinclude("ogdf/orthogonal/OrthoLayout.h")

        ordered_nodes: list[object] = sorted(graph.nodes(), key=repr)

        # Per-node sizes feed both GraphAttributes and the returned
        # LayoutResult.node_sizes so the renderer sees the same dimensions
        # OGDF used internally.
        node_sizes: dict[object, tuple[float, float]] = {}
        for node_id in ordered_nodes:
            attrs = graph.nodes[node_id]
            width = float(attrs.get("width", _DEFAULT_NODE_WIDTH))
            height = float(attrs.get("height", _DEFAULT_NODE_HEIGHT))
            node_sizes[node_id] = (width, height)

        def _build() -> tuple[Any, Any, dict[object, Any], dict[tuple[object, object, object], Any]]:
            """Mirror the input nx graph into an OGDF Graph + GraphAttributes.

            Self-loops are skipped because OGDF's planarisation pipeline
            cannot route them; this matches ``ogdf_adapter._build`` so the
            two baselines exclude exactly the same edges.
            """
            g = ogdf.Graph()
            node_handles: dict[object, Any] = {}
            for node_id in ordered_nodes:
                node_handles[node_id] = g.newNode()
            edge_handles: dict[tuple[object, object, object], Any] = {}
            for source, target, key in graph.edges(keys=True):
                if source == target:
                    continue
                edge_handles[(source, target, key)] = g.newEdge(
                    node_handles[source], node_handles[target]
                )
            ga = ogdf.GraphAttributes(
                g,
                ogdf.GraphAttributes.nodeGraphics
                | ogdf.GraphAttributes.edgeGraphics,
            )
            ga.setAllWidth(_DEFAULT_NODE_WIDTH)
            ga.setAllHeight(_DEFAULT_NODE_HEIGHT)
            # Per-node sizes via the no-arg overloads; see the same comment
            # block in ogdf_adapter._build for why the single-arg form is
            # not usable as an lvalue under cppyy.
            width_arr = ga.width()
            height_arr = ga.height()
            for node_id, (width, height) in node_sizes.items():
                handle = node_handles[node_id]
                width_arr[handle] = width
                height_arr[handle] = height
            return g, ga, node_handles, edge_handles

        t0 = time.perf_counter()
        g, ga, node_handles, edge_handles = _build()

        # Strict gate 1: planarity test.  BoyerMyrvold.isPlanar takes the
        # raw ogdf::Graph and returns a bool -- we run it on a *copy* by
        # default behaviour (non-destructive overload), so the original
        # graph survives intact for the layout call below if planar.
        bm = ogdf.BoyerMyrvold()
        bm.__python_owns__ = False
        if not bm.isPlanar(g):
            runtime_ms = (time.perf_counter() - t0) * 1000.0
            return LayoutResult(
                node_positions={},
                edge_routes={},
                runtime_ms=runtime_ms,
                node_sizes=node_sizes,
                error_class="non_planar",
            )

        # Strict gate 2: PlanarizationLayout with OrthoLayout as the
        # explicit planar drawing module.  We do NOT catch a degradation
        # path here -- an OGDF-side exception is the contract's
        # "ortho_failed" bucket and is surfaced as such.
        try:
            pl = ogdf.PlanarizationLayout()
            pl.__python_owns__ = False
            ortho = ogdf.OrthoLayout()
            # ortho is owned by the PlanarizationLayout once handed off via
            # setPlanarLayouter -- detaching it from cppyy's GC matches the
            # ownership story used in ogdf_adapter for its algorithm objects.
            ortho.__python_owns__ = False
            pl.setPlanarLayouter(ortho)
            pl.call(ga)
        except Exception as exc:  # noqa: BLE001 - cppyy bubbles C++ types opaquely
            runtime_ms = (time.perf_counter() - t0) * 1000.0
            return LayoutResult(
                node_positions={},
                edge_routes={},
                runtime_ms=runtime_ms,
                node_sizes=node_sizes,
                error_class=f"ortho_failed: {type(exc).__name__}: {exc}",
            )
        runtime_ms = (time.perf_counter() - t0) * 1000.0

        # Read positions: OGDF stores node coordinates as bounding-box
        # centres, matching the convention used by every other adapter in
        # the suite.
        node_positions: dict[object, tuple[float, float]] = {}
        for node_id, handle in node_handles.items():
            node_positions[node_id] = (float(ga.x(handle)), float(ga.y(handle)))

        # Stitch edge polylines: GA.bends(edge) yields only interior bend
        # points; sandwich them between source/target centres so downstream
        # metrics see a complete polyline per edge -- OrthoLayout populates
        # bends natively, so this is the canonical orthogonal route.
        edge_routes: dict[tuple[object, object, object], list[tuple[float, float]]] = {}
        for edge_id, handle in edge_handles.items():
            source, target, _key = edge_id
            polyline: list[tuple[float, float]] = [node_positions[source]]
            try:
                bends = ga.bends(handle)
                for pt in bends:
                    polyline.append((float(pt.m_x), float(pt.m_y)))
            except Exception:  # noqa: BLE001 - per-edge defence, see ogdf_adapter
                pass
            polyline.append(node_positions[target])
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

        Mirrors ``ogdf_adapter.render`` so cross-adapter PNGs sit at the
        same visual scale.  When ``result.error_class`` is set (e.g.
        ``"non_planar"``) we emit a small placeholder PNG so the harness
        finds the artifact it expects on disk; the metrics record carries
        the actual failure information.
        """
        _ = graph  # all geometry needed already lives in result
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt

        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not result.node_positions:
            # Empty layout (typically from error_class=non_planar/ortho_failed):
            # write a placeholder so the harness output tree stays consistent.
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
        # Invert Y so screen-style coordinates match the other adapters.
        ax.set_ylim(y_max, y_min)
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
