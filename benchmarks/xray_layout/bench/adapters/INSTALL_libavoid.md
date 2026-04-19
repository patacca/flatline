# INSTALL_libavoid

## Status
DEFERRED

## Repo URL
https://github.com/Adaptagrams/adaptagrams (libavoid lives in `cola/libavoid/`)

## Commands Tried
```bash
benchmarks/xray_layout/.venv-bench/bin/pip install libavoid
benchmarks/xray_layout/.venv-bench/bin/pip install adaptagrams
benchmarks/xray_layout/.venv-bench/bin/pip install pyavoid
```

## Result
All three PyPI lookups failed with
`ERROR: Could not find a version that satisfies the requirement <name>`.
Upstream adaptagrams does not publish Python wheels; only autotools/CMake
C++ artifacts are available.

## System Dependencies
For a Wave-2 source build:
- C++17 compiler (gcc / clang)
- autoconf, automake, libtool (or CMake >= 3.16 via the CMake side-tree)
- Python headers if a custom pybind11/SWIG wrapper is added

## Recommendation
Defer. Two viable paths for Wave 2:
1. Build libavoid as a shared library and write a thin pybind11 wrapper
   that exposes Router, ConnRef, Rectangle, Point, and the routing
   options enum. ~1-2 days of work.
2. Use libavoid via subprocess by exporting graph state to its diagram
   format, invoking a CLI driver, and parsing the resulting routes.
   Faster to prototype but slower at runtime.

The combo adapter (`ogdf_libavoid`) depends on a working libavoid binding,
so this gate must be cleared before the combo path can be exercised.
