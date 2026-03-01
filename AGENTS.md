# Maintenance
- Update this file on every repo operation to reflect the current state.
- Keep updates minimal: only facts that save significant re-derivation time for future prompts.

# Overview
- Pip-installable Python wrapper around the Ghidra C++ decompiler, bundling runtime assets. Multi-ISA.
- **Phase P2 (Linux MVP delivery) — in progress.** Phases P0 (Spec Lock) and P1 (Contract Test Harness) are complete.
- Public API: `DecompilerSession` lifecycle + one-shot operation wrappers (`_session.py`); data models and error hierarchy in `_models.py` / `_errors.py`.
- Bridge: nanobind C++ extension (`_flatline_native.cpp`) built via optional Meson `native_bridge` feature (`auto` default); Python fallback in `_bridge.py`. Bridge normalizes native tuple/dict payloads to public dataclasses and maps exceptions to structured `internal_error` results.
- Bridge now pre-validates requested `language_id` / `compiler_spec` against enumerated pairs before native decompile calls and returns structured `unsupported_target` on mismatch (no silent fallback); malformed native "success" payloads are normalized to structured `internal_error`.
- Bridge startup now validates `runtime_data_dir` path existence and supports runtime-data-backed pair enumeration fallback (`.ldefs` parsing with backing spec-file filtering) when native pair listing is missing/empty.
- Build toolchain dependencies stay in `build-system.requires` (no user-facing `native` extra); native-dependent pytest items use `@pytest.mark.requires_native` and auto-skip with an actionable reason when `flatline._flatline_native` is unavailable.
- Meson now stages nanobind headers/sources into the build tree before compiling the native extension, preventing editable rebuild failures caused by pip build-isolation temp paths disappearing during `tox` imports.
- Native extension now links against a static Ghidra decompiler library (82 upstream C++ source files compiled via Meson, zlib required). `startDecompilerLibrary` initializes process-global state once via `std::once_flag`; `SleighArchitecture::getDescriptions()` provides native pair enumeration (285 language/compiler pairs with full Ghidra runtime data). Decompile pipeline remains a stub (`internal_error`) pending next step.
- Next: wire real decompile pipeline -- `SleighArchitecture` init per-request, `LoadImage` adapter, action/decompile/output extraction -- while preserving current bridge-level validation/enumeration guarantees.

# Non-goals
- Not a general Ghidra automation framework; only exposes the decompiler surface.
- No UI, no project database management.

# Architecture (3-layer adapter)
1. **Public Contract** — Python request/result models, error taxonomy, and session lifecycle surface (`src/flatline/_models.py`, `_errors.py`, `_session.py`)
2. **Bridge Contract** — nanobind C++ extension module (ADR-002); translates public models <-> native decompiler calls. Source in `src/flatline/_flatline_native.cpp` (linked against `ghidra_decompiler` static lib); runtime fallback in `src/flatline/_bridge.py`.
3. **Upstream Adapter** — wraps Ghidra C++ callable surface

# Conventions
- **File length:** aim for files no longer than 700 lines whenever possible. Split into focused modules if a file grows beyond this.
- **Spec-first / TDD:** test definitions precede code.
- **Error model:** Hard errors on invalid input; warnings on degraded success. No silent fallbacks.
- **All structured results are frozen value copies** — no native pointers cross the ABI boundary.
- **C++ standard: C++20** — enforced via `default_options: ['cpp_std=c++20']` in root `meson.build` and `-std=c++20` in `src/flatline/meson.build`. All C++ source must compile clean under C++20.
- **Code style:** see `docs/code_style.md` for naming, formatting, import, test, and annotation rules.
- **ASCII only in code:** all source files (`.py`, `.cpp`, `.h`, `meson.build`) must use only ASCII characters. No Unicode symbols, smart quotes, em-dashes, or non-ASCII identifiers.

# Baseline and policy
- Upstream pin: `Ghidra_12.0.3_build` @ `09f14c92d3` (2026-02-10).
- MVP host: Linux x86_64, Python 3.13+, latest-upstream-only.
- MVP target ISAs: any Ghidra-supported; priority: x86, ARM, RISC-V, MIPS (32/64-bit each).
- Stable public Python API over unstable upstream internals.
- **Always work in a Python venv** — mandatory for all development and testing.

# ADR status
- **ADR-001 (Public Scope Model): DECIDED — Option A** (Memory + Architecture + Function-Level).
  - Users provide `memory_image` + `base_address`, not file paths.
  - Convenience layer (binary file → memory → decompile) deferred to post-MVP.
  - Full rationale in `docs/specs.md` §5.5.
- **ADR-003 (Determinism Oracle Level): DECIDED** — Normalized token/structure comparison, not canonical text.
- **ADR-009 (ISA Variant Scope): DECIDED** — x86 32+64; ARM64, RISC-V 64, MIPS32; others best-effort.
- **ADR-002 (Bridge Surface): DECIDED** — nanobind C++ extension module. Public Python API is stable; bridge is internal.
- ADR-004 through ADR-008: unresolved (see `docs/roadmap.md` for schedule).

# Source of truth
- `docs/specs.md` — SDD: API contract, data models, error taxonomy, cross-cutting requirements.
- `docs/roadmap.md` — 7 phases (P0–P6), 6 milestones (M0–M5), risk register, ADR backlog.
- `docs/code_style.md` — code style guide: naming, formatting, imports, annotations, test conventions.
- `docs/planning.md` — original brief/requirements.
- `docs/preplanning.md` — discovery constraints and experiment plan (completed).
- `docs/refine_plan.md` — plan refinement checklist and cross-file consistency guide.

# Repo structure (non-vendored)
- `pyproject.toml` — project metadata, tool settings (pytest, ruff). Build backend: `meson-python`.
- `meson.build` (root) + `src/flatline/meson.build` — meson build definitions.
- `meson_options.txt` — meson feature flags (`native_bridge` for optional nanobind extension build).
- `src/flatline/` — installable Python package (src layout).
- `src/flatline/_session.py` — `DecompilerSession` lifecycle + one-shot operation wrappers.
- `src/flatline/_bridge.py` — internal bridge session protocol + fallback bridge implementation.
- `src/flatline/_runtime_data.py` — runtime-data discovery/validation helpers for language/compiler pair enumeration.
- `src/flatline/_flatline_native.cpp` — nanobind extension source with Ghidra startup + pair enumeration (wired via optional Meson `native_bridge` feature; links `ghidra_decompiler` static lib).
- `docs/` — specs, roadmap, planning artifacts.
- `notes/api/decompiler_inventory.md` — 18 required callable symbols with inputs/outputs, init order, thread-safety.
- `notes/r2ghidra/integration_map.md` — 5-section integration analysis; classifies each block as reusable / reimplement / skip. Keep as a reference implementation only.
- `tests/` — test catalog, fixture strategy, pytest skeletons, and `conftest.py`.

# Build & development commands
- **Always activate the venv first:** `source .venv/bin/activate`
- **Always use `tox`** for running tests and lint — prefer tox over invoking `pytest` or `ruff` directly.
- **Install editable (dev):** `pip install -e ".[dev]"`
- **Install editable with native bridge forced on:** `pip install -e ".[dev]" -Csetup-args=-Dnative_bridge=enabled`
- **Debug build (no optimizations, with debug symbols):** `pip install -e ".[dev]" -Csetup-args=--buildtype=debug`
- **Release build (optimized, no debug symbols):** `pip install -e ".[dev]" -Csetup-args=--buildtype=release`
- Meson buildtype defaults to `release` (-O3, no debug symbols) when not overridden. Override with `-Csetup-args=--buildtype=<debug|release|debugoptimized>` via pip or `--buildtype=<...>` via `meson setup`.
- **Build wheel:** `python -m build` (requires `build` package)
- **Run all checks (tests + lint):** `tox` (envs: `py313`, `py314`, `lint`)
- **Run tests only:** `tox -e py313,py314`
- **Run lint only:** `tox -e lint`
- **Run native-dependent tests:** `tox -e py313,py314 -- -m requires_native` (auto-skips if native extension is unavailable)
- Tox is configured for offline/local execution: skips package install, runs `pytest`/`ruff` from `.venv`, and sets `PYTHONPATH=src`.
- `skip_missing_interpreters = true` is enabled (e.g., `py313` is skipped if `python3.13` is unavailable).
- **Run single test category:** `tox -e py313,py314 -- -m unit` (also: `contract`, `integration`, `regression`, `negative`)
- **Run single test file:** `tox -e py313,py314 -- tests/unit/test_models.py`
- **Run single test:** `tox -e py313,py314 -- tests/unit/test_models.py::test_name -v`

# Tests
- 23 tests passing (17 unit, 6 contract); 16 native-dependent spec placeholders currently skip at runtime while integration assertions are still skeleton-only.
- `tests/conftest.py` — shared configuration; auto-applies category markers from directory names.
- `tests/specs/test_catalog.md` — 36 test definitions across 5 categories + contract-clause-to-test traceability matrix.
- `tests/specs/fixtures.md` — 10 fixture definitions, oracle strategy, determinism rules.
- 5 pytest skeleton files under `tests/{unit,contract,integration,regression,negative}/`.

# Vendored upstream
- `third_party/ghidra` — upstream Ghidra source snapshot.
- `third_party/r2ghidra` — reference integration code and patches.
- Treat as read-only unless explicitly asked to modify.

# Key data models (from specs.md)
- `DecompileRequest` — `memory_image`, `base_address`, `function_address`, `language_id`, `compiler_spec`, `runtime_data_dir`, `function_size_hint`, `analysis_budget`.
- `DecompileResult` — decompiled C output, structured `FunctionInfo`, warnings, error, metadata.
- `FunctionInfo` — name, entry_address, size, is_complete, prototype, local_variables, call_sites, jump_tables, diagnostics, varnode_count.
- `FunctionPrototype` — calling_convention, parameters, return_type, is_noreturn, has_this_pointer, recovery flags.
- `TypeInfo` — name, size, metatype (stable string enum).
- `DiagnosticFlags` — is_complete, has_unreachable_blocks, has_unimplemented, has_bad_data, has_no_code.
- `LanguageCompilerPair` — `language_id`, `compiler_spec`.
- `WarningItem` — `code`, `message`, `phase`.
- `ErrorItem` — `category`, `message`, `retryable`.
- `VersionInfo` — `flatline_version`, `upstream_tag`, `upstream_commit`, `runtime_data_revision`.
- `FlatlineError` — 5 categories: `invalid_argument`, `unsupported_target`, `invalid_address`, `decompile_failed`, `internal_error`.
