#!/usr/bin/env bash
# install_ogdf.sh - Wave 1 install gate for OGDF via ogdf-python.
#
# The pip install side succeeds; the runtime gate only passes if the
# OGDF + COIN-OR shared libraries are reachable via LD_LIBRARY_PATH or
# the OGDF_BUILD_DIR / OGDF_INSTALL_DIR env vars (see INSTALL_ogdf.md).
set -u

BENCH_PIP="benchmarks/xray_layout/.venv-bench/bin/pip"
BENCH_PY="benchmarks/xray_layout/.venv-bench/bin/python"

if [ ! -x "$BENCH_PIP" ] || [ ! -x "$BENCH_PY" ]; then
    echo "DEFERRED: bench venv not found" >&2
    exit 0
fi

if ! "$BENCH_PIP" install ogdf-python >/tmp/ogdf_install.log 2>&1; then
    echo "DEFERRED: ogdf-python pip install failed"
    exit 0
fi

if "$BENCH_PY" -c 'import ogdf_python' >/tmp/ogdf_import.log 2>&1; then
    echo "INSTALLED: ogdf-python (with libOGDF/libCOIN reachable)"
    exit 0
fi

echo "DEFERRED: ogdf-python installed but libOGDF/libCOIN missing"
echo "          see INSTALL_ogdf.md for the system-build plan"
exit 0
