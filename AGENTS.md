# Maintenance
- Update this file on every repo operation; only facts that save re-derivation time.

# Overview
- Pip-installable Python wrapper around the Ghidra C++ decompiler, consuming packaged runtime assets from `ghidra-sleigh`. Multi-ISA.
- **Phase P2 (Linux MVP) — in progress.** P0, P1 complete.
- `.sla` runtime data now comes from the `ghidra-sleigh` runtime dependency (pip name) / `ghidra_sleigh` (import); default build ships all processor families, lighter build uses `all_processors=false`.
- `pyproject.toml` now pins `ghidra-sleigh == 12.0.4` to match the vendored `Ghidra_12.0.4_build` native baseline.
- `third_party/ghidra` is now tracked by the top-level repo as a git submodule pinned to `Ghidra_12.0.4_build` / `e40ed13014025f82488b1f8f7bca566894ac376b`; `third_party/r2ghidra` remains a local read-only reference checkout ignored by the parent repo.
- End-to-end decompilation verified: x86_64 `add(a,b)` produces correct C output with full structured data.
- Priority-ISA native memory fixtures are now committed as `tests/fixtures/*.hex`: x86_64, x86_32, AArch64, RISC-V 64, MIPS32, plus x86_64 switch and warning fixtures.
- Fixture sources now live beside the artifacts under `tests/fixtures/sources/`, with regeneration scripted in `tests/fixtures/generate_hex_fixtures.py`.
- Tox now tests the installed package artifact: `py313`/`py314` build `flatline[test]` wheels inside `.tox`, while `lint` remains package-skip + `ruff`.
- Public sessions now auto-discover `ghidra_sleigh.get_runtime_data_dir()` when `runtime_data_dir` is omitted; explicit `runtime_data_dir` values still override the default, and auto-discovered Ghidra pin drift is surfaced as a runtime warning.
- ADR-005 is now resolved: `AnalysisBudget` is a public frozen value type, omitted requests default to `max_instructions=100000`, mapping inputs are coerced/validated in `DecompileRequest`, and the native bridge applies the resolved cap to `Architecture::max_instructions`. Unsupported budget keys or non-positive limits fail as `invalid_argument`; wall-clock timeout remains out of scope for P2.
- Native regression baselines now include fixture-backed warm-session p95 budgets for `fx_add_elf64`, `fx_add_elf32`, `fx_add_arm64`, `fx_add_riscv64`, `fx_add_mips32`, and `fx_switch_elf64`; the switch regression also asserts recovered switch site `0x1009` plus its 9 target addresses.
- `docs/roadmap.md` M2 wording now explicitly distinguishes per-ISA known-function fixtures from the single committed x86_64 jump-table fixture, and tracks the switch fixture's latency budget separately from the priority-ISA perf budgets.
- `CHANGELOG.md` exists at the repo root, follows Keep a Changelog, and must be updated for every release.
- **Next:** resolve the remaining end-of-P2 policy/spec gaps, starting with ADR-006 logging/redaction policy.
- Not a general Ghidra automation framework; decompiler surface only. No UI, no project DB.

# Architecture (3-layer adapter)
1. **Public Contract** — `DecompilerSession` lifecycle + one-shot wrappers (`_session.py`); Python request/result models and error taxonomy in `_models.py` / `_errors.py`.
2. **Bridge Contract** — nanobind C++ extension (`_flatline_native.cpp`, ADR-002) with Python fallback (`_bridge.py`). Pre-validates language/compiler pairs; `.ldefs`-based fallback enumeration when native listing unavailable. Translates public models ↔ native calls. Unstable internal.
3. **Native layer** — Upstream Adapter, wraps Ghidra C++ callable surface; changes absorb upstream drift. 82 upstream C++ sources compiled via Meson (zlib required), linked as `ghidra_decompiler` static lib. Per-request flow: `SleighArchitecture` init, custom `LoadImage`, action reset/perform, `docFunction`, structured `FunctionInfo` extraction.

# Conventions
- **File length:** max ~700 lines; split if exceeded.
- **Spec-first / TDD:** tests precede code.
- **Error model:** hard errors on invalid input; warnings on degraded success; no silent fallbacks.
- **Frozen value copies** — no native pointers cross ABI boundary.
- **C++20** — `default_options: ['cpp_std=c++20']` in root `meson.build`, `-std=c++20` in `src/flatline/meson.build`.
- **Code style:** `docs/code_style.md`.
- **ASCII only** in `.py`, `.cpp`, `.h`, `meson.build`.

# Baseline and policy
- Upstream pin: `Ghidra_12.0.4_build` @ `e40ed13014` (2026-03-03).
- MVP host: Linux x86_64, Python 3.13+, latest-upstream-only.
- MVP ISAs: any Ghidra-supported; priority x86, ARM, RISC-V, MIPS (32/64 each).
- Stable public Python API over unstable upstream internals.
- **Always work in a Python venv.**

# ADR status
- **ADR-001 (Public Scope Model): Option A** — Memory + Architecture + Function-Level. Users provide `memory_image` + `base_address`. Convenience file-to-memory layer deferred post-MVP. Rationale: `docs/specs.md` S5.5.
- **ADR-002 (Bridge Surface): nanobind C++ extension.** Public API stable; bridge internal.
- **ADR-003 (Determinism Oracle): Normalized token/structure comparison**, not canonical text.
- **ADR-004 (Runtime Asset Policy):** Flatline depends on `ghidra-sleigh` for its default runtime-data UX, auto-discovers the installed package when `runtime_data_dir` is omitted, expects the full multi-ISA install by default, and keeps lighter/custom runtime-data roots behind explicit `runtime_data_dir` overrides. No second flatline-side size gate in P2; auto-discovered upstream pin drift emits a warning instead of silently switching baselines.
- **ADR-005 (Analysis Budget Defaults):** Flatline applies a fixed per-request `AnalysisBudget(max_instructions=100000)` default across the Linux MVP matrix, callers may override `max_instructions` explicitly, and the native bridge wires the resolved value into `Architecture::max_instructions`. No wall-clock timeout is exposed in P2 because the pinned Ghidra callable surface does not provide a compatible cancellation hook.
- **ADR-009 (ISA Variant Scope):** x86 32+64; ARM64, RISC-V 64, MIPS32; others best-effort.
- **ADR-010 (Runtime Data Packaging):** Separate `ghidra-sleigh` pip package (repo `patacca/ghidra-sleigh`, import `ghidra_sleigh`). Builds `sleighc` at package build time, ships compiled `.sla` files as package data, and exposes `ghidra_sleigh.get_runtime_data_dir()`. Flatline now layers ADR-004's dependency-backed default policy on top of this mechanism.
- ADR-006 through ADR-008: unresolved (`docs/roadmap.md`).

# Source of truth
- `docs/specs.md` — SDD: API contract, data models, error taxonomy, cross-cutting requirements.
- `docs/roadmap.md` — 7 phases (P0-P6), 6 milestones (M0-M5), risk register, ADR backlog.
- `docs/code_style.md` — naming, formatting, imports, annotations, test conventions.
- `CHANGELOG.md` — release history; update on every release.
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
- `tests/_native_fixtures.py` — committed native fixture catalog, normalized-output baselines, and session helpers.
- `tests/` — catalog, committed fixtures, executable pytest suites, `conftest.py`.
- `tests/fixtures/*.hex` — committed ASCII hex memory images for native integration/regression coverage.
- `tests/fixtures/sources/` + `tests/fixtures/generate_hex_fixtures.py` — authoritative fixture source snippets and regeneration path.
- External companion package: `ghidra-sleigh` (GitHub `patacca/ghidra-sleigh`) provides compiled Sleigh runtime data; it is not vendored in this repo.

# Build & development commands
- **Activate venv:** `source .venv/bin/activate`
- **Always use `tox`** for tests and lint.
- **Editable install:** `pip install -e ".[dev]"`
- **Editable + native forced:** `pip install -e ".[dev]" -Csetup-args=-Dnative_bridge=enabled`
- **Debug build:** `pip install -e ".[dev]" -Csetup-args=-Dbuildtype=debug`
- **Release build:** `pip install -e ".[dev]" -Csetup-args=-Dbuildtype=release`
- Meson buildtype defaults `release` (-O3). Override: `-Csetup-args=-Dbuildtype=<debug|release|debugoptimized>`.
- **Build wheel:** `python -m build`
- **All checks:** `tox` (envs: `py313`, `py314`, `lint`)
- **Tests only:** `tox -e py313,py314`
- **Lint only:** `tox -e lint`
- **Native tests:** `tox -e py313,py314 -- -m requires_native`
- **Single category:** `tox -e py313,py314 -- -m unit` (also: `contract`, `integration`, `regression`, `negative`)
- **Single file:** `tox -e py313,py314 -- tests/unit/test_models.py`
- **Single test:** `tox -e py313,py314 -- tests/unit/test_models.py::test_name -v`
- Tox: `py313`/`py314` build and install `flatline[test]` wheels in `.tox`; `lint` skips package install and runs `ruff` directly. `skip_missing_interpreters = true`.
- `ghidra-sleigh` source-build details live in its own repo; use its documented Meson options there, not from this workspace.

# Tests
- `tox`: `py314` passes all 64 tests (31 unit, 6 contract, 10 integration, 12 regression, 5 negative) against the installed wheel artifact; `py313` skips when `python3.13` is absent.
- Native tests expect compiled `.sla` data from the installed `ghidra-sleigh` runtime dependency, currently covering DATA, x86, AARCH64, RISCV, and MIPS.
- Native tox runs still resolve runtime data from `ghidra_sleigh.get_runtime_data_dir()` explicitly; public `DecompilerSession` startup now auto-discovers that default path when `runtime_data_dir` is omitted, and `DecompileRequest` / `DecompilerSession` coerce path-like `runtime_data_dir` inputs to strings.
- `tests/conftest.py` — auto-applies category markers from directory names.
- `tests/specs/test_catalog.md` — 38 definitions, 5 categories, contract traceability matrix.
- `tests/specs/fixtures.md` — 10 fixtures, oracle strategy, determinism rules.
- `tests/unit/test_native_bridge_runtime_spec.py` — native smoke test uses committed x86_64 add fixture and the real Ghidra runtime-data root.
- `tests/unit/test_runtime_data_spec.py` — `.ldefs` tolerance, dependency-backed default runtime-data discovery, and deterministic failure tests.
- `tests/unit/test_public_contract_spec.py` and `tests/unit/test_bridge_adapter_spec.py` now lock the ADR-005 contract: default `AnalysisBudget(max_instructions=100000)`, mapping coercion/validation, and stable native payload serialization.
- `tests/regression/test_regression_spec.py` — R-002 now asserts the committed switch-site baseline for `fx_switch_elf64`; R-003 now parameterizes warm-session p95 budgets across the priority-ISA add fixtures plus `fx_switch_elf64`.
- `tests/integration/test_integration_spec.py`, `tests/regression/test_regression_spec.py`, and `tests/negative/test_negative_spec.py` now assert against committed native fixtures instead of spec-only skips.

# Vendored upstream
- `third_party/ghidra` — upstream snapshot. `third_party/r2ghidra` — reference integration.
- `.gitmodules` tracks `third_party/ghidra` as the vendored native-source submodule. `third_party/r2ghidra/` is ignored by the parent repo and remains reference-only.
- Read-only unless explicitly asked.

# Key data models (from specs.md)
- `DecompileRequest` — `memory_image`, `base_address`, `function_address`, `language_id`, `compiler_spec`, `runtime_data_dir`, `function_size_hint`, `analysis_budget`.
- `AnalysisBudget` — `max_instructions` (stable P2 field; default `100000` when omitted).
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
