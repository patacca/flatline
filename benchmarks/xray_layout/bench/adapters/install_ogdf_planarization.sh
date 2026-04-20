#!/usr/bin/env bash
# install_ogdf_planarization.sh - Patch ogdf-python to expose OrthoLayout.
#
# ogdf-python's loader.py only pre-includes a small set of OGDF headers; types
# from headers it does not include are not exposed on the `ogdf` namespace
# until something else triggers cppyy to parse them. OrthoLayout
# (ogdf/orthogonal/OrthoLayout.h) is one such missing header, which blocks
# Baseline B (PlanarizationLayout + OrthoLayout planar layouter).
#
# This script idempotently appends one line to ogdf_python/loader.py inside
# the bench venv (the venv itself is gitignored, so this leaves no diff
# against main).  It is guarded by a sentinel so re-runs are no-ops.
#
# Exits 0 on success / already-applied; non-zero if the verification gate
# fails (HARD GATE per Baseline B contract -- no Sugiyama fallback here).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_PY="${BENCH_DIR}/.venv-bench/bin/python"
THIRD_PARTY="${BENCH_DIR}/third_party"
OGDF_BUILD="${THIRD_PARTY}/ogdf/build"

if [[ ! -x "${VENV_PY}" ]]; then
    echo "[install_ogdf_planarization] FAIL: venv python missing at ${VENV_PY}" >&2
    exit 1
fi

# Locate ogdf_python/loader.py without importing the package (the import
# itself fails when OGDF_BUILD_DIR / LD_LIBRARY_PATH are unset).  We resolve
# the package via importlib.util.find_spec, which only inspects metadata.
LOADER_PY="$("${VENV_PY}" -c "
import importlib.util, os, sys
spec = importlib.util.find_spec('ogdf_python')
if spec is None or spec.origin is None:
    sys.exit(1)
print(os.path.join(os.path.dirname(spec.origin), 'loader.py'))
" 2>/dev/null || true)"
if [[ -z "${LOADER_PY}" || ! -f "${LOADER_PY}" ]]; then
    echo "[install_ogdf_planarization] FAIL: cannot locate ogdf_python/loader.py" >&2
    exit 1
fi

# Env required so the loader can actually load OGDF for the verification step.
if [[ -d "${OGDF_BUILD}" ]]; then
    export OGDF_BUILD_DIR="$(realpath "${OGDF_BUILD}")"
    export LD_LIBRARY_PATH="${OGDF_BUILD_DIR}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
fi

verify() {
    "${VENV_PY}" -c "from ogdf_python import ogdf; assert hasattr(ogdf, 'OrthoLayout'), 'OrthoLayout missing'; print('OK')"
}

# Fast idempotent path: if already exposed, nothing to do.
if verify >/dev/null 2>&1; then
    echo "[install_ogdf_planarization] already exposed, skipping patch"
    exit 0
fi

SENTINEL="# flatline-bench: expose OrthoLayout"
PATCH_LINE='cppyy.include("ogdf/orthogonal/OrthoLayout.h")  '"${SENTINEL}"

# Apply patch only if sentinel is absent.  We append after the last
# `cppyy.include(...)` block in loader.py (inside the try: ... except
# ImportError block, before it raises).  The simplest robust insertion
# point is right after `cppyy.include("ogdf/basic/LayoutStandards.h")`
# which is the final pre-load include.
if ! grep -qF "${SENTINEL}" "${LOADER_PY}"; then
    echo "[install_ogdf_planarization] patching ${LOADER_PY}"
    "${VENV_PY}" - <<EOF
import io, sys
path = r"""${LOADER_PY}"""
sentinel = r"""${SENTINEL}"""
patch_line = r'''cppyy.include("ogdf/orthogonal/OrthoLayout.h")  ''' + sentinel
with open(path, "r", encoding="utf-8") as fh:
    src = fh.read()
if sentinel in src:
    sys.exit(0)
anchor = 'cppyy.include("ogdf/basic/LayoutStandards.h")'
if anchor not in src:
    print(f"FAIL: anchor not found in {path}", file=sys.stderr)
    sys.exit(2)
new = src.replace(anchor, anchor + "\n    " + patch_line, 1)
with open(path, "w", encoding="utf-8") as fh:
    fh.write(new)
EOF
else
    echo "[install_ogdf_planarization] sentinel present, skipping rewrite"
fi

# Drop any stale bytecode so the next import sees the patched source.
"${VENV_PY}" -c "
import pathlib, ogdf_python, shutil
pkg = pathlib.Path(ogdf_python.__file__).parent
cache = pkg / '__pycache__'
if cache.is_dir():
    shutil.rmtree(cache)
" 2>/dev/null || true

# HARD GATE: verify after patch.
if ! verify; then
    echo "[install_ogdf_planarization] FAIL: OrthoLayout still not exposed after patch" >&2
    exit 1
fi

echo "[install_ogdf_planarization] SUCCESS"
exit 0
