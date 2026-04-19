#!/usr/bin/env bash
# install_domus.sh - Wave 1 install gate for DOMUS.
#
# Clones https://github.com/shape-metrics/domus into
#   benchmarks/xray_layout/third_party/domus
# (which is .gitignored) and builds the standalone `domus` executable
# via CMake. See INSTALL_domus.md for details.
set -u

DEST="benchmarks/xray_layout/third_party/domus"
BIN="$DEST/build/domus"

if [ -x "$BIN" ]; then
    echo "INSTALLED: $BIN (already built)"
    exit 0
fi

mkdir -p "$(dirname "$DEST")"

if [ ! -d "$DEST/.git" ]; then
    if ! git clone --depth 1 https://github.com/shape-metrics/domus.git "$DEST" \
            >/tmp/domus_clone.log 2>&1; then
        echo "DEFERRED: git clone failed; see /tmp/domus_clone.log"
        exit 0
    fi
fi

if ! cmake -S "$DEST" -B "$DEST/build" -DCMAKE_BUILD_TYPE=Release \
        >/tmp/domus_cmake.log 2>&1; then
    echo "DEFERRED: cmake configure failed; see /tmp/domus_cmake.log"
    exit 0
fi

if ! cmake --build "$DEST/build" -j"$(nproc)" >/tmp/domus_build.log 2>&1; then
    echo "DEFERRED: cmake build failed; see /tmp/domus_build.log"
    exit 0
fi

if [ -x "$BIN" ]; then
    echo "INSTALLED: $BIN"
else
    echo "DEFERRED: build completed but binary missing at $BIN"
fi
exit 0
