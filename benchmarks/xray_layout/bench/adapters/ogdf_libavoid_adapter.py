"""OGDF + libavoid combo layout adapter (Wave 1 stub).

The combo strategy uses OGDF for node placement (its compaction and
planarization passes are mature) and libavoid for orthogonal edge
routing (its router is the de-facto reference). Neither is currently
runnable end-to-end -- both component adapters report DEFERRED -- but
this adapter sets up the plumbing so that as soon as the two engines
are available the combo can be exercised without further harness work.

install_check() delegates to OgdfAdapter.install_check() and
LibavoidAdapter.install_check() and returns True only if BOTH succeed.
The stub layout() documents the planned data flow in code comments.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from benchmarks.xray_layout.bench.adapters._base import BaseAdapter, LayoutResult
from benchmarks.xray_layout.bench.adapters.libavoid_adapter import LibavoidAdapter
from benchmarks.xray_layout.bench.adapters.ogdf_adapter import OgdfAdapter

if TYPE_CHECKING:
    from pathlib import Path

    import networkx as nx


class OgdfLibavoidAdapter(BaseAdapter):
    """Combo adapter: OGDF for node positions, libavoid for edge routes."""

    name = "ogdf_libavoid"

    def __init__(self) -> None:
        super().__init__(self.name)
        # Hold component adapter instances so install_check() and the
        # eventual Wave-2 layout() can delegate without re-importing.
        self._ogdf = OgdfAdapter()
        self._libavoid = LibavoidAdapter()

    def install_check(self) -> tuple[bool, str]:
        """Both components must be installed for the combo to run."""
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
        msg = (
            "OGDF+libavoid benchmark adapter is deferred: both component engines must "
            "pass their install gates before the combo pipeline can run"
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
