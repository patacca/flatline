#!/usr/bin/env bash
# install_sugiyama_libavoid.sh - Install gate for the SugiyamaLibavoid adapter.
#
# Idempotent: re-runs reuse the OGDF + adaptagrams installations from the
# component install scripts.  Composes install_libavoid.sh + install_ogdf.sh
# (same component dependencies as the existing ogdf_libavoid combo) and then
# verifies the new adapter's install_check() passes end-to-end (smoke
# fixture exercises self-loop + back-edge + true/false split).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REPO_ROOT="$(cd "${BENCH_DIR}/../.." && pwd)"
VENV_PY="${BENCH_DIR}/.venv-bench/bin/python"
INSTALL_RECORD="${SCRIPT_DIR}/INSTALL_sugiyama_libavoid.md"

LIBAVOID_OK=0
OGDF_OK=0

if bash "${SCRIPT_DIR}/install_libavoid.sh"; then
    LIBAVOID_OK=1
fi

if bash "${SCRIPT_DIR}/install_ogdf.sh"; then
    OGDF_OK=1
fi

if [[ ${LIBAVOID_OK} -eq 1 ]] && [[ ${OGDF_OK} -eq 1 ]]; then
    if (cd "${REPO_ROOT}" && "${VENV_PY}" -c "
from benchmarks.xray_layout.bench.adapters import sugiyama_libavoid_adapter
ok, msg = sugiyama_libavoid_adapter.SugiyamaLibavoidAdapter().install_check()
print(msg)
raise SystemExit(0 if ok else 1)
"); then
        cat > "${INSTALL_RECORD}" <<'EOF'
INSTALL_PATH: combined-ok
LIBAVOID: source-build (see INSTALL_libavoid.md)
OGDF: source-build (see INSTALL_ogdf.md)
ADAPTER: sugiyama_libavoid_adapter.install_check passed
EOF
        echo "[install_sugiyama_libavoid] SUCCESS"
        exit 0
    fi
fi

# Cascade-reason aggregation: identify which component(s) failed.
MISSING=""
if [[ ${LIBAVOID_OK} -eq 0 ]]; then MISSING="libavoid"; fi
if [[ ${OGDF_OK} -eq 0 ]]; then
    if [[ -n "${MISSING}" ]]; then MISSING="both"; else MISSING="ogdf"; fi
fi
if [[ -z "${MISSING}" ]]; then
    MISSING="install_check"
fi

LIBAVOID_REASON=$(grep "^REASON" "${SCRIPT_DIR}/INSTALL_libavoid.md" 2>/dev/null | head -1 || echo "see INSTALL_libavoid.md")
OGDF_REASON=$(grep "^REASON_PATH" "${SCRIPT_DIR}/INSTALL_ogdf.md" 2>/dev/null | head -2 | tr '\n' ';' || echo "see INSTALL_ogdf.md")

cat > "${INSTALL_RECORD}" <<EOF
INSTALL_PATH: deferred
MISSING: ${MISSING}
LIBAVOID_REASON: ${LIBAVOID_REASON}
OGDF_REASON: ${OGDF_REASON}
EOF

echo "[install_sugiyama_libavoid] DEFERRED: missing=${MISSING}"
exit 1
