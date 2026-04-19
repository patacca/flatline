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
                    timeout=60,
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
        - collapse parallel/directed duplicates to one undirected edge, and
        - enforce DOMUS's max-degree-4 constraint by dropping excess edges.
        """
        ordered_nodes = sorted(graph.nodes(), key=repr)
        domus_ids = {node_id: index for index, node_id in enumerate(ordered_nodes)}
        domus_to_original = {index: node_id for node_id, index in domus_ids.items()}

        degree_by_node = {node_id: 0 for node_id in ordered_nodes}
        seen_pairs: set[tuple[object, object]] = set()
        encoded_pairs: list[tuple[object, object]] = []
        skipped_edges = 0

        for source, target, _key in graph.edges(keys=True):
            if source == target:
                skipped_edges += 1
                continue

            pair = self._normalize_pair(source, target)
            if pair in seen_pairs:
                continue
            if degree_by_node[source] >= 4 or degree_by_node[target] >= 4:
                skipped_edges += 1
                continue

            seen_pairs.add(pair)
            degree_by_node[source] += 1
            degree_by_node[target] += 1
            encoded_pairs.append((source, target))

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
        """Parse DOMUS SVG into canonical node centers and straight edge routes."""
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

        pair_to_route: dict[tuple[int, int], list[tuple[float, float]]] = {}
        for line in root.findall(".//svg:line", ns):
            x1 = self._parse_float_attr(line, "x1")
            y1 = self._parse_float_attr(line, "y1")
            x2 = self._parse_float_attr(line, "x2")
            y2 = self._parse_float_attr(line, "y2")
            start = (x1, y1)
            end = (x2, y2)
            start_domus_id = self._nearest_domus_node(start, centers_by_domus_id)
            end_domus_id = self._nearest_domus_node(end, centers_by_domus_id)
            pair = self._normalize_int_pair(start_domus_id, end_domus_id)
            pair_to_route[pair] = [start, end]

        if len(pair_to_route) != len(undirected_pairs):
            msg = (
                f"DOMUS emitted {len(pair_to_route)} edge lines for "
                f"{len(undirected_pairs)} encoded edges"
            )
            raise RuntimeError(msg)

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
            second_domus_id = self._nearest_domus_node(route[1], centers_by_domus_id)
            if first_domus_id == source_domus_id and second_domus_id == target_domus_id:
                edge_routes[(source, target, key)] = route
            else:
                edge_routes[(source, target, key)] = [route[1], route[0]]

        return node_positions, node_sizes, edge_routes

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
