"""libavoid layout adapter (Wave 1 stub).

libavoid is a C++ library for orthogonal connector routing, part of the
adaptagrams project (https://github.com/Adaptagrams/adaptagrams). It is
typically used to route edges between nodes whose positions are computed
by another engine (e.g. OGDF, see ogdf_libavoid_adapter for the planned
combo).

Wave 1 status: install gate only. No PyPI distribution exists for libavoid;
upstream ships only autotools/CMake C++ artifacts. See INSTALL_libavoid.md
for the deferred build plan. The stub layout()/render() implementations
return trivial 2-node geometry so the harness pipeline (timeout, schema
emission, render path) can still be exercised end-to-end.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from benchmarks.xray_layout.bench.adapters._base import BaseAdapter, LayoutResult

if TYPE_CHECKING:
    from pathlib import Path

    import networkx as nx


class LibavoidAdapter(BaseAdapter):
    """Adapter wrapping the libavoid orthogonal connector router.

    Wave 1: stub only. install_check() probes for any of the candidate
    Python module names; layout()/render() return trivial placeholders.
    """

    name = "libavoid"

    def __init__(self) -> None:
        super().__init__(self.name)

    def install_check(self) -> tuple[bool, str]:
        """Probe for any libavoid Python binding.

        Returns (True, version) if any candidate import succeeds; otherwise
        (False, reason) with the last ImportError message.
        """
        # Candidate module names observed in the wild for libavoid bindings.
        candidates = ("libavoid", "pyavoid", "adaptagrams")
        last_error = "no candidate module name was importable"
        for mod_name in candidates:
            try:
                mod = __import__(mod_name)
            except ImportError as exc:
                last_error = f"{mod_name}: {exc}"
                continue
            version = getattr(mod, "__version__", "unknown")
            return (True, f"{mod_name} {version}")
        return (False, last_error)

    def layout(self, graph: "nx.MultiDiGraph[Any]") -> LayoutResult:
        msg = (
            "libavoid benchmark adapter is deferred: the install gate did not produce "
            "a usable Python binding in this bench environment"
        )
        raise NotImplementedError(msg)

    def render(
        self,
        result: LayoutResult,
        graph: "nx.MultiDiGraph[Any]",
        out_path: Path,
    ) -> None:
        """Stub render: write a 1x1 placeholder PNG.

        Wave 2 will draw nodes as rectangles and edges as polylines built
        from libavoid's checkpoints.
        """
        from PIL import Image

        img = Image.new("RGB", (1, 1), color=(200, 200, 200))
        img.save(str(out_path))
