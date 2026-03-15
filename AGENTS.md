# Maintenance
- Update this file on every repo operation; only facts that save re-derivation time.

# Overview
- Pip-installable Python wrapper around the Ghidra C++ decompiler, consuming packaged runtime assets from `ghidra-sleigh`. Multi-ISA.
- **Phase P5 (Initial public release) — in progress.** P0-P4 deliverables are committed locally; initial public release notes/support policy now live in `docs/release_notes.md`.
- `.sla` runtime data now comes from the `ghidra-sleigh` runtime dependency (pip name) / `ghidra_sleigh` (import); default build ships all processor families, lighter build uses `all_processors=false`.
- `pyproject.toml` now pins `ghidra-sleigh == 12.0.4` to match the vendored `Ghidra_12.0.4_build` native baseline.
- Flatline version strings are now normalized to the PEP 440 form `0.1.0.dev0` across `pyproject.toml`, `meson.build`, and `src/flatline/_version.py`.
- `third_party/ghidra` is now tracked by the top-level repo as a git submodule pinned to `Ghidra_12.0.4_build` / `e40ed13014025f82488b1f8f7bca566894ac376b`; `third_party/r2ghidra` remains a local read-only reference checkout ignored by the parent repo.
- End-to-end decompilation verified: x86_64 `add(a,b)` produces correct C output with full structured data.
- Priority-ISA native memory fixtures are now committed as `tests/fixtures/*.hex`: x86_64, x86_32, AArch64, RISC-V 64, MIPS32, plus x86_64 switch and warning fixtures.
- Fixture sources now live beside the artifacts under `tests/fixtures/sources/`, with regeneration scripted in `tests/fixtures/generate_hex_fixtures.py`.
- Tox now tests the installed package artifact: `py313`/`py314` build `flatline[test]` wheels inside `.tox`, while `lint` remains package-skip + `ruff`.
- Wheels and sdists ship only the public runtime modules and optional native extension. Repo-only release tools now live under `tools/flatline_dev/` with `tools/*.py` wrappers; `tools/prune_dist.py` removes that tree from sdists, wheels never install it, and dev-tool tests still skip gracefully under tox wheel installs via `pytest.importorskip`.
- GitHub Actions CI uses `ubuntu-latest` for lint/build and pins `ubuntu-24.04` for perf-sensitive test/regression lanes; the general test lane runs non-regression tox envs across Python 3.13/3.14 and a dedicated `py314` regression lane enforces the committed normalized-output and warm-session p95 budgets.
- Public sessions now auto-discover `ghidra_sleigh.get_runtime_data_dir()` when `runtime_data_dir` is omitted; explicit `runtime_data_dir` values still override the default, and auto-discovered Ghidra pin drift is surfaced as a runtime warning.
- ADR-005 is now resolved: `AnalysisBudget` is a public frozen value type, omitted requests default to `max_instructions=100000`, mapping inputs are coerced/validated in `DecompileRequest`, and the native bridge applies the resolved cap to `Architecture::max_instructions`. Unsupported budget keys or non-positive limits fail as `invalid_argument`; wall-clock timeout remains out of scope for P2.
- ADR-006 is now resolved: P2 emits diagnostics only through startup/runtime-data `RuntimeWarning` messages and structured `WarningItem` / `ErrorItem` payloads; diagnostic text includes full filesystem paths for debuggability, raw memory-image bytes are never emitted, and P2 exposes no public logging sink.
- Persona/UX contract cleanup is now applied in `docs/specs.md` / `docs/roadmap.md`: top-level scope language distinguishes bundled-ISA breadth from fixture-backed confidence (x86 32/64, ARM64, RISC-V 64, MIPS32), release planning now requires public support-tier / known-variant notes, and package-size planning preserves the one-package default UX unless an explicit product/compliance decision changes it.
- ADR-011 is now resolved: public error taxonomy adds `configuration_error` for user-fixable install/startup/runtime-data failures (missing/bad `runtime_data_dir`, missing default `ghidra-sleigh` runtime data, malformed runtime-data roots), while `internal_error` remains reserved for unexpected flatline/bridge/native bugs.
- ADR-007 is now resolved: release redistribution checks require root `LICENSE` + `NOTICE`, a pinned-source compliance manifest in `docs/compliance.md`, and a passing `python tools/compliance.py` audit covering the Ghidra attribution files, `ghidra-sleigh == 12.0.4`, and the fixture redistribution note.
- Default-install footprint is now measured by `python tools/footprint.py`; `docs/footprint.md` records the current `.tox/py314` installed-wheel baseline at `30,758,692` bytes (`29.33 MiB`) combined payload, with `ghidra-sleigh` runtime data contributing `80.3%`.
- Native regression baselines now include fixture-backed warm-session p95 budgets for `fx_add_elf64`, `fx_add_elf32`, `fx_add_arm64`, `fx_add_riscv64`, `fx_add_mips32`, and `fx_switch_elf64`; the switch regression also asserts recovered switch site `0x1009` plus its 9 target addresses.
- `docs/roadmap.md` M2 wording now explicitly distinguishes per-ISA known-function fixtures from the single committed x86_64 jump-table fixture, and tracks the switch fixture's latency budget separately from the priority-ISA perf budgets.
- `pyproject.toml` now declares `license-files = ["LICENSE", "NOTICE"]`, and `README.md` now points redistribution guidance at those artifacts while matching the actual fixture-backed confidence matrix (x86 32/64, ARM64, RISC-V 64, MIPS32; others best-effort).
- `CHANGELOG.md` exists at the repo root, follows Keep a Changelog, and must be updated for every release.
- `docs/release_notes.md` now captures the initial public release-facing contract guarantees, support tiers, known-variant limits, and upgrade policy; `README.md` links it and now tracks P5 as the current focus.
- `docs/release_workflow.md` now records the initial public release procedure and the first-release SemVer recommendation: finalize `0.1.0.dev0` as `0.1.0`; `python tools/release.py` audits version/doc alignment and rejects dirty git worktrees before tagging because Meson sdists omit uncommitted changes.
- `docs/release_review.md` now captures the source-controlled public artifact-review checklist plus a release-candidate record template (reviewed git commit, artifact filenames, deterministic command outcomes, approval status) for the final human P5 sign-off; `python tools/release.py` now requires that stronger review doc alongside the release notes/workflow links.
- `python tools/artifacts.py dist` now audits built wheel/sdist artifacts for shipped `LICENSE` / `NOTICE`, current version metadata, the pinned `ghidra-sleigh == 12.0.4` dependency, and accidental dev-tool leakage before the human public-artifact review sign-off.
- `pip install -e ".[dev]"` now installs `build >= 1.2`, so the documented `python -m build` release step works from the standard repo venv without extra manual tooling setup.
- **Next:** once `docs/release_review.md` is completed and approved, run the documented initial public release workflow, bump to `0.1.0`, and create tag `v0.1.0`.
- Post-MVP P7 will expose pcode ops and varnode graphs as frozen Python value types for downstream analysis (BSim-style similarity, binary diffing, data flow/taint). Design tracked in ADR-012.
- Not a general Ghidra automation framework; decompiler surface only. No UI, no project DB.

# Design posture
- **User-centered library development.** Every feature, default, error message, and API surface is designed from the caller's perspective first. The library exists to serve its users; no design decision should work against them or force them to fight the API. When in doubt, choose the option that makes the user's life easier.

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
- **ADR-006 (Logging and Diagnostics):** P2 emits diagnostics only through startup/runtime-data `RuntimeWarning` messages and structured `WarningItem` / `ErrorItem` payloads. Diagnostic text includes full filesystem paths for debuggability; raw memory-image bytes are never emitted. No general-purpose logging sink is exposed in P2.
- **ADR-007 (License Compliance Process):** releases ship root `LICENSE` + `NOTICE`, keep the pinned source/dependency references in `docs/compliance.md`, pass `python tools/compliance.py`, and now keep the default-install footprint baseline refreshed in `docs/footprint.md` via `python tools/footprint.py`. The compliance/footprint/release/artifact-audit tools now live under `tools/flatline_dev` with repo-only wrappers in `tools/`, excluded from distribution artifacts (wheels and sdists).
- **ADR-008 (Cross-Platform Order):** unresolved (`docs/roadmap.md`).
- **ADR-009 (ISA Variant Scope):** x86 32+64; ARM64, RISC-V 64, MIPS32; others best-effort.
- **ADR-010 (Runtime Data Packaging):** Separate `ghidra-sleigh` pip package (repo `patacca/ghidra-sleigh`, import `ghidra_sleigh`). Builds `sleighc` at package build time, ships compiled `.sla` files as package data, and exposes `ghidra_sleigh.get_runtime_data_dir()`. Flatline now layers ADR-004's dependency-backed default policy on top of this mechanism.
- **ADR-011 (Setup Failure Taxonomy):** `configuration_error` covers user-fixable install/startup/runtime-data failures; `internal_error` is reserved for unexpected flatline/bridge/native bugs.
- **ADR-012 (Enriched Output Design):** unresolved; post-MVP. Pcode ops and varnode data flow graphs as frozen Python types for similarity, diffing, and data flow analysis. Needed by P7.

# Source of truth
- `docs/specs.md` — SDD: API contract, data models, error taxonomy, cross-cutting requirements.
- `docs/roadmap.md` — 8 phases (P0-P7), 7 milestones (M0-M6), risk register, ADR backlog.
- `docs/code_style.md` — naming, formatting, imports, annotations, test conventions.
- `CHANGELOG.md` — release history; update on every release.
- `docs/ai/compact_agent.md` — compact prompt template for lossless AGENTS.md compression.
- `docs/ai/planning.md` — original brief/requirements.
- `docs/ai/preplanning.md` — discovery constraints and experiment plan (completed).
- `docs/ai/refine_plan.md` — plan refinement checklist and cross-file consistency guide.
- `docs/compliance.md` — ADR-007 compliance manifest + redistribution checklist.
- `docs/footprint.md` — default-install footprint baseline and size-policy note.
- `docs/release_notes.md` — initial public release notes: contract guarantees, support tiers, known-variant limits, and upgrade policy.
- `docs/release_review.md` — public artifact-review checklist and approval record template for the initial public release gate.

# Repo structure (non-vendored)
- `pyproject.toml` — metadata, tool settings. Build backend: `meson-python`.
- `meson.build` (root) + `src/flatline/meson.build` — build definitions.
- `meson_options.txt` — feature flags (`native_bridge`).
- `src/flatline/` — installable package (src layout).
- `src/flatline/_session.py` — `DecompilerSession` lifecycle + one-shot wrappers.
- `src/flatline/_bridge.py` — bridge session protocol + fallback implementation.
- `src/flatline/_runtime_data.py` — runtime-data discovery/validation for language/compiler pair enumeration.
- `src/flatline/_flatline_native.cpp` — nanobind extension: Ghidra startup, pair enumeration, native decompile pipeline (links `ghidra_decompiler`).
- `tools/flatline_dev/` — repo-only Python package for compliance, footprint, release-readiness, and artifact-audit logic; never shipped in wheel/sdist.
- `tools/compliance.py`, `tools/footprint.py`, `tools/release.py`, `tools/artifacts.py` — repo-only wrappers for the dev-tool CLIs.
- `docs/` — specs, roadmap, project documentation.
- `docs/ai/` — agent prompts, planning artifacts, workflow templates.
- `docs/release_notes.md` — initial public release notes and support-policy summary.
- `docs/release_review.md` — public artifact-review checklist and approval record template.
- `docs/release_workflow.md` — initial public release workflow, hold point, and `0.1.0` SemVer recommendation.
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
- **Compliance audit:** `python tools/compliance.py`
- **Release readiness:** `python tools/release.py`
- **Footprint report:** `python tools/footprint.py`
- **Artifact audit:** `python tools/artifacts.py dist`
- **All checks:** `tox` (envs: `py313`, `py314`, `dev`, `lint`)
- **Tests only:** `tox -e py313,py314`
- **Dev-only tests:** `tox -e dev` (compliance, footprint, release workflow, artifact audit — runs against source tree, not wheel)
- **Lint only:** `tox -e lint`
- **Native tests:** `tox -e py313,py314 -- -m requires_native`
- **Single category:** `tox -e py313,py314 -- -m unit` (also: `contract`, `integration`, `regression`, `negative`)
- **Single file:** `tox -e py313,py314 -- tests/unit/test_models.py`
- **Single test:** `tox -e py313,py314 -- tests/unit/test_models.py::test_name -v`
- Tox: `py313`/`py314` build and install `flatline[test]` wheels in `.tox`; `dev` skips package install and uses `PYTHONPATH=src:tools` to test repo-only dev modules against the source tree; `lint` skips package install and runs `ruff` directly over `src/`, `tests/`, and `tools/`. `skip_missing_interpreters = true`.
- `ghidra-sleigh` source-build details live in its own repo; use its documented Meson options there, not from this workspace.

# Tests
- Latest dev-tool separation verification: with `MESONPY_EDITABLE_SKIP=/home/patacca/patacca_git/flatline/build/cp314` and `PYTHONPATH=src:tools`, 14 focused unit tests passed, `ruff check src/ tests/ tools/` passed, `python -m build --outdir /tmp/flatline-dist-check` succeeded, and `python tools/artifacts.py /tmp/flatline-dist-check --repo-root .` passed.
- Native tests expect compiled `.sla` data from the installed `ghidra-sleigh` runtime dependency, currently covering DATA, x86, AARCH64, RISCV, and MIPS.
- Native tox runs still resolve runtime data from `ghidra_sleigh.get_runtime_data_dir()` explicitly; public `DecompilerSession` startup now auto-discovers that default path when `runtime_data_dir` is omitted, and `DecompileRequest` / `DecompilerSession` coerce path-like `runtime_data_dir` inputs to strings.
- `tests/conftest.py` — auto-applies category markers from directory names.
- `tests/specs/test_catalog.md` — 44 definitions, 5 categories, contract traceability matrix.
- `tests/specs/fixtures.md` — 10 fixtures, oracle strategy, determinism rules.
- `tests/unit/test_ci_workflow_spec.py` — locks the pinned GitHub Actions regression gate (runner pin, py313/py314 non-regression matrix, dedicated `py314` regression lane).
- `tests/unit/test_native_bridge_runtime_spec.py` — native smoke test uses committed x86_64 add fixture and the real Ghidra runtime-data root.
- `tests/unit/test_runtime_data_spec.py` — `.ldefs` tolerance, dependency-backed default runtime-data discovery, and deterministic failure tests.
- `tests/unit/test_compliance_spec.py` — ADR-007 compliance audit for required notice files, pinned-source references, and dependency-pin drift. Skips under tox (dev-only module).
- `tests/unit/test_footprint_spec.py` — default-install footprint measurement excludes `__pycache__` noise and keeps `docs/footprint.md` pinned to the current workflow/policy. Skips under tox (dev-only module).
- `tests/unit/test_release_notes_spec.py` — locks the initial public release notes doc and README against the P5 gate: contract guarantees, support tiers, known-variant limits, upgrade policy, and current-phase messaging.
- `tests/unit/test_release_review_spec.py` — locks the source-controlled public artifact-review checklist against the P5 gate: required readiness commands, artifact evidence, notices, release-doc references, and approval-record fields.
- `tests/unit/test_release_workflow_spec.py` — locks the initial public release workflow and SemVer recommendation: `0.1.0.dev0` finalizes to `0.1.0`, README links the workflow doc, and missing workflow docs or version drift fail deterministically. Skips under tox (dev-only module).
- `tests/unit/test_artifact_audit_spec.py` — built wheel/sdist audit for shipped notices plus current version and dependency metadata. Skips under tox (dev-only module).
- `tests/unit/test_devtool_layout_spec.py` — locks the repo-only dev-tool layout: `tools/flatline_dev` plus `tools/*.py` wrappers exist, and `src/flatline` contains no dev-only release helpers.
- `tests/unit/test_public_contract_spec.py` and `tests/unit/test_bridge_adapter_spec.py` now lock the ADR-005 contract: default `AnalysisBudget(max_instructions=100000)`, mapping coercion/validation, and stable native payload serialization.
- `tests/unit/test_runtime_data_spec.py` and `tests/unit/test_bridge_adapter_spec.py` now also lock ADR-006 diagnostics: startup/runtime-data warnings and bridge error messages include full filesystem paths for debuggability.
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
- `VersionInfo` — `flatline_version`, `upstream_tag`, `upstream_commit`.
- `FlatlineError` — 6 categories: `invalid_argument`, `unsupported_target`, `invalid_address`, `decompile_failed`, `configuration_error`, `internal_error`.
