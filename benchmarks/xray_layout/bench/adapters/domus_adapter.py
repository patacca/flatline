"""DOMUS layout adapter.

DOMUS (https://github.com/shape-metrics/domus) is a SAT-based orthogonal
graph drawing tool published at GD2025. It has no Python bindings; the
adapter wraps the `domus` C++ executable via subprocess.

The adapter serialises the benchmark graph into DOMUS's ``graph.txt``
format, runs the standalone ``domus`` binary in a temporary working
directory, parses the emitted ``drawing.svg`` back into canonical node
centres and edge routes, and rasterises that SVG to PNG for the harness.
"""

from __future__ import annotations

import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING, Any

from benchmarks.xray_layout.bench.adapters._base import BaseAdapter, LayoutResult
from benchmarks.xray_layout.bench.render import svg_to_png

if TYPE_CHECKING:
    import networkx as nx


# Repo-relative path to the locally built DOMUS executable. The build
# step is documented in INSTALL_domus.md and is intentionally outside
# the bench venv since DOMUS is a standalone C++ tool, not a Python pkg.
_DOMUS_BIN = (
    Path(__file__).resolve().parents[2]
    / "third_party"
    / "domus"
    / "build"
    / "domus"
)


class DomusAdapter(BaseAdapter):
    """Adapter wrapping the DOMUS SAT-based orthogonal drawing tool."""

    name: str = "domus"

    def __init__(self) -> None:
        super().__init__(self.name)
        self._last_svg: str | None = None

    def install_check(self) -> tuple[bool, str]:
        """Probe for the locally built domus executable.

        DOMUS does not implement --help/--version; the binary expects a
        graph.txt in CWD and writes drawing.svg next to it. We therefore
        run it with no args and treat a non-zero exit (with the expected
        "cannot open: graph.txt" diagnostic on stdout) as proof that the
        binary is present and functional.
        """
        if not _DOMUS_BIN.exists():
            return (False, f"domus binary not found at {_DOMUS_BIN}")
        try:
            proc = subprocess.run(  # noqa: S603 - trusted local path
                [str(_DOMUS_BIN)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return (False, f"domus probe failed: {exc}")
        # Expected diagnostic confirms the binary executes and reaches
        # its file-loader without arguments.
        if "graph.txt" in (proc.stdout + proc.stderr):
            return (True, f"domus (local build) at {_DOMUS_BIN}")
        return (False, f"domus produced unexpected output: {proc.stdout!r}")

    def layout(self, graph: "nx.MultiDiGraph[Any]") -> LayoutResult:
        graph_txt, domus_to_original, undirected_pairs, skipped_edges = self._encode_graph(graph)

        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            graph_path = tmpdir / "graph.txt"
            _ = graph_path.write_text(graph_txt, encoding="utf-8")

            t0 = time.perf_counter()
            try:
                proc = subprocess.run(  # noqa: S603 - trusted local path
                    [str(_DOMUS_BIN)],
                    cwd=str(tmpdir),
                    capture_output=True,
                    text=True,
                    timeout=300,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError("DOMUS layout timed out after 60s") from exc
            runtime_ms = (time.perf_counter() - t0) * 1000.0

            svg_path = tmpdir / "drawing.svg"
            if svg_path.exists():
                svg_text = svg_path.read_text(encoding="utf-8")
            elif proc.returncode != 0:
                stderr = proc.stderr.strip() or proc.stdout.strip() or "unknown DOMUS failure"
                raise RuntimeError(f"DOMUS failed: {stderr}")
            else:
                raise RuntimeError("DOMUS did not produce drawing.svg")

        self._last_svg = svg_text
        node_positions, node_sizes, edge_routes = self._parse_svg(
            svg_text=svg_text,
            graph=graph,
            domus_to_original=domus_to_original,
            undirected_pairs=undirected_pairs,
        )
        if skipped_edges:
            # Keep the condition explicit for future adapter/run extensions that
            # may decide to surface this lossiness in the canonical payload.
            _ = skipped_edges
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
        _ = (result, graph)
        if self._last_svg is None:
            msg = "DOMUS render() requires a preceding layout() call that produced SVG"
            raise RuntimeError(msg)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".svg",
            encoding="utf-8",
            delete=False,
        ) as handle:
            _ = handle.write(self._last_svg)
            svg_path = Path(handle.name)
        try:
            svg_to_png(svg_path, out_path)
        finally:
            svg_path.unlink(missing_ok=True)

    def _encode_graph(
        self,
        graph: "nx.MultiDiGraph[Any]",
    ) -> tuple[str, dict[int, object], dict[tuple[int, int], tuple[object, object]], int]:
        """Serialise the directed multigraph into DOMUS's simple graph.txt.

        DOMUS consumes an undirected simple graph with integer node IDs.  We
        therefore:
        - renumber nodes to a stable 0..N-1 domain,
        - drop self-loops (DOMUS's undirected model cannot represent them), and
        - collapse parallel/directed duplicates to one undirected edge.

        DOMUS handles arbitrary node degree natively (see
        ``has_graph_degree_more_than_4`` and ``build_nodes_position_degree_more_than_4``
        in ``src/orthogonal/drawing_builder.cpp``); it routes edges incident to
        high-degree nodes through auxiliary "green/blue" port-expansion nodes.
        We therefore do NOT enforce a max-degree-4 cap on the encoded graph -
        doing so would partition real CFGs and trigger DOMUS's
        ``DisconnectedGraphError`` (see ``compute_cycle_basis`` assertion in
        ``src/core/graph/graphs_algorithms.cpp``), which the standalone
        ``domus`` executable does not catch and surfaces as an uncaught
        ``std::terminate``.

        DOMUS additionally requires the input to be connected; we verify this
        on the post-collapse undirected projection and raise a clear error if
        violated, instead of letting DOMUS abort.
        """
        # Local import: nx is type-hint-only at module level (TYPE_CHECKING),
        # but we need the runtime symbol here for the connectedness check.
        import networkx as nx

        ordered_nodes = sorted(graph.nodes(), key=repr)
        domus_ids = {node_id: index for index, node_id in enumerate(ordered_nodes)}
        domus_to_original = {index: node_id for node_id, index in domus_ids.items()}

        seen_pairs: set[tuple[object, object]] = set()
        encoded_pairs: list[tuple[object, object]] = []
        skipped_edges = 0

        for source, target, _key in graph.edges(keys=True):
            if source == target:
                # DOMUS's undirected simple-graph model has no self-loops.
                skipped_edges += 1
                continue

            pair = self._normalize_pair(source, target)
            if pair in seen_pairs:
                # Parallel and reverse-direction edges collapse to one
                # undirected edge in DOMUS's input format.
                continue

            seen_pairs.add(pair)
            encoded_pairs.append((source, target))

        # Verify connectedness on the post-collapse undirected projection.
        # CFGs from a single function are connected by construction (single
        # entry, every block reachable), so a failure here indicates an
        # upstream caller bug rather than a DOMUS limitation.
        undirected = nx.Graph()
        undirected.add_nodes_from(ordered_nodes)
        undirected.add_edges_from((source, target) for source, target in encoded_pairs)
        if undirected.number_of_nodes() > 0 and not nx.is_connected(undirected):
            num_components = nx.number_connected_components(undirected)
            msg = (
                f"DOMUS requires connected input but graph has {num_components} "
                f"connected components after parallel-edge collapse "
                f"({undirected.number_of_nodes()} nodes, "
                f"{undirected.number_of_edges()} edges)"
            )
            raise RuntimeError(msg)

        node_lines = ["nodes:", *[str(domus_ids[node_id]) for node_id in ordered_nodes]]
        edge_lines = [
            "edges:",
            *[
                f"{domus_ids[source]} {domus_ids[target]}"
                for source, target in encoded_pairs
            ],
        ]
        graph_txt = "\n".join([*node_lines, *edge_lines, ""])
        undirected_pairs = {
            self._normalize_int_pair(domus_ids[source], domus_ids[target]): (source, target)
            for source, target in encoded_pairs
        }
        return graph_txt, domus_to_original, undirected_pairs, skipped_edges

    def _parse_svg(
        self,
        *,
        svg_text: str,
        graph: "nx.MultiDiGraph[Any]",
        domus_to_original: dict[int, object],
        undirected_pairs: dict[tuple[int, int], tuple[object, object]],
    ) -> tuple[
        dict[object, tuple[float, float]],
        dict[object, tuple[float, float]],
        dict[tuple[object, object, object], list[tuple[float, float]]],
    ]:
        """Parse DOMUS SVG into canonical node centers and orthogonal polyline routes.

        DOMUS's ``make_svg`` (src/orthogonal/drawing.cpp:219) emits one ``<line>``
        per (node, neighbor) pair on the *augmented* graph - which contains
        bend-subdivision nodes added by the shape-metrics process and
        green/blue port-expansion nodes added for vertices with degree > 4.
        Bend/port nodes are not rendered as ``<rect>`` (only BLACK-coloured
        original nodes are), so each logical edge appears as a chain of two or
        more line segments threaded through invisible interior vertices.

        Reconstruction algorithm:
        1. Build a segment graph keyed by quantised endpoint coordinates.
        2. Identify "real" vertices = endpoints coinciding with rect centres.
        3. Walk each segment outward from a real vertex; at any non-real
           interior vertex of degree exactly 2 (a bend), follow through to the
           other neighbour; stop when we reach another real vertex.  Each walk
           yields one undirected polyline between two real vertices.
        4. Each undirected edge is emitted twice by DOMUS (once in each
           direction) so we deduplicate by normalised endpoint pair.
        """
        try:
            root = ET.fromstring(svg_text)
        except ET.ParseError as exc:
            snippet = svg_text[:240].replace("\n", " ")
            raise RuntimeError(f"Failed to parse DOMUS SVG: {snippet}") from exc

        ns = {"svg": "http://www.w3.org/2000/svg"}
        rects = [
            rect
            for rect in root.findall(".//svg:rect", ns)
            if not self._is_background_rect(rect)
        ]
        texts = []
        for text in root.findall(".//svg:text", ns):
            label = "".join(text.itertext()).strip()
            if not label:
                continue
            try:
                texts.append((int(label), text))
            except ValueError:
                continue

        if len(rects) != len(texts):
            msg = (
                f"DOMUS SVG node mismatch: {len(rects)} rects vs {len(texts)} labels"
            )
            raise RuntimeError(msg)

        node_positions: dict[object, tuple[float, float]] = {}
        node_sizes: dict[object, tuple[float, float]] = {}
        centers_by_domus_id: dict[int, tuple[float, float]] = {}

        for rect, (domus_id, _text) in zip(rects, texts, strict=True):
            original_id = domus_to_original.get(domus_id)
            if original_id is None:
                raise RuntimeError(f"DOMUS SVG referenced unknown node label {domus_id}")
            x = self._parse_float_attr(rect, "x")
            y = self._parse_float_attr(rect, "y")
            width = self._parse_float_attr(rect, "width")
            height = self._parse_float_attr(rect, "height")
            center = (x + (width / 2.0), y + (height / 2.0))
            centers_by_domus_id[domus_id] = center
            node_positions[original_id] = center
            node_sizes[original_id] = (width, height)

        pair_to_route = self._reconstruct_polylines(
            root=root,
            ns=ns,
            centers_by_domus_id=centers_by_domus_id,
        )

        edge_routes: dict[tuple[object, object, object], list[tuple[float, float]]] = {}
        for source, target, key in graph.edges(keys=True):
            if source == target:
                continue
            source_domus_id = self._lookup_domus_id(source, domus_to_original)
            target_domus_id = self._lookup_domus_id(target, domus_to_original)
            pair = self._normalize_int_pair(source_domus_id, target_domus_id)
            route = pair_to_route.get(pair)
            if route is None:
                continue

            first_domus_id = self._nearest_domus_node(route[0], centers_by_domus_id)
            if first_domus_id == source_domus_id:
                edge_routes[(source, target, key)] = list(route)
            else:
                edge_routes[(source, target, key)] = list(reversed(route))

        return node_positions, node_sizes, edge_routes

    def _reconstruct_polylines(
        self,
        *,
        root: ET.Element,
        ns: dict[str, str],
        centers_by_domus_id: dict[int, tuple[float, float]],
    ) -> dict[tuple[int, int], list[tuple[float, float]]]:
        """Reconstruct edge polylines from DOMUS's flat list of SVG segments.

        See ``_parse_svg`` docstring for the algorithm rationale.  Returns one
        polyline per undirected edge, keyed by the normalised pair of DOMUS
        node IDs at its endpoints.  The polyline endpoints are the rect-centre
        coordinates of the real nodes; interior points are the bend/port
        coordinates encountered during the walk.
        """
        # Quantisation tolerance: DOMUS prints SVG coordinates with ~3 decimal
        # digits, and port-expansion stubs sit ~3-4 px from their parent node.
        # 0.5 px is well below the smallest meaningful gap and well above
        # printf rounding error.
        quantum = 0.5

        def quantise(point: tuple[float, float]) -> tuple[int, int]:
            return (round(point[0] / quantum), round(point[1] / quantum))

        # Map each real-node centre to its quantised key.  Port-expansion
        # stubs (which sit a few pixels off the centre) hash to a different
        # bucket and are correctly treated as interior bend nodes.
        center_key_to_domus_id: dict[tuple[int, int], int] = {
            quantise(center): domus_id
            for domus_id, center in centers_by_domus_id.items()
        }

        # Build a multigraph of segments: vertex = quantised point; edge =
        # one SVG <line>.  We keep the original (unquantised) coordinates
        # alongside so reconstructed polylines preserve the float precision
        # DOMUS emitted (avoids drift when downstream metrics measure length).
        adjacency: dict[tuple[int, int], list[tuple[tuple[int, int], tuple[float, float]]]] = {}
        coord_by_key: dict[tuple[int, int], tuple[float, float]] = {}

        for line in root.findall(".//svg:line", ns):
            p1 = (self._parse_float_attr(line, "x1"), self._parse_float_attr(line, "y1"))
            p2 = (self._parse_float_attr(line, "x2"), self._parse_float_attr(line, "y2"))
            k1 = quantise(p1)
            k2 = quantise(p2)
            if k1 == k2:
                # Zero-length segment - DOMUS emits these for some degenerate
                # port stubs; skip to avoid self-loops in the segment graph.
                continue
            coord_by_key.setdefault(k1, p1)
            coord_by_key.setdefault(k2, p2)
            adjacency.setdefault(k1, []).append((k2, p2))
            adjacency.setdefault(k2, []).append((k1, p1))

        is_real: dict[tuple[int, int], bool] = {
            key: (key in center_key_to_domus_id) for key in adjacency
        }

        # Mark each segment as visited via an undirected key so the second
        # half of DOMUS's symmetric (a, b) + (b, a) emission is collapsed.
        visited_segments: set[frozenset[tuple[int, int]]] = set()
        pair_to_route: dict[tuple[int, int], list[tuple[float, float]]] = {}

        for start_key in list(adjacency.keys()):
            if not is_real.get(start_key, False):
                continue
            for next_key, next_coord in adjacency[start_key]:
                segment_id = frozenset((start_key, next_key))
                if segment_id in visited_segments:
                    continue
                polyline_keys, segments_consumed = self._walk_to_real_node(
                    start_key=start_key,
                    next_key=next_key,
                    next_coord=next_coord,
                    adjacency=adjacency,
                    is_real=is_real,
                )
                if polyline_keys is None:
                    # Walk hit an interior junction (degree != 2) before
                    # reaching another real node; mark the starting segment
                    # consumed so we don't loop forever, but skip recording.
                    visited_segments.add(segment_id)
                    continue
                visited_segments.update(segments_consumed)

                end_key = polyline_keys[-1]
                start_domus = center_key_to_domus_id[start_key]
                end_domus = center_key_to_domus_id[end_key]
                pair = self._normalize_int_pair(start_domus, end_domus)
                # Materialise float coordinates from the quantised key chain.
                # The starting endpoint comes from centers_by_domus_id (exact
                # rect-centre); interior + end points come from coord_by_key.
                polyline = [centers_by_domus_id[start_domus]]
                for key in polyline_keys[1:-1]:
                    polyline.append(coord_by_key[key])
                polyline.append(centers_by_domus_id[end_domus])
                pair_to_route.setdefault(pair, polyline)

        return pair_to_route

    def _walk_to_real_node(
        self,
        *,
        start_key: tuple[int, int],
        next_key: tuple[int, int],
        next_coord: tuple[float, float],
        adjacency: dict[tuple[int, int], list[tuple[tuple[int, int], tuple[float, float]]]],
        is_real: dict[tuple[int, int], bool],
    ) -> tuple[list[tuple[int, int]] | None, set[frozenset[tuple[int, int]]]]:
        """Follow a segment chain from ``start_key`` outward through bends.

        Returns ``(polyline_keys, consumed_segments)`` on success.  Returns
        ``(None, set())`` if the chain hits a non-real vertex with degree
        other than 2 (a true junction we cannot disambiguate).

        ``polyline_keys`` includes both endpoint keys; the first is
        ``start_key`` and the last is the next reached real-node key.
        """
        _ = next_coord  # coordinate is recovered from coord_by_key by caller
        polyline_keys: list[tuple[int, int]] = [start_key, next_key]
        consumed: set[frozenset[tuple[int, int]]] = {frozenset((start_key, next_key))}

        previous_key = start_key
        current_key = next_key
        # Hard cap on chain length to defend against pathological cycles in
        # malformed SVG; real polylines have at most a handful of bends.
        for _ in range(1024):
            if is_real.get(current_key, False):
                return polyline_keys, consumed
            neighbours = adjacency.get(current_key, [])
            if len(neighbours) != 2:
                return None, set()
            next_neighbour_key: tuple[int, int] | None = None
            for neighbour_key, _neighbour_coord in neighbours:
                if neighbour_key != previous_key:
                    next_neighbour_key = neighbour_key
                    break
            if next_neighbour_key is None:
                return None, set()
            consumed.add(frozenset((current_key, next_neighbour_key)))
            polyline_keys.append(next_neighbour_key)
            previous_key = current_key
            current_key = next_neighbour_key
        return None, set()

    def _is_background_rect(self, rect: ET.Element) -> bool:
        """Return True for DOMUS's canvas background rect."""
        return rect.attrib.get("fill", "").lower() == "white" and rect.attrib.get("x") == "0"

    def _nearest_domus_node(
        self,
        point: tuple[float, float],
        centers_by_domus_id: dict[int, tuple[float, float]],
    ) -> int:
        """Resolve a line endpoint back to the closest DOMUS node center."""
        if not centers_by_domus_id:
            raise RuntimeError("DOMUS SVG contained no node centers")
        return min(
            centers_by_domus_id,
            key=lambda domus_id: self._squared_distance(point, centers_by_domus_id[domus_id]),
        )

    def _lookup_domus_id(self, original_id: object, domus_to_original: dict[int, object]) -> int:
        """Find the DOMUS integer ID assigned to one original graph node."""
        for domus_id, mapped_original_id in domus_to_original.items():
            if mapped_original_id == original_id:
                return domus_id
        raise RuntimeError(f"DOMUS node ID lookup failed for {original_id!r}")

    def _parse_float_attr(self, element: ET.Element, name: str) -> float:
        """Read one required numeric SVG attribute."""
        raw = element.attrib.get(name)
        if raw is None:
            raise RuntimeError(f"DOMUS SVG element missing required attribute {name!r}")
        value = float(raw)
        if value != value:
            raise RuntimeError(
                "DOMUS produced NaN coordinates (likely linear graph with no cycles)"
            )
        return value

    def _normalize_pair(self, left: object, right: object) -> tuple[object, object]:
        """Build a deterministic undirected key for two arbitrary node IDs."""
        return (left, right) if repr(left) <= repr(right) else (right, left)

    def _normalize_int_pair(self, left: int, right: int) -> tuple[int, int]:
        """Build a deterministic undirected key for DOMUS integer IDs."""
        return (left, right) if left <= right else (right, left)

    def _squared_distance(
        self,
        left: tuple[float, float],
        right: tuple[float, float],
    ) -> float:
        """Compute squared Euclidean distance without importing math."""
        dx = left[0] - right[0]
        dy = left[1] - right[1]
        return (dx * dx) + (dy * dy)
