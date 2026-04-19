#!/usr/bin/env bash
# install_libavoid.sh - Wave 1 install gate for libavoid.
#
# Tries each known PyPI candidate name in turn. All are expected to fail
# (no upstream wheel exists); see INSTALL_libavoid.md for the deferred
# Wave-2 source-build plan.
#
# Usage:
#   ./install_libavoid.sh
#
# The script always exits 0 so it can run as a probe; check the output
# for "INSTALLED" / "DEFERRED" markers.

set -u

BENCH_PIP="benchmarks/xray_layout/.venv-bench/bin/pip"

if [ ! -x "$BENCH_PIP" ]; then
    echo "DEFERRED: bench venv pip not found at $BENCH_PIP" >&2
    exit 0
fi

for pkg in libavoid adaptagrams pyavoid; do
    echo "--- attempting: pip install $pkg"
    if "$BENCH_PIP" install "$pkg" >/tmp/libavoid_install.log 2>&1; then
        echo "INSTALLED: $pkg"
        exit 0
    fi
done

echo "DEFERRED: no PyPI candidate satisfied; see INSTALL_libavoid.md"
exit 0
