# Maintenance
- Update this file on every repo operation; keep only facts that save re-derivation time.

# Overview
- `flatline`: pip-installable Python wrapper around the Ghidra C++ decompiler; decompiler surface only, no UI/project DB.
- Release state: P5 complete; version `0.1.0`; release-facing contract/support policy in `docs/release_notes.md`; `CHANGELOG.md` follows Keep a Changelog and updates on every release.
- Next: P6 host-feasibility work is now macOS-first, Windows-second per ADR-008; `docs/host_feasibility.md` records the current audit, the pinned `macos-15` native smoke lane, and the equivalent contract-coverage bar; P7 enriched output remains deferred behind ADR-012.
- Runtime data comes from runtime dependency `ghidra-sleigh` / import `ghidra_sleigh`; omitted `runtime_data_dir` auto-discovers `ghidra_sleigh.get_runtime_data_dir()`, explicit `runtime_data_dir` overrides it, any installed `ghidra-sleigh` is accepted for default runtime data.
- Default asset profile expects full multi-ISA runtime data; lighter roots such as `all_processors=false` are explicit user-managed overrides.
- Version `0.1.0` is aligned in `pyproject.toml`, `meson.build`, and `src/flatline/_version.py`; `pyproject.toml` declares unpinned runtime dependency `ghidra-sleigh` and `license-files = ["LICENSE", "NOTICE"]`.
- `third_party/ghidra` is a git submodule; `third_party/r2ghidra` is a local read-only reference checkout ignored by the parent repo.
- Fixture-backed confidence matrix: x86_64, x86_32, AArch64, RISC-V 64, MIPS32; committed memory fixtures live in `tests/fixtures/*.hex`, sources in `tests/fixtures/sources/`, regen via `tests/fixtures/generate_hex_fixtures.py`.
- Additional committed native fixtures: x86_64 switch and warning cases; regression asserts switch site `0x1009` and 9 target addresses.
- End-to-end decompilation is verified for x86_64 `add(a,b)` with structured output.
- Packaging/test shape: `py313`/`py314` tox envs build/install `flatline[test]` wheels inside `.tox`; `lint` is package-skip + `ruff`; repo-only compliance/footprint/release/artifact tools live in `tools/flatline_dev/` with `tools/*.py` wrappers and are excluded from wheels/sdists by `tools/prune_dist.py`.
- P6 build hardening: `src/flatline/meson.build` now selects warning/include flag syntax through `cpp.get_argument_syntax()` so shared native-build paths no longer assume GCC-style flags before Windows feasibility work starts.
- CI: `.github/workflows/ci.yml` uses `ubuntu-latest` for `lint`/`build`, pinned `macos-15` for native smoke/build evidence, and `ubuntu-24.04` for `test`/`regression`; `test` runs non-regression `py313` + `py314`, `regression` runs `py314`.
- Release publishing: `.github/workflows/release.yml` runs on GitHub `release.published` to PyPI and `workflow_dispatch` to TestPyPI with `skip-existing`.
- Release tooling/docs: `docs/release_workflow.md` records the `0.1.0.dev0` -> `0.1.0` SemVer decision; `docs/release_review.md` is the source-controlled human artifact-review checklist/hold point; `python tools/release.py` audits version/doc alignment and rejects dirty git worktrees before tagging; `python tools/artifacts.py dist` audits built wheel/sdist version/dependency metadata, `LICENSE` / `NOTICE`, and leaked dev tools.
- Redistribution/compliance: root `LICENSE` + `NOTICE`, `docs/compliance.md`, `python tools/compliance.py`; default-install footprint tracked by `python tools/footprint.py` in `docs/footprint.md` at `30,742,876` bytes (`29.32 MiB`) combined payload, `ghidra-sleigh` runtime data `80.3%`.
- Public support messaging distinguishes bundled-ISA enumeration from fixture-backed confidence: x86 32/64, ARM64, RISC-V 64, MIPS32 are fixture-backed; other bundled ISAs/variants are best-effort.

# Design posture
- User-centered library development; prefer the option that makes the caller's life easier.

# Architecture (3-layer adapter)
- Public Contract: `DecompilerSession` lifecycle + one-shot wrappers in `src/flatline/_session.py`; request/result models and error taxonomy in `_models.py` / `_errors.py`.
- Bridge Contract: nanobind extension `src/flatline/_flatline_native.cpp` plus Python fallback `src/flatline/_bridge.py`; pre-validates language/compiler pairs, uses `.ldefs` fallback enumeration when native listing is unavailable, translates public models <-> native calls; unstable internal.
- Native layer: upstream adapter over Ghidra callable surface; 82 upstream C++ sources compiled via Meson into static `ghidra_decompiler` (zlib required); per request `SleighArchitecture` init -> custom `LoadImage` -> action reset/perform -> `docFunction` -> structured `FunctionInfo`.

# Conventions
- File length: max about 700 lines; split when exceeded.
- Spec-first / TDD.
- Error model: hard errors on invalid input; warnings on degraded success; no silent fallbacks.
- Frozen value copies; no native pointers cross ABI boundary.
- C++20: `default_options: ['cpp_std=c++20']` in root `meson.build`; `-std=c++20` in `src/flatline/meson.build`.
- Code style: `docs/code_style.md`.
- ASCII only in `.py`, `.cpp`, `.h`, `meson.build`.

# Baseline and policy
- Vendored decompiler source: `third_party/ghidra` git submodule.
- MVP host: Linux x86_64, Python 3.13+, latest-upstream-only.
- ISA policy: any Ghidra-supported target may enumerate; priority families x86, ARM, RISC-V, MIPS (32/64 each); release-facing fixture-backed variants are x86 32/64, ARM64, RISC-V 64, MIPS32.
- Stable public Python API over unstable upstream internals.
- Always work in a Python venv.

# ADR status
- ADR-001 (Public Scope Model): Option A; users provide `memory_image` + `base_address`; convenience file-to-memory layer deferred post-MVP; rationale in `docs/specs.md` S5.5.
- ADR-002 (Bridge Surface): nanobind C++ extension; public API stable, bridge internal.
- ADR-003 (Determinism Oracle): normalized token/structure comparison, not canonical text.
- ADR-004 (Runtime Asset Policy): default runtime UX depends on `ghidra-sleigh`; omitted `runtime_data_dir` auto-discovers dependency runtime data; full multi-ISA install is the default expectation; lighter/custom roots require explicit `runtime_data_dir`; no second flatline-side size gate in P2.
- ADR-005 (Analysis Budget Defaults): default `AnalysisBudget(max_instructions=100000)`; callers may override `max_instructions`; bridge wires the resolved cap into `Architecture::max_instructions`; unsupported budget keys or non-positive limits fail as `invalid_argument`; no wall-clock timeout in P2.
- ADR-006 (Logging and Diagnostics): P2 emits only startup/runtime-data `RuntimeWarning` messages and structured `WarningItem` / `ErrorItem`; diagnostic text may include full filesystem paths; raw memory-image bytes are never emitted; no public logging sink.
- ADR-007 (License Compliance Process): releases ship root `LICENSE` + `NOTICE`, keep `docs/compliance.md`, pass `python tools/compliance.py`, refresh default-install footprint via `python tools/footprint.py` / `docs/footprint.md`; compliance/footprint/release/artifact helpers live under `tools/flatline_dev` with `tools/*.py` wrappers and are excluded from wheel/sdist artifacts.
- ADR-008 (Cross-Platform Order): resolved to macOS first, then Windows; P6 starts with shared build-system hardening plus source-controlled feasibility findings in `docs/host_feasibility.md`.
- ADR-009 (ISA Variant Scope): x86 32+64; ARM64, RISC-V 64, MIPS32; others best-effort.
- ADR-010 (Runtime Data Packaging): separate `ghidra-sleigh` pip package (repo `patacca/ghidra-sleigh`, import `ghidra_sleigh`); builds `sleighc`, ships compiled `.sla` files as package data, exposes `ghidra_sleigh.get_runtime_data_dir()`; flatline layers ADR-004 on top.
- ADR-011 (Setup Failure Taxonomy): `configuration_error` covers user-fixable install/startup/runtime-data failures; `internal_error` is reserved for unexpected flatline/bridge/native bugs.
- ADR-012 (Enriched Output Design): unresolved; post-MVP pcode ops and varnode graphs as frozen Python types for similarity, diffing, and data flow; needed by P7.

# Source of truth
- `docs/specs.md` — API contract, data models, error taxonomy, cross-cutting requirements.
- `docs/roadmap.md` — phases `P0`-`P7`, milestones `M0`-`M6`, risk register, ADR backlog.
- `docs/code_style.md` — naming, formatting, imports, annotations, test conventions.
- `CHANGELOG.md` — release history; update on every release.
- `docs/ai/planning.md` — original brief/requirements.
- `docs/ai/preplanning.md` — discovery constraints and experiment plan.
- `docs/ai/refine_plan.md` — refinement checklist and cross-file consistency guide.
- `docs/compliance.md` — ADR-007 compliance manifest and redistribution checklist.
- `docs/footprint.md` — default-install footprint baseline and size-policy note.
- `docs/host_feasibility.md` — P6 platform audit, ADR-008 host order, and equivalent host-coverage bar.
- `docs/release_notes.md` — `0.1.0` contract guarantees, support tiers, known-variant limits, upgrade policy.
- `docs/release_review.md` — public artifact-review checklist and external approval hold point.

# Repo structure (non-vendored)
- Build/config: `pyproject.toml`, `.github/workflows/release.yml`, `meson.build`, `src/flatline/meson.build`, `meson_options.txt`.
- Public package: `src/flatline/`; `src/flatline/_session.py`, `src/flatline/_bridge.py`, `src/flatline/_runtime_data.py`, `src/flatline/_flatline_native.cpp`.
- Dev tools: `tools/flatline_dev/`; wrappers `tools/compliance.py`, `tools/footprint.py`, `tools/release.py`, `tools/artifacts.py`.
- Docs/notes: `docs/`, `docs/ai/`, `docs/host_feasibility.md`, `docs/release_notes.md`, `docs/release_review.md`, `docs/release_workflow.md`, `notes/api/decompiler_inventory.md`, `notes/r2ghidra/integration_map.md`.
- Tests/fixtures: `tests/_native_fixtures.py`, `tests/`, `tests/fixtures/*.hex`, `tests/fixtures/sources/`, `tests/fixtures/generate_hex_fixtures.py`.
- External companion package: `ghidra-sleigh` (GitHub `patacca/ghidra-sleigh`) provides compiled Sleigh runtime data and is not vendored in this repo.

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
- Single category: `tox -e py313,py314 -- -m unit` (also: `contract`, `integration`, `regression`, `negative`)
- Single file: `tox -e py313,py314 -- tests/unit/test_models.py`
- Single test: `tox -e py313,py314 -- tests/unit/test_models.py::test_name -v`
- Tox behavior: `py313`/`py314` build/install `flatline[test]` wheels in `.tox`; `dev` skips package install and uses `PYTHONPATH=src:tools`; `lint` skips package install and runs `ruff` over `src/`, `tests/`, `tools/`; `skip_missing_interpreters = true`.
- `ghidra-sleigh` source-build details live in its own repo; use its documented Meson options there, not from this workspace.

# Tests
- Native tests expect compiled `.sla` data from installed `ghidra-sleigh`; current runtime coverage includes DATA, x86, AARCH64, RISCV, and MIPS.
- Native tox runs still resolve runtime data from `ghidra_sleigh.get_runtime_data_dir()` explicitly; public `DecompilerSession` startup auto-discovers that path when `runtime_data_dir` is omitted; `DecompileRequest` and `DecompilerSession` coerce path-like `runtime_data_dir` inputs to strings.
- `tests/conftest.py` auto-applies category markers from directory names.
- Specs: `tests/specs/test_catalog.md` (47 definitions, 5 categories, traceability matrix), `tests/specs/fixtures.md` (10 fixtures, oracle strategy, determinism rules).
- Workflow specs: `tests/unit/test_ci_workflow_spec.py` pins CI runner/env matrix and regression gate; `tests/unit/test_release_ci_workflow_spec.py` pins release publish workflow.
- Runtime/contract specs: `tests/unit/test_native_bridge_runtime_spec.py`, `tests/unit/test_runtime_data_spec.py`, `tests/unit/test_public_contract_spec.py`, `tests/unit/test_bridge_adapter_spec.py` cover real runtime-data smoke, `.ldefs` tolerance/default discovery, ADR-005 budget contract, and ADR-006 full-path diagnostics.
- Release/compliance/devtool specs: `tests/unit/test_compliance_spec.py`, `tests/unit/test_footprint_spec.py`, `tests/unit/test_release_notes_spec.py`, `tests/unit/test_release_review_spec.py`, `tests/unit/test_release_workflow_spec.py`, `tests/unit/test_artifact_audit_spec.py`, `tests/unit/test_devtool_layout_spec.py`; dev-tool module tests skip under tox wheel installs via `pytest.importorskip`.
- Regression/integration/negative specs: `tests/regression/test_regression_spec.py` covers normalized-output switch-site baseline and warm-session p95 budgets across priority-ISA add fixtures plus `fx_switch_elf64`; `tests/integration/test_integration_spec.py` and `tests/negative/test_negative_spec.py` assert committed native fixtures, not spec-only skips.

# Vendored upstream
- `third_party/ghidra` — upstream snapshot.
- `third_party/r2ghidra` — reference integration.
- `.gitmodules` tracks `third_party/ghidra` as the vendored native-source submodule; `third_party/r2ghidra/` stays ignored by the parent repo and read-only unless explicitly asked.

# Key data models (from specs.md)
- `DecompileRequest` — `memory_image`, `base_address`, `function_address`, `language_id`, `compiler_spec`, `runtime_data_dir`, `function_size_hint`, `analysis_budget`.
- `AnalysisBudget` — `max_instructions`; stable P2 field; default `100000` when omitted.
- `DecompileResult` — decompiled C, structured `FunctionInfo`, warnings, error, metadata.
- `FunctionInfo` — name, entry_address, size, is_complete, prototype, local_variables, call_sites, jump_tables, diagnostics, varnode_count.
- `FunctionPrototype` — calling_convention, parameters, return_type, is_noreturn, has_this_pointer, recovery flags.
- `TypeInfo` — name, size, metatype.
- `DiagnosticFlags` — is_complete, has_unreachable_blocks, has_unimplemented, has_bad_data, has_no_code.
- `LanguageCompilerPair` — `language_id`, `compiler_spec`.
- `WarningItem` — `code`, `message`, `phase`.
- `ErrorItem` — `category`, `message`, `retryable`.
- `VersionInfo` — `flatline_version`, `decompiler_version`.
- `FlatlineError` — `invalid_argument`, `unsupported_target`, `invalid_address`, `decompile_failed`, `configuration_error`, `internal_error`.
