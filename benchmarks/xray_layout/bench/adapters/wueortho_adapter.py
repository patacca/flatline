"""WueOrtho layout adapter (Wave 1 stub).

WueOrtho (https://github.com/WueGD/wueortho) is a Scala-based pipeline
for orthogonal graph drawing developed at the University of Wuerzburg.
There is no Python binding; integration would require either a JVM
subprocess or a HTTP wrapper.

Wave 1 status: install gate only. Nothing installed; install_check()
always returns DEFERRED with a pointer to INSTALL_wueortho.md. Stub
layout()/render() return trivial geometry.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, Any

from benchmarks.xray_layout.bench.adapters._base import BaseAdapter, LayoutResult

if TYPE_CHECKING:
    from pathlib import Path

    import networkx as nx


class WueorthoAdapter(BaseAdapter):
    """Adapter for the WueOrtho Scala orthogonal drawing pipeline."""

    name = "wueortho"

    def __init__(self) -> None:
        super().__init__(self.name)

    def install_check(self) -> tuple[bool, str]:
        """Probe for the JVM toolchain WueOrtho would need at runtime.

        We cannot probe WueOrtho itself in Wave 1 because no integration
        exists. As a proxy, we report whether `sbt` (the Scala build
        tool) is on PATH. Even a True here means "JVM toolchain
        present, integration still TBD" -- not "WueOrtho ready to run".
        """
        sbt = shutil.which("sbt")
        java = shutil.which("java")
        if sbt is None and java is None:
            return (False, "neither sbt nor java found on PATH")
        if sbt is None:
            return (
                False,
                f"java present at {java} but sbt missing; WueOrtho needs sbt",
            )
        return (
            False,
            f"sbt found at {sbt}, but WueOrtho integration not yet implemented",
        )

    def layout(self, graph: "nx.MultiDiGraph[Any]") -> LayoutResult:
        msg = (
            "WueOrtho benchmark adapter is deferred: no runnable JVM integration is "
            "implemented for the Scala pipeline"
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
