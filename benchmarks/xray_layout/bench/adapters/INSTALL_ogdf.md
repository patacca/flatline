# INSTALL_ogdf

## Status
DEFERRED

## Repo URL
- Library: https://ogdf.uos.de/ — source mirror at https://github.com/ogdf/ogdf
- Python wrapper: https://github.com/N-Coder/ogdf-python (PyPI: `ogdf-python`)

## Commands Tried
```bash
benchmarks/xray_layout/.venv-bench/bin/pip install ogdf-python
benchmarks/xray_layout/.venv-bench/bin/pip install ogdf
```

## Result
- `ogdf-python 0.3.5` (with cppyy 3.5.0, cppyy-cling 6.32.8, etc.) **installed**.
- Plain `ogdf` is not on PyPI (`No matching distribution found`).
- Importing `ogdf_python` fails at runtime:
  ```
  RuntimeError: Unable to load library "COIN"
  ImportError: ogdf-python couldn't load OGDF (or one of its
    dependencies like COIN) in mode 'release'.
  ```
  The cppyy loader cannot find `libCOIN.so`/`libOGDF.so` on
  `LD_LIBRARY_PATH`. No OGDF system package is installed
  (`apt list --installed | grep ogdf` returns nothing).

## System Dependencies
For Wave 2 the host needs the OGDF + COIN-OR shared libraries. Two
options:
1. Build from source:
   ```bash
   git clone https://github.com/ogdf/ogdf.git third_party/ogdf
   cmake -S third_party/ogdf -B third_party/ogdf/build \
         -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON
   cmake --build third_party/ogdf/build -j
   export OGDF_BUILD_DIR=$PWD/third_party/ogdf/build
   ```
   The cppyy loader honours `OGDF_BUILD_DIR` / `OGDF_INSTALL_DIR`.
2. Use a distro package where one exists (none on this Linux host).

## Recommendation
Defer Wave-2 readiness until OGDF is built from source and
`OGDF_BUILD_DIR` is exported in the bench environment. Once available,
implement layout() with `ogdf_python.PlanarizationLayout` (or
`OrthoLayout`) and project node coordinates / edge bends back into
`LayoutResult`.
