# INSTALL_domus

## Status
INSTALLED

## Repo URL
https://github.com/shape-metrics/domus
(GD2025 paper: https://arxiv.org/abs/2508.19416)

## Commands Tried
```bash
git clone --depth 1 https://github.com/shape-metrics/domus.git \
    benchmarks/xray_layout/third_party/domus
cd benchmarks/xray_layout/third_party/domus
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

## Result
Configure + build both succeeded. Final artifact:

```
benchmarks/xray_layout/third_party/domus/build/domus
```

Smoke test (binary expects `./graph.txt` in CWD):
```
$ ./domus
Current working directory: /home/patacca/patacca_git/flatline
load_graph_from_txt_file: cannot open: graph.txt
```

The diagnostic is the expected error when no input file is present and
serves as the install_check signal.

## System Dependencies
- C++ toolchain (gcc / clang) with C++17 support
- CMake >= 3.16
- pthread (auto-detected by CMake)

DOMUS is fully self-contained: bundled SAT solvers (Glucose, Kissat) and
no external library deps.

## Recommendation
Proceed to Wave 2. Concrete steps:
1. Implement `_serialize_graph(graph) -> str` in DOMUS's expected
   `graph.txt` format (see `example-graphs/grafo114.26.txt` for the
   schema).
2. In `layout()`, write `graph.txt` into a `tempfile.TemporaryDirectory`
   alongside the `domus` binary (or copy the binary in), invoke
   subprocess with a 60-s timeout.
3. Parse the resulting `drawing.svg` to recover node positions and
   edge polylines; project into `LayoutResult`.
4. The `render()` step can simply forward the SVG to PNG via cairosvg
   already available in the bench venv.

## Important
`benchmarks/xray_layout/third_party/` is in `.gitignore` — the build
output stays out of git, exactly as required.
