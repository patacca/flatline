# Maintenance
- Update this file on every repo operation to reflect the current state.
- Keep updates minimal: only facts that save significant re-derivation time for future prompts.

# Overview
- Pip-installable Python wrapper around the Ghidra C++ decompiler, bundling runtime assets. Multi-ISA.
- Phase P0 (Spec Lock) is **complete**.
- Phase P1 (Contract Test Harness) is **complete** — 26 test definitions, 10 fixtures, contract traceability matrix, ADRs resolved.
- **Phase P2 (Linux MVP delivery) — in progress.** P2-Step-1 complete: Python data models, error hierarchy, 10 tests passing (6 unit + 4 contract).
- Next: P2-Step-2 (nanobind C++ bridge skeleton, LoadImage, session lifecycle).

# Non-goals
- Not a general Ghidra automation framework; only exposes the decompiler surface.
- No UI, no project database management.

# Architecture (3-layer adapter)
1. **Public Contract** — Python request/result models, error taxonomy (`src/flatline/_models.py`, `_errors.py`)
2. **Bridge Contract** — nanobind C++ extension module (ADR-002); translates public models ↔ native decompiler calls
3. **Upstream Adapter** — wraps Ghidra C++ callable surface

# Conventions
- **Spec-first / TDD:** test definitions precede code.
- **Error model:** Hard errors on invalid input; warnings on degraded success. No silent fallbacks.
- **All structured results are frozen value copies** — no native pointers cross the ABI boundary.
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
- `src/flatline/` — installable Python package (src layout).
- `docs/` — specs, roadmap, planning artifacts.
- `notes/api/decompiler_inventory.md` — 18 required callable symbols with inputs/outputs, init order, thread-safety.
- `notes/r2ghidra/integration_map.md` — 5-section integration analysis; classifies each block as reusable / reimplement / skip. Keep as a reference implementation only.
- `tests/` — test catalog, fixture strategy, pytest skeletons, and `conftest.py`.

# Build & development commands
- **Always activate the venv first:** `source .venv/bin/activate`
- **Always use `tox`** for running tests and lint — prefer tox over invoking `pytest` or `ruff` directly.
- **Install editable (dev):** `pip install -e ".[dev]"`
- **Build wheel:** `python -m build` (requires `build` package)
- **Run all checks (tests + lint):** `tox` (envs: `py313`, `py314`, `lint`)
- **Run tests only:** `tox -e py313,py314`
- **Run lint only:** `tox -e lint`
- **Run single test category:** `tox -e py313,py314 -- -m unit` (also: `contract`, `integration`, `regression`, `negative`)
- **Run single test file:** `tox -e py313,py314 -- tests/unit/test_models.py`
- **Run single test:** `tox -e py313,py314 -- tests/unit/test_models.py::test_name -v`

# Tests
- 10 tests passing (6 unit, 4 contract); 16 still skip-decorated (need native bridge).
- `tests/conftest.py` — shared configuration; auto-applies category markers from directory names.
- `tests/specs/test_catalog.md` — 26 test definitions across 5 categories + contract-clause-to-test traceability matrix.
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
