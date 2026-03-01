# Maintenance
- Update this file on every repo operation; only facts that save re-derivation time.

# Overview
- Pip-installable Python wrapper around Ghidra C++ decompiler, bundling runtime assets. Multi-ISA.
- **Phase P2 (Linux MVP) — in progress.** P0, P1 complete.
- **Caveat:** `third_party/ghidra` lacks compiled `.sla` assets; decompile requests commonly return `decompile_failed`.
- **Next:** compile/provide `.sla` assets for fixture targets; replace placeholder skeleton assertions.
- Not a general Ghidra automation framework; decompiler surface only. No UI, no project DB.

# Architecture (3-layer adapter)
1. **Public Contract** — `DecompilerSession` lifecycle + one-shot wrappers (`_session.py`); models/errors in `_models.py` / `_errors.py`.
2. **Bridge Contract** — nanobind C++ extension (`_flatline_native.cpp`, ADR-002) with Python fallback (`_bridge.py`). Pre-validates language/compiler pairs; `.ldefs`-based fallback enumeration when native listing unavailable.
3. **Native layer** — 82 upstream C++ sources compiled via Meson (zlib required), linked as `ghidra_decompiler` static lib. Per-request flow: `SleighArchitecture` init, custom `LoadImage`, action reset/perform, `docFunction`, structured `FunctionInfo` extraction.

# Conventions
- **File length:** max ~700 lines; split if exceeded.
- **Spec-first / TDD:** tests precede code.
- **Error model:** hard errors on invalid input; warnings on degraded success; no silent fallbacks.
- **Frozen value copies** — no native pointers cross ABI boundary.
- **C++20** — `default_options: ['cpp_std=c++20']` in root `meson.build`, `-std=c++20` in `src/flatline/meson.build`.
- **Code style:** `docs/code_style.md`.
- **ASCII only** in `.py`, `.cpp`, `.h`, `meson.build`.

# Baseline and policy
- Upstream pin: `Ghidra_12.0.3_build` @ `09f14c92d3` (2026-02-10).
- MVP host: Linux x86_64, Python 3.13+, latest-upstream-only.
- MVP ISAs: any Ghidra-supported; priority x86, ARM, RISC-V, MIPS (32/64 each).
- Stable public Python API over unstable upstream internals.
- **Always work in a Python venv.**

# ADR status
- **ADR-001 (Public Scope Model): Option A** — Memory + Architecture + Function-Level. Users provide `memory_image` + `base_address`. Convenience file-to-memory layer deferred post-MVP. Rationale: `docs/specs.md` S5.5.
- **ADR-002 (Bridge Surface): nanobind C++ extension.** Public API stable; bridge internal.
- **ADR-003 (Determinism Oracle): Normalized token/structure comparison**, not canonical text.
- **ADR-009 (ISA Variant Scope):** x86 32+64; ARM64, RISC-V 64, MIPS32; others best-effort.
- ADR-004 through ADR-008: unresolved (`docs/roadmap.md`).

# Source of truth
- `docs/specs.md` — SDD: API contract, data models, error taxonomy, cross-cutting requirements.
- `docs/roadmap.md` — 7 phases (P0-P6), 6 milestones (M0-M5), risk register, ADR backlog.
- `docs/code_style.md` — naming, formatting, imports, annotations, test conventions.
- `docs/compact_agent.md` — compact prompt template for lossless AGENTS.md compression.
- `docs/planning.md` — original brief/requirements.
- `docs/preplanning.md` — discovery constraints and experiment plan (completed).
- `docs/refine_plan.md` — plan refinement checklist and cross-file consistency guide.

# Repo structure (non-vendored)
- `pyproject.toml` — metadata, tool settings. Build backend: `meson-python`.
- `meson.build` (root) + `src/flatline/meson.build` — build definitions.
- `meson_options.txt` — feature flags (`native_bridge`).
- `src/flatline/` — installable package (src layout).
- `src/flatline/_session.py` — `DecompilerSession` lifecycle + one-shot wrappers.
- `src/flatline/_bridge.py` — bridge session protocol + fallback implementation.
- `src/flatline/_runtime_data.py` — runtime-data discovery/validation for language/compiler pair enumeration.
- `src/flatline/_flatline_native.cpp` — nanobind extension: Ghidra startup, pair enumeration, native decompile pipeline (links `ghidra_decompiler`).
- `docs/` — specs, roadmap, planning artifacts.
- `notes/api/decompiler_inventory.md` — 18 required callable symbols with I/O, init order, thread-safety.
- `notes/r2ghidra/integration_map.md` — 5-section integration analysis (reusable/reimplement/skip). Reference only.
- `tests/` — catalog, fixtures, pytest skeletons, `conftest.py`.

# Build & development commands
- **Activate venv:** `source .venv/bin/activate`
- **Always use `tox`** for tests and lint.
- **Editable install:** `pip install -e ".[dev]"`
- **Editable + native forced:** `pip install -e ".[dev]" -Csetup-args=-Dnative_bridge=enabled`
- **Debug build:** `pip install -e ".[dev]" -Csetup-args=--buildtype=debug`
- **Release build:** `pip install -e ".[dev]" -Csetup-args=--buildtype=release`
- Meson buildtype defaults `release` (-O3). Override: `-Csetup-args=--buildtype=<debug|release|debugoptimized>`.
- **Build wheel:** `python -m build`
- **All checks:** `tox` (envs: `py313`, `py314`, `lint`)
- **Tests only:** `tox -e py313,py314`
- **Lint only:** `tox -e lint`
- **Native tests:** `tox -e py313,py314 -- -m requires_native`
- **Single category:** `tox -e py313,py314 -- -m unit` (also: `contract`, `integration`, `regression`, `negative`)
- **Single file:** `tox -e py313,py314 -- tests/unit/test_models.py`
- **Single test:** `tox -e py313,py314 -- tests/unit/test_models.py::test_name -v`
- Tox: offline/local, skips package install, runs from `.venv`, `PYTHONPATH=src`. `skip_missing_interpreters = true`.

# Tests
- 28 passing (22 unit, 6 contract); 16 native-dependent placeholders skip at runtime.
- `tests/conftest.py` — auto-applies category markers from directory names.
- `tests/specs/test_catalog.md` — 37 definitions, 5 categories, contract traceability matrix.
- `tests/specs/fixtures.md` — 10 fixtures, oracle strategy, determinism rules.
- `tests/unit/test_native_bridge_runtime_spec.py` — native smoke test (decompile path no longer stub).
- `tests/unit/test_runtime_data_spec.py` — `.ldefs` tolerance and deterministic failure tests.
- 5 skeleton files under `tests/{unit,contract,integration,regression,negative}/`.

# Vendored upstream
- `third_party/ghidra` — upstream snapshot. `third_party/r2ghidra` — reference integration.
- Read-only unless explicitly asked.

# Key data models (from specs.md)
- `DecompileRequest` — `memory_image`, `base_address`, `function_address`, `language_id`, `compiler_spec`, `runtime_data_dir`, `function_size_hint`, `analysis_budget`.
- `DecompileResult` — decompiled C, structured `FunctionInfo`, warnings, error, metadata.
- `FunctionInfo` — name, entry_address, size, is_complete, prototype, local_variables, call_sites, jump_tables, diagnostics, varnode_count.
- `FunctionPrototype` — calling_convention, parameters, return_type, is_noreturn, has_this_pointer, recovery flags.
- `TypeInfo` — name, size, metatype (stable string enum).
- `DiagnosticFlags` — is_complete, has_unreachable_blocks, has_unimplemented, has_bad_data, has_no_code.
- `LanguageCompilerPair` — `language_id`, `compiler_spec`.
- `WarningItem` — `code`, `message`, `phase`.
- `ErrorItem` — `category`, `message`, `retryable`.
- `VersionInfo` — `flatline_version`, `upstream_tag`, `upstream_commit`, `runtime_data_revision`.
- `FlatlineError` — 5 categories: `invalid_argument`, `unsupported_target`, `invalid_address`, `decompile_failed`, `internal_error`.
