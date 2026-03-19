# Maintenance
- Update this file on every repo operation; keep only facts that save re-derivation time.

# Overview
- `flatline`: pip-installable Python wrapper around Ghidra C++ decompiler; decompiler surface only, no UI/project DB.
- Version `0.1.0`; aligned in `pyproject.toml`, `meson.build`, `src/flatline/_version.py`; P5 complete.
- Next: P6.5 wheel matrix in progress (ADR-013); P6 host-feasibility macOS-first (ADR-008); P7 deferred behind ADR-012.
- 64-bit wheel matrix locked in `docs/wheel_matrix.md`: manylinux x86_64/aarch64, Windows x86_64, macOS x86_64/arm64.
- Runtime data: dependency `ghidra-sleigh` (import `ghidra_sleigh`); omitted `runtime_data_dir` auto-discovers via `ghidra_sleigh.get_runtime_data_dir()`; explicit overrides; full multi-ISA default.
- `pyproject.toml`: unpinned `ghidra-sleigh`, `license-files = ["LICENSE", "NOTICE"]`, `cibuildwheel` config, global Meson `setup = ["--vsenv"]` under `[tool.meson-python.args]`.
- `third_party/ghidra` git submodule; `third_party/r2ghidra` local read-only, ignored.
- Fixture-backed ISAs: x86_64, x86_32, AArch64, RISC-V 64, MIPS32; fixtures in `tests/fixtures/*.hex`, sources in `tests/fixtures/sources/`, regen via `tests/fixtures/generate_hex_fixtures.py`; additional x86_64 switch/warning fixtures; regression asserts switch site `0x1009` + 9 targets.
- Tox envs: `py313`/`py314` build wheels in `.tox`; `py314-native` forces `native_bridge=enabled`; Meson `--vsenv` comes from `[tool.meson-python.args]` rather than tox `config_settings_*`; `lint` = `ruff`; dev tools in `tools/flatline_dev/` excluded from wheels by `tools/prune_dist.py`.
- Build hardening: `src/flatline/meson.build` handles compiler flags, Meson include dirs for nanobind, auto-discovers Homebrew/vcpkg `zlib`; `pyproject.toml` globally adds Meson `--vsenv` so isolated Windows package builds can self-bootstrap MSVC; no raw compiler/linker env flags needed.
- CI (`ci.yml`): Python `3.14` for non-Ubuntu jobs; Ubuntu full matrix (`py313`+`py314`); regression `py314`; host-feasibility lanes use `tox -e py314-native -- -m "not regression"`.
- Release (`release.yml`): `cibuildwheel` + `manylinux_2_28`; Windows bootstraps vcpkg zlib; wheel smoke via `tools/flatline_dev/wheel_smoke.py`; sdist with compliance audit; `twine check` + `python tools/artifacts.py`; PyPI on `release.published`, TestPyPI on `workflow_dispatch`.
- Release tooling: `python tools/release.py` audits version/doc alignment, rejects dirty worktrees; `python tools/artifacts.py dist` audits metadata/LICENSE/NOTICE/leaked dev tools/native extensions.
- Compliance: root `LICENSE` + `NOTICE`, `docs/compliance.md`, `python tools/compliance.py`; footprint `30,742,876` bytes (`29.32 MiB`), `ghidra-sleigh` data `80.3%`.
- Support messaging: fixture-backed ISAs vs best-effort bundled; docs distinguish published wheel availability from supported host status.

# Design posture
- User-centered library; prefer caller convenience.
- Only test functional changes.

# Architecture (3-layer adapter)
- Public: `DecompilerSession` + one-shot wrappers in `_session.py`; models in `_models.py`; errors in `_errors.py`.
- Bridge: nanobind `_flatline_native.cpp` + Python fallback `_bridge.py`; pre-validates language/compiler, `.ldefs` fallback enumeration; unstable internal.
- Native: 82 upstream C++ sources via Meson into static `ghidra_decompiler` (zlib required); `SleighArchitecture` init -> `LoadImage` -> action reset/perform -> `docFunction` -> `FunctionInfo`.

# Conventions
- Max ~700 lines per file.
- Spec-first / TDD.
- Hard errors on invalid input; warnings on degraded success; no silent fallbacks.
- Frozen value copies; no native pointers cross ABI boundary.
- Tests: parse structured formats, not grep; no tests for NFC/CI/doc-only changes; workflow tests smoke-check critical behavior only.
- Build UX: no user-facing `CPPFLAGS`/`LDFLAGS`/`PKG_CONFIG_PATH`; hide in build layer.
- C++20: `default_options: ['cpp_std=c++20']` root, `-std=c++20` in `src/flatline/meson.build`.
- Style: `docs/code_style.md`; ASCII only in `.py`, `.cpp`, `.h`, `meson.build`.

# Baseline and policy
- Vendored source: `third_party/ghidra` submodule.
- MVP host: Linux x86_64, Python 3.13+, latest-upstream-only.
- ISA: priority x86/ARM/RISC-V/MIPS 32+64; fixture-backed x86 32/64, ARM64, RISC-V 64, MIPS32; others best-effort.
- Stable public API over unstable internals.
- Always use Python venv.

# ADR status
- ADR-001: Option A; `memory_image` + `base_address`; file-to-memory deferred; `docs/specs.md` S5.5.
- ADR-002: nanobind extension; public stable, bridge internal.
- ADR-003: normalized token/structure comparison, not canonical text.
- ADR-004: `ghidra-sleigh` auto-discovery; full multi-ISA default; explicit `runtime_data_dir` for custom roots; no flatline-side size gate.
- ADR-005: default `AnalysisBudget(max_instructions=100000)`; unsupported keys / non-positive limits -> `invalid_argument`; no wall-clock timeout.
- ADR-006: startup `RuntimeWarning` + structured `WarningItem`/`ErrorItem`; paths in diagnostics; no raw bytes; no public logging sink.
- ADR-007: `LICENSE`+`NOTICE`, `docs/compliance.md`, `python tools/compliance.py`, footprint via `python tools/footprint.py`; dev tools excluded from artifacts.
- ADR-008: macOS first, Windows second; shared build hardening + `docs/host_feasibility.md`.
- ADR-009: x86 32+64, ARM64, RISC-V 64, MIPS32; others best-effort.
- ADR-010: `ghidra-sleigh` (repo `patacca/ghidra-sleigh`, import `ghidra_sleigh`); builds `sleighc`, ships `.sla`, exposes `get_runtime_data_dir()`.
- ADR-011: `configuration_error` = user-fixable; `internal_error` = flatline bugs.
- ADR-012: unresolved; pcode/varnode frozen types for P7.
- ADR-013: CPython `>= 3.13`, `cibuildwheel`; 64-bit: manylinux x86_64 + aarch64, Windows x86_64, macOS x86_64 + arm64; `manylinux_2_28`; macOS target `11.0`; 32-bit/musllinux/Windows ARM64 deferred; `docs/wheel_matrix.md`.

# Source of truth
- `docs/specs.md` — API contract, models, errors.
- `docs/roadmap.md` — P0-P7 (incl P6.5), M0-M6 (incl M5.5), risks, ADR backlog.
- `docs/code_style.md` — naming, formatting, imports, annotations, tests.
- `CHANGELOG.md` — release history; update on every release.
- `docs/ai/planning.md` — original brief.
- `docs/ai/preplanning.md` — discovery constraints.
- `docs/ai/refine_plan.md` — refinement checklist, cross-file consistency.
- `docs/compliance.md` — compliance manifest.
- `docs/footprint.md` — footprint baseline.
- `docs/host_feasibility.md` — P6 platform audit.
- `docs/release_notes.md` — `0.1.0` contract, support tiers, upgrade policy.
- `docs/release_review.md` — artifact-review checklist.
- `docs/wheel_matrix.md` — wheel matrix analysis, manylinux policy.

# Repo structure (non-vendored)
- Build: `pyproject.toml`, `.github/workflows/release.yml`, `meson.build`, `src/flatline/meson.build`, `meson_options.txt`.
- Package: `src/flatline/`; `_session.py`, `_bridge.py`, `_runtime_data.py`, `_flatline_native.cpp`.
- Dev tools: `tools/flatline_dev/`; wrappers `tools/compliance.py`, `tools/footprint.py`, `tools/release.py`, `tools/artifacts.py`.
- Docs: `docs/`, `docs/ai/`; `notes/api/decompiler_inventory.md`, `notes/r2ghidra/integration_map.md`.
- Tests: `tests/`, `tests/_native_fixtures.py`, `tests/fixtures/*.hex`, `tests/fixtures/sources/`, `tests/fixtures/generate_hex_fixtures.py`.
- External: `ghidra-sleigh` (`patacca/ghidra-sleigh`), not vendored.

# Build & development commands
- Activate venv: `source .venv/bin/activate`
- Always use `tox` for tests and lint.
- Editable install: `pip install -e ".[dev]"`
- Editable + native forced: `pip install -e ".[dev]" -Csetup-args=-Dnative_bridge=enabled`
- Debug build: `pip install -e ".[dev]" -Csetup-args=-Dbuildtype=debug`
- Release build: `pip install -e ".[dev]" -Csetup-args=-Dbuildtype=release`
- Meson buildtype default: `release` (`-O3`); override with `-Csetup-args=-Dbuildtype=<debug|release|debugoptimized>`.
- Build wheel: `python -m build`
- Compliance audit: `python tools/compliance.py`
- Release readiness: `python tools/release.py`
- Footprint report: `python tools/footprint.py`
- Artifact audit: `python tools/artifacts.py dist`
- All checks: `tox` (envs: `py313`, `py314`, `lint`; `dev` must be run explicitly)
- Tests only: `tox -e py313,py314`
- Dev-only tests: `tox -e dev` (compliance, footprint, release workflow, artifact audit; runs against source tree, not wheel)
- Lint only: `tox -e lint`
- Native tests: `tox -e py313,py314 -- -m requires_native`
- Native tests with forced bridge: `tox -e py314-native -- -m requires_native`
- Single category: `tox -e py313,py314 -- -m unit` (also: `contract`, `integration`, `regression`, `negative`)
- Single file: `tox -e py313,py314 -- tests/unit/test_models.py`
- Single test: `tox -e py313,py314 -- tests/unit/test_models.py::test_name -v`
- Tox: `py313`/`py314` build wheels; `dev` uses `PYTHONPATH=src:tools`; `lint` runs `ruff` on `src/`, `tests/`, `tools/`; `skip_missing_interpreters = true`.
- `ghidra-sleigh` build details in its own repo.

# Tests
- Native tests need `.sla` data from `ghidra-sleigh`; coverage: DATA, x86, AARCH64, RISCV, MIPS.
- Runtime data resolved via `ghidra_sleigh.get_runtime_data_dir()`; `DecompilerSession` auto-discovers; `DecompileRequest`/`DecompilerSession` coerce path-like inputs.
- `tests/conftest.py` auto-applies category markers from directory names.
- Specs: `tests/specs/test_catalog.md` (49 defs, 5 categories), `tests/specs/fixtures.md` (10 fixtures, oracle strategy).
- Workflow specs: `test_ci_workflow_spec.py`, `test_native_tox_env_spec.py`, `test_release_ci_workflow_spec.py` — smoke-check critical CI/publish invariants incl Tier-1 wheel matrix.
- Runtime/contract specs: `test_native_bridge_runtime_spec.py`, `test_runtime_data_spec.py`, `test_public_contract_spec.py`, `test_bridge_adapter_spec.py` — runtime smoke, `.ldefs` tolerance, ADR-005 budget, ADR-006 diagnostics.
- Release/devtool specs: `test_compliance_spec.py`, `test_footprint_spec.py`, `test_release_notes_spec.py`, `test_release_review_spec.py`, `test_release_workflow_spec.py`, `test_artifact_audit_spec.py`, `test_devtool_layout_spec.py`; dev-tool tests skip under tox wheel installs via `pytest.importorskip`.
- Regression/integration/negative: `test_regression_spec.py` covers switch-site baseline + warm-session p95 budgets across priority ISAs; `test_integration_spec.py` and `test_negative_spec.py` assert committed native fixtures.

# Vendored upstream
- `third_party/ghidra` — submodule; `.gitmodules` tracks it.
- `third_party/r2ghidra` — reference integration. Ignored, read-only unless explicitly asked.

# Key data models (from specs.md)
- `DecompileRequest` — `memory_image`, `base_address`, `function_address`, `language_id`, `compiler_spec`, `runtime_data_dir`, `function_size_hint`, `analysis_budget`.
- `AnalysisBudget` — `max_instructions`; default `100000`.
- `DecompileResult` — decompiled C, `FunctionInfo`, warnings, error, metadata.
- `FunctionInfo` — name, entry_address, size, is_complete, prototype, local_variables, call_sites, jump_tables, diagnostics, varnode_count.
- `FunctionPrototype` — calling_convention, parameters, return_type, is_noreturn, has_this_pointer, recovery flags.
- `TypeInfo` — name, size, metatype.
- `DiagnosticFlags` — is_complete, has_unreachable_blocks, has_unimplemented, has_bad_data, has_no_code.
- `LanguageCompilerPair` — `language_id`, `compiler_spec`.
- `WarningItem` — `code`, `message`, `phase`.
- `ErrorItem` — `category`, `message`, `retryable`.
- `VersionInfo` — `flatline_version`, `decompiler_version`.
- `FlatlineError` — `invalid_argument`, `unsupported_target`, `invalid_address`, `decompile_failed`, `configuration_error`, `internal_error`.
