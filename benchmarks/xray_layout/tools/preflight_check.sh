#!/usr/bin/bash
set -euo pipefail

# Pre-flight assumption probes for xray-layout benchmark
# Checks 10 assumptions (A1-A10) and writes a structured report

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/home/patacca/patacca_git/flatline"
BENCH_DIR="${PROJECT_ROOT}/benchmarks/xray_layout"

# Track overall status
FAIL_COUNT=0
WARN_COUNT=0

# Helper to increment counters (avoids set -e issues with (( )))
incr_fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); }
incr_warn() { WARN_COUNT=$((WARN_COUNT + 1)); }

# A1: swig check
probe_a1() {
    local name="swig"
    local value
    local status="PASS"
    
    if command -v swig >/dev/null 2>&1; then
        value=$(swig -version 2>&1 | head -1)
    else
        value="MISSING"
        status="FAIL"
        incr_fail
        echo "       HINT: sudo apt-get install swig"
    fi
    
    echo "A1: ${name} = ${value} [${status}]"
}

# A2: libtool check
probe_a2() {
    local name="libtool"
    local value
    local status="PASS"
    
    value=$(pkg-config --modversion libtool 2>/dev/null || libtool --version 2>/dev/null | head -1 || echo "MISSING")
    
    if [[ "${value}" == "MISSING" ]]; then
        status="WARN"
        incr_warn
    fi
    
    echo "A2: ${name} = ${value} [${status}]"
}

# A3: cling check
probe_a3() {
    local name="cling"
    local value
    local status="PASS"
    
    if command -v cling >/dev/null 2>&1; then
        value=$(cling --version 2>&1 | head -1)
    else
        value="MISSING"
        status="WARN"
        incr_warn
    fi
    
    echo "A3: ${name} = ${value} [${status}]"
}

# A4: cmake and make check
probe_a4() {
    local name="source-build-toolchain"
    local cmake_ver
    local make_ver
    local status="PASS"
    
    cmake_ver=$(cmake --version 2>/dev/null | head -1 || echo "MISSING")
    make_ver=$(make --version 2>/dev/null | head -1 || echo "MISSING")
    
    if [[ "${cmake_ver}" == "MISSING" ]] || [[ "${make_ver}" == "MISSING" ]]; then
        status="FAIL"
        incr_fail
        echo "       HINT: sudo apt-get install cmake build-essential"
    fi
    
    echo "A4: ${name} = cmake:${cmake_ver}, make:${make_ver} [${status}]"
}

# A5: Python version check (must be 3.13 or 3.14)
probe_a5() {
    local name="python-version"
    local value
    local status="PASS"
    local py_ver
    
    if [[ -f "${BENCH_DIR}/.venv-bench/bin/python" ]]; then
        py_ver=$(${BENCH_DIR}/.venv-bench/bin/python -c "import sys; print(sys.version_info[:2])" 2>/dev/null || echo "MISSING")
    else
        py_ver="MISSING"
    fi
    
    value="${py_ver}"
    
    if [[ "${py_ver}" == "(3, 13)" ]] || [[ "${py_ver}" == "(3, 14)" ]]; then
        status="PASS"
    else
        status="FAIL"
        incr_fail
    fi
    
    echo "A5: ${name} = ${value} [${status}]"
}

# A6: Disk space check (warn if < 5GB free)
probe_a6() {
    local name="disk-space-gb"
    local value
    local status="PASS"
    local free_gb
    
    if [[ -d "${BENCH_DIR}" ]]; then
        free_gb=$(df -BG "${BENCH_DIR}" 2>/dev/null | tail -1 | awk '{print $4+0}' || echo "0")
    else
        free_gb="0"
    fi
    
    value="${free_gb}"
    
    if [[ "${free_gb}" -lt 5 ]]; then
        status="WARN"
        incr_warn
    fi
    
    echo "A6: ${name} = ${value} [${status}]"
}

# A7: C++ compiler check
probe_a7() {
    local name="cpp-compiler"
    local value
    local status="PASS"
    
    value=$(gcc --version 2>/dev/null | head -1 || echo "MISSING")
    
    if [[ "${value}" == "MISSING" ]]; then
        status="FAIL"
        incr_fail
    fi
    
    echo "A7: ${name} = ${value} [${status}]"
}

# A8: System libraries check (optional)
probe_a8() {
    local name="system-libs"
    local value
    local status="PASS"
    
    value=$(ldconfig -p 2>/dev/null | grep -E "libz\.so|libcairo\.so" | head -3 | tr '\n' ';' || echo "MISSING")
    
    if [[ "${value}" == "MISSING" ]] || [[ -z "${value}" ]]; then
        value="MISSING"
        status="WARN"
        incr_warn
    fi
    
    echo "A8: ${name} = ${value} [${status}]"
}

# A9: WIP delta count (informational)
probe_a9() {
    local name="wip-delta-count"
    local value
    local status="PASS"
    local count
    
    count=$(git -C "${PROJECT_ROOT}" status --porcelain benchmarks/xray_layout/ 2>/dev/null | wc -l || echo "0")
    value="${count}"
    
    # Informational only - warn if there are uncommitted changes
    if [[ "${count}" -gt 0 ]]; then
        status="WARN"
        incr_warn
    fi
    
    echo "A9: ${name} = ${value} [${status}]"
}

# A10: Branch check (must be bench/xray-layout-comparison)
probe_a10() {
    local name="git-branch"
    local value
    local status="PASS"
    
    value=$(git -C "${PROJECT_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "MISSING")
    
    if [[ "${value}" == "bench/xray-layout-comparison" ]]; then
        status="PASS"
    else
        status="FAIL"
        incr_fail
    fi
    
    echo "A10: ${name} = ${value} [${status}]"
}

# Run all probes
main() {
    echo "=== Pre-flight Assumption Probes ==="
    echo ""
    
    probe_a1
    probe_a2
    probe_a3
    probe_a4
    probe_a5
    probe_a6
    probe_a7
    probe_a8
    probe_a9
    probe_a10
    
    echo ""
    
    if [[ ${FAIL_COUNT} -gt 0 ]]; then
        echo "PRE-FLIGHT: FAIL"
        exit 1
    else
        echo "PRE-FLIGHT: PASS"
        exit 0
    fi
}

main "$@"
