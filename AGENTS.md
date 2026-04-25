# Maintenance
- Update only when repo instructions or durable project facts change; do not touch this file for routine code, CI, dependency-pin, or scanner-remediation edits.
- Prefer short commit message. One line if possible.
- **NEVER use `git add -f` / `--force` to override `.gitignore`.**

# Overview
- `flatline`: pip-installable Python wrapper around Ghidra C++ decompiler (surface only).
- Version `0.1.3.dev0`; keep in sync across `pyproject.toml`, `meson.build`, `src/flatline/_version.py`.
- Latest public release: `0.1.2`.
- Enriched output: `Enriched.pcode` + `Pcode.to_graph()` for graph traversal/drawing.
- Utility: `src/flatline/xray/` ships `flatline-xray` / `python -m flatline.xray` (tkinter pcode viewer).
- Docs: `https://patacca.github.io/flatline/`; README covers local MkDocs access.
- Hosts: Linux x86_64, macOS arm64, Windows x86_64 (Tier 1); Linux aarch64, macOS x86_64 (Pending).
- Wheels: CPython 3.13/3.14, 64-bit; manylinux x86_64/aarch64, Windows x86_64, macOS x86_64/arm64.
- Deps: `ghidra-sleigh` (runtime data), `networkx` (pcode graph); `ghidra_sleigh.get_runtime_data_dir()`.
- Submodules: `third_party/ghidra` (vendored/active); `third_party/r2ghidra` (ignored); `third_party/ogdf` (vendored/active); `third_party/libavoid_src` (vendored/active).
- ISAs: x86/ARM/RISC-V/MIPS (32+64-bit); fixture-backed in `tests/fixtures/*.hex`.

# Design posture
- User-centered; focus on user convenience.
- Stable public API over unstable internals.
- Only test functional changes; packaging/CI fixes use direct artifact validation instead of new tests, unless they change a durable release/support/native-build contract.

# Public API
- Entry points: `decompile_function()`, `list_language_compilers()`, `get_version_info()`, `DecompilerSession`.
- Request/result: `DecompileRequest`, `DecompileResult`, `AnalysisBudget`.
- Enriched: `Enriched`, `Pcode`, `PcodeOpInfo`, `VarnodeInfo`, `VarnodeFlags`, `PcodeOpcode`, `VarnodeSpace`.
- Errors: `FlatlineError` hierarchy; categories in `ERROR_CATEGORIES`.

# Architecture (3-layer adapter)
- Public: `DecompilerSession` + one-shot wrappers `_session.py`; `models/`; `_errors.py`.
- Enriched: `Enriched` -> `Pcode`; `PcodeOpInfo`, `VarnodeInfo`, `VarnodeFlags`.
- `Pcode` keeps raw values, O(1) ID lookup, `to_graph()` returns `networkx.MultiDiGraph`.
- Bridge: nanobind `native/module.cpp` + Python fallback `bridge/core.py`; pre-validates language/compiler, `.ldefs` fallback; unstable internal.
- Native: 82 upstream .cc via Meson into static `ghidra_decompiler` (zlib required).
- Flow: `SleighArchitecture` -> `LoadImage` -> action perform -> `docFunction` -> `FunctionInfo`.

# Conventions
- Max 600 lines/file (except docs). Contract-first/TDD. ASCII-only in source/build files. Try avoiding more than 5 level indentation.
- Use code comments to explain concepts, intent, and non-obvious logic; save re-derivation time and reduce documentation burden.
- Clear tree structure and self-explanatory names for files, modules, classes, functions, variables.
- **Python**: ALWAYS guard type-hint imports behind `if TYPE_CHECKING:`.
- Hard errors on invalid input; warnings on degraded success; no silent fallbacks.
- Frozen value copies; no native pointers cross ABI.
- Tests: structured format parsing, not grep; workflow tests only for durable release/support/native-build invariants.
- **Build UX**: NEVER require user-facing `CPPFLAGS`/`LDFLAGS`/`PKG_CONFIG_PATH`.
- **CI**: Windows must NOT use `ilammy/msvc-dev-cmd`; all checkout steps set `persist-credentials: false`; explicit `permissions: contents: read`.
- Use C++20 std.
- Coding style: `STYLEGUIDE.md`
- ALWAYS use python venv.

# Source of truth
- `docs/archived/`: **PERMANENTLY READ-ONLY**.
- `CHANGELOG.md`: **NEVER modify dated release entries**.
- `docs/design.md`: durable posture, boundaries, heuristics, risks.
- `docs/adr/`: architecture decision records.
- `mkdocs.yml` + `docs-site/`: User documentation + site structure.
- `docs/release_workflow.md`: operator steps; `docs/adr/adr-013.md`: wheel policy.

# Build & development commands
- **Run ALL Python commands inside the venv**: `source .venv/bin/activate` first, then `python`, `pip`, `tox`, etc. No exceptions.
- Editable: `pip install -e ".[dev]"`.
- Native: `pip install -e ".[dev]" -Csetup-args=-Dnative_bridge=enabled`.
- Build types: `-Csetup-args=-Dbuildtype=<debug|release|debugoptimized>`.
- Windows: `--vsenv` via `[tool.meson-python.args]`; do NOT pre-activate MSVC (Meson skips `--vsenv` if `cl.exe`/`VSINSTALLDIR` present).
- Wheel: `python -m build`.
- Audit: `python tools/compliance.py`, `python tools/release.py`, `python tools/footprint.py`.
- Artifacts: `python tools/artifacts.py dist`.
- Linter/code formatter: `tox -e lint`
- **MUST run full `tox` before claiming any feature complete**
- Tests: `tox -e py313,py314 -- -m <unit|contract|integration|regression|negative>`.
- Native tests: `tox -e py313,py314 -- -m requires_native`.
- Single file: `tox -e py313,py314 -- tests/unit/test_bridge_adapter_spec.py`.
- Single test: `tox -e py313,py314 -- tests/unit/test_bridge_adapter_spec.py::test_name -v`.

# Tests
- Native tests require `.sla` from `ghidra-sleigh`.
- Category markers auto-applied via `tests/conftest.py`.
- Dev-tool tests skip under wheel installs via `pytest.importorskip`.
- **NEVER write tautological tests**: tests that merely restate the implementation without asserting meaningful behavior.
