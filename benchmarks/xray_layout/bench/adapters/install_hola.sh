#!/usr/bin/env bash
# install_hola.sh - Wave 1 install gate for HOLA via hola-graph.
set -u

BENCH_PIP="benchmarks/xray_layout/.venv-bench/bin/pip"

if [ ! -x "$BENCH_PIP" ]; then
    echo "DEFERRED: bench venv pip not found at $BENCH_PIP" >&2
    exit 0
fi

if "$BENCH_PIP" install hola-graph >/tmp/hola_install.log 2>&1; then
    echo "INSTALLED: hola-graph"
    exit 0
fi

echo "DEFERRED: hola-graph install failed; see INSTALL_hola.md"
exit 0
