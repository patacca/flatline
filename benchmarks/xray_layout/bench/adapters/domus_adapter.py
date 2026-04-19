"""DOMUS layout adapter (Wave 1 stub).

DOMUS (https://github.com/shape-metrics/domus) is a SAT-based orthogonal
graph drawing tool published at GD2025. It has no Python bindings; the
adapter wraps the `domus` C++ executable via subprocess.

Wave 1 status: built locally to
    benchmarks/xray_layout/third_party/domus/build/domus
(see INSTALL_domus.md). install_check() probes for that binary. The
stub layout()/render() return trivial geometry; Wave 2 will:
  1. Serialize the input graph to DOMUS's `graph.txt` format.
  2. Run `domus` in a temp directory and read back `drawing.svg`.
  3. Parse node positions and edge polylines from the SVG.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from benchmarks.xray_layout.bench.adapters._base import BaseAdapter, LayoutResult

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

    name = "domus"

    def __init__(self) -> None:
        super().__init__(self.name)

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
