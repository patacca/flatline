#!/usr/bin/env bash
# install_ogdf_libavoid.sh - Wave 1 install gate for the OGDF+libavoid combo.
#
# Pure composition: defers to install_ogdf.sh and install_libavoid.sh
# and reports INSTALLED only if BOTH succeed. See
# INSTALL_ogdf_libavoid.md for the combo strategy.
set -u

ADAPTER_DIR="$(dirname "$0")"

OGDF_RESULT="$("$ADAPTER_DIR/install_ogdf.sh" 2>&1 | tail -1)"
LIBAVOID_RESULT="$("$ADAPTER_DIR/install_libavoid.sh" 2>&1 | tail -1)"

case "$OGDF_RESULT" in
    INSTALLED*) ogdf_ok=1 ;;
    *)          ogdf_ok=0 ;;
esac
case "$LIBAVOID_RESULT" in
    INSTALLED*) libavoid_ok=1 ;;
    *)          libavoid_ok=0 ;;
esac

if [ "$ogdf_ok" = 1 ] && [ "$libavoid_ok" = 1 ]; then
    echo "INSTALLED: ogdf_libavoid combo (both components ready)"
    exit 0
fi

echo "DEFERRED: ogdf=$OGDF_RESULT | libavoid=$LIBAVOID_RESULT"
exit 0
