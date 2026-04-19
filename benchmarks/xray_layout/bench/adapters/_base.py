"""Base adapter protocol and abstract class for layout engines.

Defines the contract that all layout adapters must implement. Adapters
wrap third-party layout libraries (e.g., Grandalf, igraph, pydot) and
provide a unified interface for benchmarking.

Budget conventions:
- 30-minute total budget for the entire benchmark suite
- 60-second timeout per individual layout operation
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

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
    """

    node_positions: dict
    edge_routes: dict
    runtime_ms: float
    node_sizes: dict


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

    def layout(self, graph: nx.MultiDiGraph) -> LayoutResult:
        """Compute a layout for the given graph.

        Must complete within the 60-second per-layout timeout.

        Args:
            graph: The graph to layout. Nodes have 'width' and 'height'
                attributes; edges may have additional metadata.

        Returns:
            LayoutResult containing node positions, edge routes, runtime,
            and node sizes.
        """
        ...

    def render(
        self, result: LayoutResult, graph: nx.MultiDiGraph, out_path: Path
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

    The 30-minute total budget and 60-second per-layout timeout are
    enforced by the benchmark runner, not individual adapters.
    """

    def __init__(self, name: str) -> None:
        """Initialize the adapter.

        Args:
            name: Human-readable adapter identifier (e.g., "grandalf").
        """
        self.name = name

    def build_payload(
        self,
        status: str,
        error_message: str | None = None,
        metrics: dict | None = None,
    ) -> dict:
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
        payload: dict = {
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
