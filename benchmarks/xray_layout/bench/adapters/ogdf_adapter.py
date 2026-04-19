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

from typing import TYPE_CHECKING, Any

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

    def layout(self, graph: "nx.MultiDiGraph[Any]") -> LayoutResult:
        msg = (
            "OGDF benchmark adapter is deferred: ogdf_python cannot import until the "
            "required system libCOIN/libOGDF shared libraries are installed"
        )
        raise NotImplementedError(msg)

    def render(
        self,
        result: LayoutResult,
        graph: "nx.MultiDiGraph[Any]",
        out_path: Path,
    ) -> None:
        from PIL import Image

        img = Image.new("RGB", (1, 1), color=(200, 200, 200))
        img.save(str(out_path))
