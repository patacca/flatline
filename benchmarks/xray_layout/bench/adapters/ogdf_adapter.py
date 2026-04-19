"""OGDF layout adapter (Wave 1 stub).

OGDF is the Open Graph Drawing Framework (https://ogdf.uos.de/), a C++
library with extensive orthogonal layout support. The `ogdf-python`
package wraps it via cppyy; however it requires the OGDF and COIN-OR
shared libraries to be installed system-wide (see INSTALL_ogdf.md for
the deferred system-build plan).

Wave 1 status: ogdf-python wheel installed but import fails because
`libCOIN`/`libOGDF` are absent. install_check() therefore reports
DEFERRED until those system libraries ship. Stub layout()/render()
return trivial 2-node geometry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from benchmarks.xray_layout.bench.adapters._base import BaseAdapter, LayoutResult

if TYPE_CHECKING:
    from pathlib import Path

    import networkx as nx


class OgdfAdapter(BaseAdapter):
    """Adapter wrapping OGDF orthogonal layouts via ogdf-python (cppyy)."""

    name = "ogdf"

    def __init__(self) -> None:
        super().__init__(self.name)

    def install_check(self) -> tuple[bool, str]:
        """Probe for the ogdf_python cppyy wrapper.

        The wrapper attempts to dlopen libCOIN and libOGDF on import; if
        either is missing the import itself raises ImportError.
        """
        try:
            import ogdf_python
        except ImportError as exc:
            return (False, f"ogdf_python: {exc}")
        version = getattr(ogdf_python, "__version__", "unknown")
        return (True, f"ogdf_python {version}")

    def layout(self, graph: nx.MultiDiGraph) -> LayoutResult:
        nodes = list(graph.nodes())[:2]
        positions = {n: (float(i * 10), 0.0) for i, n in enumerate(nodes)}
        sizes = {n: (4.0, 4.0) for n in nodes}
        return LayoutResult(
            node_positions=positions,
            edge_routes={},
            runtime_ms=0.0,
            node_sizes=sizes,
        )

    def render(
        self, result: LayoutResult, graph: nx.MultiDiGraph, out_path: Path
    ) -> None:
        from PIL import Image

        img = Image.new("RGB", (1, 1), color=(200, 200, 200))
        img.save(str(out_path))
