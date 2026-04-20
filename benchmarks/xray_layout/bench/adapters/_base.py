"""Base adapter protocol and abstract class for layout engines.

Defines the contract that all layout adapters must implement. Adapters
wrap third-party layout libraries (e.g., Grandalf, igraph, pydot) and
provide a unified interface for benchmarking.

Budget conventions:
- 30-minute total budget for the entire benchmark suite
- per-case timeout for individual layout operations (configurable, default 300s)
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    import networkx as nx


@dataclass(frozen=True)
class LayoutResult:
    """Result of a layout operation.

    Attributes:
        node_positions: Mapping from node ID to (x, y) coordinates.
        edge_routes: Mapping from edge ID to list of (x, y) waypoints.
        runtime_ms: Wall-clock time for layout computation in milliseconds.
        node_sizes: Mapping from node ID to (width, height) in pixels.
        error_class: Optional category tag set by adapters that hard-fail
            (instead of raising) when their strict contract rejects the
            input graph -- e.g. ``"non_planar"`` for Baseline B's
            PlanarizationLayout+OrthoLayout pipeline on K5.  ``None`` for
            successful runs.  Adapters that surface error_class typically
            return otherwise-empty position/route maps.
    """

    node_positions: dict[object, tuple[float, float]]
    edge_routes: dict[tuple[object, object, object], list[tuple[float, float]]]
    runtime_ms: float
    node_sizes: dict[object, tuple[float, float]]
    error_class: str | None = None


@runtime_checkable
class Adapter(Protocol):
    """Protocol for layout engine adapters.

    All adapters must implement this interface to participate in
    the benchmark suite.
    """

    name: str

    def install_check(self) -> tuple[bool, str]:
        """Check if the adapter's dependencies are available.

        Returns:
            A tuple of (is_available, message). If is_available is False,
            the message should explain why (e.g., missing library).
        """
        ...

    def layout(self, graph: "nx.MultiDiGraph[Any]") -> LayoutResult:
        """Compute a layout for the given graph.

        Must complete within the per-case layout timeout (configurable, default 300s).

        Args:
            graph: The graph to layout. Nodes have 'width' and 'height'
                attributes; edges may have additional metadata.

        Returns:
            LayoutResult containing node positions, edge routes, runtime,
            and node sizes.
        """
        ...

    def render(
        self,
        result: LayoutResult,
        graph: "nx.MultiDiGraph[Any]",
        out_path: Path,
    ) -> None:
        """Render the layout result to a file.

        Args:
            result: The layout result from layout().
            graph: The original graph (for edge/node metadata).
            out_path: Destination file path. Format inferred from suffix.
        """
        ...


class BaseAdapter(ABC):
    """Abstract base class for layout adapters.

    Provides common functionality for building benchmark payloads.
    Subclasses must implement the Adapter protocol methods.

    The 30-minute total budget and per-case layout timeout (configurable,
    default 300s) are enforced by the benchmark runner, not individual adapters.
    """

    def __init__(self, name: str) -> None:
        """Initialize the adapter.

        Args:
            name: Human-readable adapter identifier (e.g., "grandalf").
        """
        self.name = name

    @abstractmethod
    def install_check(self) -> tuple[bool, str]:
        """Check whether the adapter is runnable in the current environment."""

    @abstractmethod
    def layout(self, graph: "nx.MultiDiGraph[Any]") -> LayoutResult:
        """Compute a canonical layout result for the given graph."""

    @abstractmethod
    def render(
        self,
        result: LayoutResult,
        graph: "nx.MultiDiGraph[Any]",
        out_path: Path,
    ) -> None:
        """Render one layout result to the requested output path."""

    def build_payload(
        self,
        status: str,
        error_message: str | None = None,
        metrics: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Build a canonical-schema JSON payload for benchmark results.

        The payload follows the benchmark schema with candidate identifier,
        status, optional error message, and optional metrics.

        Args:
            status: Status string (e.g., "success", "timeout", "error").
            error_message: Optional error description for failed layouts.
            metrics: Optional dictionary of performance metrics.

        Returns:
            Dictionary ready for JSON serialization with keys:
            - candidate: Adapter name
            - binary: Empty string placeholder
            - function: Empty string placeholder
            - status: Status string
            - error_message: Optional error message
            - metrics: Optional metrics dict
        """
        payload: dict[str, Any] = {
            "candidate": self.name,
            "binary": "",
            "function": "",
            "status": status,
        }
        if error_message is not None:
            payload["error_message"] = error_message
        if metrics is not None:
            payload["metrics"] = metrics
        return payload

    def run(
        self,
        *,
        binary_path: Path,
        entry: str | None,
        budget_seconds: int,
        out_dir: Path,
    ) -> dict[str, Any]:
        """Execute one benchmark run and emit the canonical metrics JSON.

        The current CLI still writes a secondary copy of the returned record
        under ``out/runs``.  The benchmark plan, however, treats
        ``out/metrics/<binary>__<candidate>.json`` as the canonical artifact,
        so adapters write that file directly here.
        """
        from benchmarks.xray_layout.bench.graph_extract import extract
        from benchmarks.xray_layout.bench.metrics import compute

        binary_stem = binary_path.stem
        meta_path = self._resolve_meta_path(binary_path)
        ok, message = self.install_check()
        if not ok:
            record = self.build_payload("deferred", error_message=message)
            return self._finalize_record(
                record=record,
                binary_stem=binary_stem,
                entry=entry,
                out_dir=out_dir,
            )

        graph = extract(binary_path, meta_path)
        png_path = out_dir / "renders" / f"{binary_stem}__{self.name}.png"

        # Wall-clock budget is enforced by the harness via a per-case
        # subprocess + killpg; in-process SIGALRM cannot interrupt the
        # native C++ layout/routing calls below, so no inner cap is set.
        _ = budget_seconds
        result = self.layout(graph)

        # Strict-contract adapters (e.g. ogdf_planarization) signal a
        # rejected input by returning a LayoutResult with error_class set
        # and empty position/route maps. Treat that as a real failure --
        # otherwise the harness records status="ok" with all-zero metrics,
        # which both hides the failure in the executive summary AND gives
        # the candidate an artificially perfect composite score.
        if result.error_class is not None:
            self.render(result, graph, png_path)
            record = self.build_payload(
                "error",
                error_message=result.error_class,
            )
            record["outputs"] = {
                "png_path": str(png_path),
            }
            return self._finalize_record(
                record=record,
                binary_stem=binary_stem,
                entry=entry,
                out_dir=out_dir,
            )

        metrics = compute(result, graph)
        self.render(result, graph, png_path)

        record = self.build_payload(
            "ok",
            metrics=metrics,
        )
        record["outputs"] = {
            "png_path": str(png_path),
        }
        return self._finalize_record(
            record=record,
            binary_stem=binary_stem,
            entry=entry,
            out_dir=out_dir,
        )

    def _resolve_meta_path(self, binary_path: Path) -> Path:
        """Resolve the corpus metadata JSON paired with a built benchmark ELF."""
        meta_path = binary_path.with_suffix(".meta.json")
        if meta_path.exists():
            return meta_path
        msg = f"benchmark metadata not found for {binary_path} (expected {meta_path})"
        raise FileNotFoundError(msg)

    def _finalize_record(
        self,
        *,
        record: dict[str, Any],
        binary_stem: str,
        entry: str | None,
        out_dir: Path,
    ) -> dict[str, Any]:
        """Fill required schema fields, validate, and write canonical JSON."""
        from benchmarks.xray_layout.bench.schema import validate

        record["candidate"] = self.name
        record["binary"] = binary_stem
        record["function"] = entry or "<auto>"
        validate(record)

        metrics_dir = out_dir / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        metrics_path = metrics_dir / f"{binary_stem}__{self.name}.json"
        _ = metrics_path.write_text(
            json.dumps(record, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return record
