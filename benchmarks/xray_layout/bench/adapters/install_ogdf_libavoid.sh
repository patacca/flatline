#!/usr/bin/env bash
# install_ogdf_libavoid.sh - Combo install gate for the OGDF+libavoid adapter.
#
# Wraps install_libavoid.sh and install_ogdf.sh; succeeds only if both
# components are importable simultaneously. Records combined outcome in
# INSTALL_ogdf_libavoid.md and surfaces the cascade reason on partial failure.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_PY="${BENCH_DIR}/.venv-bench/bin/python"
INSTALL_RECORD="${SCRIPT_DIR}/INSTALL_ogdf_libavoid.md"

LIBAVOID_OK=0
OGDF_OK=0

if bash "${SCRIPT_DIR}/install_libavoid.sh"; then
    LIBAVOID_OK=1
fi

if bash "${SCRIPT_DIR}/install_ogdf.sh"; then
    OGDF_OK=1
fi

if [[ ${LIBAVOID_OK} -eq 1 ]] && [[ ${OGDF_OK} -eq 1 ]]; then
    if "${VENV_PY}" -c "import adaptagrams; from ogdf_python import ogdf; ogdf.Graph()" 2>/dev/null; then
        cat > "${INSTALL_RECORD}" <<'EOF'
INSTALL_PATH: combined-ok
LIBAVOID: source-build
OGDF: see INSTALL_ogdf.md
EOF
        echo "[install_ogdf_libavoid] SUCCESS: both components installed"
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
    MISSING="combined-import"
fi

LIBAVOID_REASON=$(grep "^REASON:" "${SCRIPT_DIR}/INSTALL_libavoid.md" 2>/dev/null | head -1 || echo "see INSTALL_libavoid.md")
OGDF_REASON=$(grep "^REASON_PATH" "${SCRIPT_DIR}/INSTALL_ogdf.md" 2>/dev/null | head -2 | tr '\n' ';' || echo "see INSTALL_ogdf.md")

cat > "${INSTALL_RECORD}" <<EOF
INSTALL_PATH: deferred
MISSING: ${MISSING}
LIBAVOID_REASON: ${LIBAVOID_REASON}
OGDF_REASON: ${OGDF_REASON}
EOF

echo "[install_ogdf_libavoid] DEFERRED: missing=${MISSING}"
exit 1
