#!/usr/bin/env bash
# install_wueortho.sh - Wave 1 install gate for WueOrtho.
#
# WueOrtho is Scala/sbt with no Python bindings; this script only
# probes for the toolchain prerequisites. Actual integration is
# deferred to Wave 2 (see INSTALL_wueortho.md).
set -u

if command -v sbt >/dev/null 2>&1 && command -v java >/dev/null 2>&1; then
    echo "DEFERRED: sbt + java present, WueOrtho integration TBD"
    exit 0
fi

echo "DEFERRED: missing sbt and/or java; WueOrtho integration TBD"
exit 0
