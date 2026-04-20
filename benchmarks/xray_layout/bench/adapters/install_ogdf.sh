#!/usr/bin/env bash
# install_ogdf.sh - Wave 1 install gate for OGDF.
#
# Decision tree:
#   Path A: ogdf-python[quickstart] via cppyy/cling (preferred; needs `cling`).
#   Path B: source build of OGDF (foxglove-202510), then ogdf-python wrapper
#           with LD_LIBRARY_PATH pointing to the build dir.
# Records outcome in INSTALL_ogdf.md. Idempotent (fast re-run when importable).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_PY="${BENCH_DIR}/.venv-bench/bin/python"
VENV_PIP="${BENCH_DIR}/.venv-bench/bin/pip"
# Pinned to OGDF tag foxglove-202510.
OGDF_SHA="5b6795655399b9d8e2921afec9d97bab9107d5ee"
INSTALL_RECORD="${SCRIPT_DIR}/INSTALL_ogdf.md"
THIRD_PARTY="${BENCH_DIR}/third_party"

if [[ ! -x "${VENV_PY}" ]] || [[ ! -x "${VENV_PIP}" ]]; then
    cat > "${INSTALL_RECORD}" <<EOF
INSTALL_PATH: deferred
REASON_PATH_A: skipped (venv missing)
REASON_PATH_B: skipped (venv missing)
EOF
    echo "[install_ogdf] DEFERRED: venv missing at ${VENV_PY}"
    exit 1
fi

# Idempotent fast path: skip if already importable.
# Probe both bare (Path A wheel route) and with prior build-dir env (Path B).
PRIOR_BUILD_DIR=""
if [[ -f "${THIRD_PARTY}/ogdf/build/libOGDF.so" ]]; then
    PRIOR_BUILD_DIR="$(realpath "${THIRD_PARTY}/ogdf/build")"
fi
if "${VENV_PY}" -c "from ogdf_python import ogdf; ogdf.Graph()" 2>/dev/null; then
    echo "[install_ogdf] already importable, skipping"
    exit 0
fi
if [[ -n "${PRIOR_BUILD_DIR}" ]] && \
   OGDF_BUILD_DIR="${PRIOR_BUILD_DIR}" LD_LIBRARY_PATH="${PRIOR_BUILD_DIR}" \
   "${VENV_PY}" -c "from ogdf_python import ogdf; ogdf.Graph()" 2>/dev/null; then
    echo "[install_ogdf] already importable via prior source build, skipping"
    exit 0
fi

REASON_PATH_A=""
REASON_PATH_B=""

# ---------------------------------------------------------------------------
# Path A: ogdf-python[quickstart] via cppyy/cling.
# Requires `cling` on PATH; the wheel route uses cppyy to JIT-bind OGDF headers.
# ---------------------------------------------------------------------------
if command -v cling >/dev/null 2>&1; then
    echo "[install_ogdf] Path A: trying ogdf-python[quickstart] via cling..."
    if timeout 600 "${VENV_PIP}" install 'ogdf-python[quickstart]' >/tmp/ogdf_path_a.log 2>&1; then
        if "${VENV_PY}" -c "from ogdf_python import ogdf; G = ogdf.Graph(); [G.newNode() for _ in range(3)]; assert G.numberOfNodes()==3" 2>/dev/null; then
            MODULE_VERSION=$("${VENV_PIP}" show ogdf-python 2>/dev/null | awk '/^Version:/{print $2}')
            : "${MODULE_VERSION:=unknown}"
            cat > "${INSTALL_RECORD}" <<EOF
INSTALL_PATH: ogdf-python
MODULE_VERSION: ${MODULE_VERSION}
ATTEMPTED_PATH_A: success
EOF
            echo "[install_ogdf] SUCCESS via Path A (ogdf-python wheel)"
            exit 0
        else
            REASON_PATH_A="ogdf-python installed but smoke test failed"
        fi
    else
        REASON_PATH_A="ogdf-python[quickstart] pip install failed (see /tmp/ogdf_path_a.log)"
    fi
else
    REASON_PATH_A="skipped (cling missing)"
fi

echo "[install_ogdf] Path A unavailable: ${REASON_PATH_A}"

# ---------------------------------------------------------------------------
# Path B: source build.
# Requires cmake + make + g++. Builds shared libOGDF + libCOIN, then installs
# ogdf-python wrapper with LD_LIBRARY_PATH set to the build dir.
# ---------------------------------------------------------------------------
echo "[install_ogdf] Path B: source build..."

write_deferred() {
    cat > "${INSTALL_RECORD}" <<EOF
INSTALL_PATH: deferred
REASON_PATH_A: ${REASON_PATH_A}
REASON_PATH_B: ${REASON_PATH_B}
EOF
}

for tool in cmake make g++ git; do
    if ! command -v "${tool}" >/dev/null 2>&1; then
        REASON_PATH_B="missing tool: ${tool}"
        write_deferred
        echo "[install_ogdf] DEFERRED: ${REASON_PATH_B}"
        exit 1
    fi
done

mkdir -p "${THIRD_PARTY}"

# Disk space check (need ~5GB headroom).
FREE_GB=$(df -BG "${THIRD_PARTY}" 2>/dev/null | tail -1 | awk '{print $4+0}' || echo 0)
if [[ "${FREE_GB}" -lt 5 ]]; then
    REASON_PATH_B="insufficient disk (need 5GB, have ${FREE_GB}GB)"
    write_deferred
    echo "[install_ogdf] DEFERRED: ${REASON_PATH_B}"
    exit 1
fi

# Clone OGDF and pin to OGDF_SHA.
if [[ ! -d "${THIRD_PARTY}/ogdf/.git" ]]; then
    rm -rf "${THIRD_PARTY}/ogdf"
    git clone --no-tags https://github.com/ogdf/ogdf.git "${THIRD_PARTY}/ogdf"
fi
(
    cd "${THIRD_PARTY}/ogdf"
    # Fetch SHA explicitly (shallow clones may miss it).
    git fetch --depth 1 origin "${OGDF_SHA}" 2>/dev/null || git fetch origin
    git checkout "${OGDF_SHA}"
)

mkdir -p "${THIRD_PARTY}/ogdf/build"
cd "${THIRD_PARTY}/ogdf/build"

if ! cmake .. -DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release -DOGDF_WARNING_ERRORS=OFF >/tmp/ogdf_cmake.log 2>&1; then
    REASON_PATH_B="cmake configure failed (see /tmp/ogdf_cmake.log)"
    write_deferred
    echo "[install_ogdf] DEFERRED: ${REASON_PATH_B}"
    exit 1
fi

set +e
timeout 1500 make -j"$(nproc)" >/tmp/ogdf_make.log 2>&1
MAKE_EXIT=$?
set -e
if [[ ${MAKE_EXIT} -eq 124 ]]; then
    REASON_PATH_B="make timed out after 1500s"
    write_deferred
    echo "[install_ogdf] DEFERRED: ${REASON_PATH_B}"
    exit 1
fi
if [[ ${MAKE_EXIT} -ne 0 ]]; then
    REASON_PATH_B="make failed with exit ${MAKE_EXIT} (see /tmp/ogdf_make.log)"
    write_deferred
    echo "[install_ogdf] DEFERRED: ${REASON_PATH_B}"
    exit 1
fi

OGDF_BUILD_DIR="$(realpath "${THIRD_PARTY}/ogdf/build")"

# Install the ogdf-python wrapper (without [quickstart] cling extra).
"${VENV_PIP}" install ogdf-python >/tmp/ogdf_python_install.log 2>&1 || true

# Smoke test against the source-built libs.
# ogdf-python uses OGDF_BUILD_DIR to locate headers + cppyy include paths;
# LD_LIBRARY_PATH lets the dynamic loader resolve libCOIN/libOGDF at import time.
if OGDF_BUILD_DIR="${OGDF_BUILD_DIR}" LD_LIBRARY_PATH="${OGDF_BUILD_DIR}" "${VENV_PY}" -c "from ogdf_python import ogdf; G = ogdf.Graph(); [G.newNode() for _ in range(3)]; assert G.numberOfNodes()==3" 2>/dev/null; then
    cat > "${INSTALL_RECORD}" <<EOF
INSTALL_PATH: source-build
OGDF_SHA: ${OGDF_SHA}
BUILD_DIR: ${OGDF_BUILD_DIR}
REASON_PATH_A: ${REASON_PATH_A}
EOF
    echo "[install_ogdf] SUCCESS via Path B (source build); LD_LIBRARY_PATH=${OGDF_BUILD_DIR}"
    exit 0
else
    REASON_PATH_B="ogdf-python ABI vs source-built OGDF mismatch or import failed"
    write_deferred
    echo "[install_ogdf] DEFERRED: ${REASON_PATH_B}"
    exit 1
fi
