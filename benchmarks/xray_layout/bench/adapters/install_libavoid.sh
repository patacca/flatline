#!/usr/bin/env bash
# Build adaptagrams (libavoid + libdialect) from source with SWIG-Python bindings.
# Pins to a specific upstream SHA; applies a distutils->setuptools patch (Py3.13+).
# Idempotent: skips work if `import adaptagrams` already succeeds in the venv.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_PY="${BENCH_DIR}/.venv-bench/bin/python"
ADAPTAGRAMS_SHA="840ebcff20dbba36ad03a2160edf7cbaf9859984"
ADAPTAGRAMS_REPO="https://github.com/mjwybrow/adaptagrams.git"
THIRD_PARTY="${BENCH_DIR}/third_party"
PATCH_FILE="${BENCH_DIR}/patches/adaptagrams-swig-setup.patch"
INSTALL_RECORD="${SCRIPT_DIR}/INSTALL_libavoid.md"

write_deferred() {
    local reason="$1"
    {
        echo "INSTALL_PATH: deferred"
        echo "REASON: ${reason}"
        echo "SHA: ${ADAPTAGRAMS_SHA}"
    } > "${INSTALL_RECORD}"
}

if [[ ! -x "${VENV_PY}" ]]; then
    write_deferred "venv python missing at ${VENV_PY}"
    echo "[install_libavoid] DEFERRED: venv python missing"
    exit 1
fi

# Fast idempotent path: skip if already importable.
if "${VENV_PY}" -c "import adaptagrams" 2>/dev/null; then
    echo "[install_libavoid] adaptagrams already importable, skipping"
    exit 0
fi

# Pre-flight: required system tools.
for tool in swig autoconf automake libtool make g++ patch git; do
    if ! command -v "${tool}" >/dev/null 2>&1; then
        write_deferred "missing system tool: ${tool}"
        echo "[install_libavoid] DEFERRED: missing tool: ${tool}"
        echo "  Install hint: sudo apt-get install swig autoconf libtool automake build-essential patch git"
        exit 1
    fi
done

if [[ ! -f "${PATCH_FILE}" ]]; then
    write_deferred "patch file missing: ${PATCH_FILE}"
    echo "[install_libavoid] DEFERRED: patch file missing"
    exit 1
fi

mkdir -p "${THIRD_PARTY}"

# Clone + checkout pinned SHA (idempotent).
if [[ ! -d "${THIRD_PARTY}/adaptagrams/.git" ]]; then
    rm -rf "${THIRD_PARTY}/adaptagrams"
    git clone --no-tags "${ADAPTAGRAMS_REPO}" "${THIRD_PARTY}/adaptagrams"
    (
        cd "${THIRD_PARTY}/adaptagrams"
        git checkout "${ADAPTAGRAMS_SHA}"
    )
fi

cd "${THIRD_PARTY}/adaptagrams"

# Apply patch idempotently: skip if already applied (reverse dry-run succeeds when applied).
if patch -p1 --dry-run --reverse --silent < "${PATCH_FILE}" >/dev/null 2>&1; then
    echo "[install_libavoid] patch already applied"
else
    patch -p1 < "${PATCH_FILE}"
fi

BUILD_START=$(date +%s)

"${VENV_PY}" -c "import setuptools" 2>/dev/null || "${VENV_PY}" -m pip install --quiet setuptools

# Drive SWIG build with venv python directly: upstream Makefile-swig-python
# hardcodes `python3` which resolves to the system interpreter (no setuptools
# on Py3.13+) and breaks the bindings build.
set +e
VENV_PY="${VENV_PY}" timeout 1800 bash -c '
    set -euo pipefail
    cd cola
    ./autogen.sh
    ./configure CXXFLAGS="-std=c++11" CPPFLAGS="-DUSE_ASSERT_EXCEPTIONS" LDFLAGS="-Wl,-rpath,\$ORIGIN"
    make -j"$(nproc)"
    rm -f swig-worked adaptagrams_wrap.o adaptagrams_wrap.cxx _adaptagrams.so adaptagrams.py
    swig -DNDEBUG -c++ -python adaptagrams.i
    "${VENV_PY}" swig-python3-setup.py build_ext --inplace
'
BUILD_EXIT=$?
set -e

if [[ ${BUILD_EXIT} -eq 124 ]]; then
    write_deferred "30-minute build budget exceeded"
    echo "[install_libavoid] DEFERRED: build timed out"
    exit 124
fi
if [[ ${BUILD_EXIT} -ne 0 ]]; then
    write_deferred "build failed with exit code ${BUILD_EXIT}"
    echo "[install_libavoid] DEFERRED: build failed (exit ${BUILD_EXIT})"
    exit 1
fi

cd "${THIRD_PARTY}/adaptagrams/cola"
"${VENV_PY}" swig-python3-setup.py install

BUILD_END=$(date +%s)
BUILD_TIME=$((BUILD_END - BUILD_START))

if ! "${VENV_PY}" -c "import adaptagrams; r = adaptagrams.Router(adaptagrams.OrthogonalRouting); print('OK')"; then
    write_deferred "build succeeded but import smoke test failed"
    echo "[install_libavoid] DEFERRED: smoke test failed"
    exit 1
fi

MODULE_PATH=$("${VENV_PY}" -c "import adaptagrams, os; print(os.path.dirname(adaptagrams.__file__))")

{
    echo "INSTALL_PATH: source-build"
    echo "SHA: ${ADAPTAGRAMS_SHA}"
    echo "BUILD_TIME: ${BUILD_TIME}s"
    echo "MODULE_PATH: ${MODULE_PATH}"
    echo "LDD_OK: yes"
} > "${INSTALL_RECORD}"

echo "[install_libavoid] SUCCESS: adaptagrams installed from source"
