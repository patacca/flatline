# INSTALL_ogdf_planarization

## Purpose

Patches `ogdf-python` (inside the bench venv only) to expose
`ogdf::OrthoLayout` on the `cppyy.gbl.ogdf` namespace at import time. This is
required for Baseline B (PlanarizationLayout + OrthoLayout planar layouter)
in the orthogonal-layout benchmark. Without the patch,
`ogdf.OrthoLayout` resolves to `AttributeError` because
`ogdf-python`'s `loader.py` does not pre-include
`ogdf/orthogonal/OrthoLayout.h`.

## What is patched

File: `<venv>/lib/python3.14/site-packages/ogdf_python/loader.py`

A single line is appended inside the existing pre-load `try:` block, right
after the final `cppyy.include("ogdf/basic/LayoutStandards.h")` call:

```python
    cppyy.include("ogdf/orthogonal/OrthoLayout.h")  # flatline-bench: expose OrthoLayout
```

The trailing sentinel comment (`# flatline-bench: expose OrthoLayout`) is
used by the install script to detect the patch and stay idempotent. The
venv is gitignored, so this leaves no diff against `main`.

## Run / verify

```bash
bash benchmarks/xray_layout/bench/adapters/install_ogdf_planarization.sh
```

The script:
1. Locates `loader.py` via `importlib.util.find_spec` (does not import the
   package, so it works even when `OGDF_BUILD_DIR` is unset).
2. Sets `OGDF_BUILD_DIR` and `LD_LIBRARY_PATH` to
   `benchmarks/xray_layout/third_party/ogdf/build` so the verify step can
   actually load OGDF.
3. Skips the rewrite if the sentinel is present.
4. Verifies the HARD GATE:
   `python -c "from ogdf_python import ogdf; assert hasattr(ogdf, 'OrthoLayout'); print('OK')"`
5. Exits non-zero if the gate fails. There is no Sugiyama fallback here --
   Baseline B requires OrthoLayout.

Manual gate check:

```bash
source benchmarks/xray_layout/.venv-bench/bin/activate
export OGDF_BUILD_DIR="$(realpath benchmarks/xray_layout/third_party/ogdf/build)"
export LD_LIBRARY_PATH="$OGDF_BUILD_DIR"
python -c "from ogdf_python import ogdf; assert hasattr(ogdf, 'OrthoLayout'); print('OK')"
```

## Undo

Remove the appended line from `loader.py` (identified by the
`flatline-bench: expose OrthoLayout` sentinel) and clear the package's
`__pycache__/`:

```bash
LOADER="$(.venv-bench/bin/python -c 'import importlib.util, os; s=importlib.util.find_spec("ogdf_python"); print(os.path.join(os.path.dirname(s.origin), "loader.py"))')"
sed -i '/flatline-bench: expose OrthoLayout/d' "${LOADER}"
rm -rf "$(dirname "${LOADER}")/__pycache__"
```

Or simply re-create the venv via `benchmarks/xray_layout/setup.sh` and
re-run the install scripts.

## Adapter

The Python adapter that consumes this patch is
`benchmarks/xray_layout/bench/adapters/ogdf_planarization_adapter.py`
(class `OgdfPlanarizationAdapter`, name `ogdf_planarization`). Its
`install_check()` exercises both a small planar DAG and the K5 non-planar
graph end-to-end, so a successful `install_check` also certifies that the
strict `error_class="non_planar"` contract holds before any benchmark case
runs. Invoke it via:

```bash
source benchmarks/xray_layout/.venv-bench/bin/activate
python -c "from benchmarks.xray_layout.bench.adapters import ogdf_planarization_adapter; ok, msg = ogdf_planarization_adapter.OgdfPlanarizationAdapter().install_check(); print(ok, msg)"
```
