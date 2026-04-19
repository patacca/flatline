# INSTALL_hola

## Status
INSTALLED

## Repo URL
- Algorithm: https://github.com/skieffer/hola (canonical HOLA reference)
- Python wrapper: https://github.com/shakfu/hola-graph (pybind11)
- PyPI: https://pypi.org/project/hola-graph/

## Commands Tried
```bash
benchmarks/xray_layout/.venv-bench/bin/pip install hola-graph
```

## Result
Installed `hola-graph 0.1.5`. Module imports cleanly:

```
['HolaEdge', 'HolaGraph', 'HolaNode', '__all__', '_core', 'api', ...]
```

A second attempt (`pip install hola`) installed an unrelated package
(`hola 1.1.54` — a sample/demo project) which was uninstalled afterwards
along with its `peppercorn` and `sampleproject` dependencies.

## System Dependencies
None at install time — the wheel ships compiled `_core` extension.
At build-from-source time the upstream wrapper would need a C++17
compiler and the adaptagrams headers.

## Recommendation
Proceed to Wave 2. Concrete steps:
1. Map `nx.MultiDiGraph` -> `HolaGraph` via `HolaNode`/`HolaEdge`.
2. Pass each node's `width`/`height` attribute through to HolaNode.
3. Run the layout (API: `hola_graph.api.run` or equivalent — to be
   confirmed against the package surface).
4. Read back node positions and convert to `LayoutResult`.
5. For edge routes, HOLA emits orthogonal polylines; project to
   `edge_routes` dict keyed by edge ID.
