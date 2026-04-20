#!/usr/bin/env bash
# HOLA ships inside libdialect within the same adaptagrams SWIG module.
# Delegate to install_libavoid.sh, then verify HOLA symbols are exposed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_PY="${BENCH_DIR}/.venv-bench/bin/python"
INSTALL_RECORD="${SCRIPT_DIR}/INSTALL_hola.md"

write_deferred() {
    local reason="$1"
    {
        echo "INSTALL_PATH: deferred"
        echo "REASON: ${reason}"
    } > "${INSTALL_RECORD}"
}

set +e
bash "${SCRIPT_DIR}/install_libavoid.sh"
LIBAVOID_EXIT=$?
set -e

if [[ ${LIBAVOID_EXIT} -ne 0 ]]; then
    write_deferred "install_libavoid.sh exited with code ${LIBAVOID_EXIT}; see INSTALL_libavoid.md"
    echo "[install_hola] DEFERRED: libavoid install failed (exit ${LIBAVOID_EXIT})"
    exit ${LIBAVOID_EXIT}
fi

# Probe HOLA accessibility via SWIG-exposed symbols (doHOLA / dialect / HOLA*).
if "${VENV_PY}" -c "
import adaptagrams
syms = dir(adaptagrams)
ok = any('HOLA' in s.upper() or 'doHOLA' in s for s in syms) or hasattr(adaptagrams, 'dialect')
import sys
sys.exit(0 if ok else 1)
" 2>/dev/null; then
    {
        echo "INSTALL_PATH: source-build"
        echo "REASON: adaptagrams built with libdialect; doHOLA accessible"
    } > "${INSTALL_RECORD}"
    echo "[install_hola] SUCCESS: HOLA accessible via adaptagrams"
else
    write_deferred "adaptagrams built but doHOLA symbol not exposed in SWIG bindings (libdialect not enabled in build)"
    echo "[install_hola] DEFERRED: doHOLA not exposed"
    exit 1
fi
