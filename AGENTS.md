# Maintenance
- Update on every repo op; keep only facts that save re-derivation.
- Prefer short commit message. One line if possible.

# Overview
- `flatline`: pip-installable Python wrapper around Ghidra C++ decompiler (decompiler surface only).
- Version `0.1.1` aligned in `pyproject.toml`, `meson.build`, `src/flatline/_version.py`; latest public release is `0.1.1`; current repo state matches the public release.
- Roadmap: P6 and P6.5 are closed; TestPyPI validated `0.1.1.dev1`, then production `0.1.1` published successfully on `2026-03-28`; P7 phase-1 landed (opt-in enriched output).
- Docs: GitHub Pages published at `https://patacca.github.io/flatline/` (root redirects to `latest/`); README documents both hosted and local MkDocs access.
- Supported hosts: Linux x86_64, macOS arm64, Windows x86_64; Linux aarch64 + macOS x86_64 = published-wheel targets pending coverage lanes.
- Wheels: 64-bit; manylinux x86_64/aarch64, Windows x86_64, macOS x86_64/arm64; locked in `docs/wheel_matrix.md`.
- Dep `ghidra-sleigh` (import `ghidra_sleigh`); unpinned; auto-discovers runtime data via `ghidra_sleigh.get_runtime_data_dir()`.
- `third_party/ghidra` submodule; `third_party/r2ghidra` read-only, ignored.
- Fixture ISAs: x86_64, x86_32, AArch64, RISC-V 64, MIPS32; `tests/fixtures/*.hex`; regen `tests/fixtures/generate_hex_fixtures.py`; regression switch site `0x1009` + 9 targets.
- Tox: `py313`/`py314` wheel-based; `py314-native` forces `native_bridge=enabled`; `.pkg-py314-native` `pass_env = ["VCPKG_INSTALLATION_ROOT"]`; `lint` = ruff + clang-format; `dev` = source-tree dev-tool tests.
- `--vsenv` via `[tool.meson-python.args]`; do NOT pre-activate MSVC (Meson skips `--vsenv` if `cl.exe`/`VSINSTALLDIR` present); no raw compiler/linker env flags.
- CI (`ci.yml`): py3.14 non-Ubuntu; Ubuntu full matrix py313+py314 incl regression; host-feasibility `tox -e py314-native -- -m "not regression"`; Windows must not use `ilammy/msvc-dev-cmd`; explicit `permissions: contents: read`; all checkout steps set `persist-credentials: false`.
- Security (`zizmor.yml`): push main + PRs `.github/workflows/**` + dispatch; `uvx zizmor --format sarif .`; SARIF category `zizmor`; third-party workflow actions pinned by commit SHA; docs deploy avoids `${{ }}` inside `run` blocks.
- Release (`release.yml`): third-party actions pinned by commit SHA; `pypa/cibuildwheel` version line remains `v3.4.0`; `manylinux_2_28`; Windows vcpkg zlib + delvewheel, no MSVC pre-activation; smoke `tools/flatline_dev/wheel_smoke.py` + `tools/flatline_dev/published_wheel_smoke.py`; sdist compliance; validate with `twine check` + `python tools/artifacts.py dist --repo-root . --require-pypi-metadata`; PyPI on `release.published`, TestPyPI on `workflow_dispatch` (unique version required).
- TestPyPI validated `2026-03-28` commit `299fae580bdb202e0c930878b33067d0eceef01a` run `23694378228`: 10 wheels + 1 sdist, full smoke pass.
- Local clean-snapshot validation `2026-03-28`: `python tools/release.py`, `tox`, `tox -e dev`, `python tools/compliance.py`, `python tools/footprint.py`, `python -m build --outdir dist`, `python tools/artifacts.py dist --repo-root .`, and `python -m twine check dist/*` all passed under the pre-fix metadata gate; built artifacts still omitted the README-backed long description plus project URLs/classifiers/keywords.
- `python tools/release.py`: current staged-release audit (`0.1.1`), rejects dirty worktrees. `python tools/artifacts.py dist`: metadata/LICENSE/NOTICE/dev-tool/native-ext audit; `--require-pypi-metadata` adds README long-description checks for release uploads.
- Compliance: `LICENSE` + `NOTICE`, `docs/compliance.md`, `python tools/compliance.py`; current `.venv` footprint 24,839,137 bytes (23.69 MiB), `ghidra-sleigh` runtime data 99.4%.

# Design posture
- User-centered; prefer caller convenience.
- Only test functional changes; packaging/release-metadata/CI-only fixes use direct build+artifact validation, not new tests, unless they change a durable release/support/native-build contract.

# Architecture (3-layer adapter)
- Public: `DecompilerSession` + one-shot wrappers `_session.py`; models `_models.py`; errors `_errors.py`.
- Enriched output: `EnrichedOutput`, `PcodeOpInfo`, `VarnodeInfo`, `VarnodeFlags`; opt-in; base contract lightweight when omitted.
- Bridge: nanobind `_flatline_native.cpp` + Python fallback `_bridge.py`; pre-validates language/compiler, `.ldefs` fallback; unstable internal.
- Native: 82 upstream .cc via Meson into static `ghidra_decompiler` (zlib required); `SleighArchitecture` -> `LoadImage` -> action reset/perform -> `docFunction` -> `FunctionInfo`; P7 extracts opcode names via `get_opname(op.code())` + varnode use-def edges post-`Action::perform()`.

# Conventions
- Max ~700 lines/file. Spec-first/TDD. ASCII only in `.py`, `.cpp`, `.h`, `meson.build`.
- Hard errors on invalid input; warnings on degraded success; no silent fallbacks.
- Frozen value copies; no native pointers cross ABI.
- Tests: structured format parsing, not grep; workflow tests only for durable release/support/native-build invariants.
- Build UX: no user-facing `CPPFLAGS`/`LDFLAGS`/`PKG_CONFIG_PATH`.
- C++20: `default_options: ['cpp_std=c++20']` root, `-std=c++20` in `src/flatline/meson.build`.
- Style: `docs/code_style.md`.

# Baseline and policy
- Vendored: `third_party/ghidra` submodule.
- MVP: Linux x86_64, Python 3.13+, latest-upstream-only.
- ISA priority: x86/ARM/RISC-V/MIPS 32+64; fixture-backed x86 32/64, ARM64, RISC-V 64, MIPS32; others best-effort.
- Stable public API over unstable internals. Always use venv.

# ADR status
- ADR-001: `memory_image` + `base_address`; file-to-memory deferred.
- ADR-002: nanobind; public stable, bridge internal.
- ADR-003: normalized token/structure comparison.
- ADR-004: `ghidra-sleigh` auto-discovery; full multi-ISA default; explicit `runtime_data_dir` override.
- ADR-005: default `AnalysisBudget(max_instructions=100000)`; bad keys/non-positive -> `invalid_argument`; no wall-clock timeout.
- ADR-006: `RuntimeWarning` + `WarningItem`/`ErrorItem`; paths in diagnostics; no raw bytes; no public logging.
- ADR-007: `LICENSE`+`NOTICE`, compliance tooling, footprint; dev tools excluded from artifacts.
- ADR-008: macOS first, Windows second; `docs/host_feasibility.md`.
- ADR-009: fixture-backed ISAs = x86 32/64, ARM64, RISC-V 64, MIPS32.
- ADR-010: `ghidra-sleigh` (repo `patacca/ghidra-sleigh`); `sleighc`, `.sla`, `get_runtime_data_dir()`.
- ADR-011: `configuration_error` = user-fixable; `internal_error` = flatline bugs.
- ADR-012: P7 enriched output opt-in, post-`Action::perform()`, ID-based pcode/varnode graph.
- ADR-013: CPython >= 3.13, `cibuildwheel`; `manylinux_2_28`; macOS target `11.0`; 32-bit/musllinux/Win ARM64 deferred.

# Source of truth
- `docs/specs.md` -- API contract, models, errors
- `docs/roadmap.md` -- P0-P7 (incl P6.5), M0-M6 (incl M5.5), risks, ADR backlog
- `docs/code_style.md` -- style guide
- `CHANGELOG.md` -- release history
- `docs/ai/planning.md` -- original brief
- `docs/ai/preplanning.md` -- discovery constraints
- `docs/ai/refine_plan.md` -- refinement checklist
- `docs/compliance.md` -- compliance manifest
- `docs/footprint.md` -- footprint baseline
- `docs/host_feasibility.md` -- P6 platform audit
- `docs/release_notes.md` -- `0.1.x` release-line contract, support tiers
- `docs/release_review.md` -- artifact-review checklist
- `docs/wheel_matrix.md` -- wheel matrix, manylinux policy

# Repo structure (non-vendored)
- Build: `pyproject.toml`, `.github/workflows/release.yml`, `meson.build`, `src/flatline/meson.build`, `meson_options.txt`
- Package: `src/flatline/` -- `_session.py`, `_bridge.py`, `_runtime_data.py`, `_flatline_native.cpp`, `_models.py`, `_errors.py`, `_version.py`
- Dev tools: `tools/flatline_dev/`; wrappers `tools/compliance.py`, `tools/footprint.py`, `tools/release.py`, `tools/artifacts.py`; excluded from wheels by `tools/prune_dist.py`
- Tests: `tests/`, `tests/_native_fixtures.py`, `tests/fixtures/*.hex`, `tests/fixtures/sources/`
- Docs: `docs/`, `docs/ai/`; `notes/api/decompiler_inventory.md`, `notes/r2ghidra/integration_map.md`

# Build & development commands
- Activate venv: `source .venv/bin/activate`
- Always use `tox` for tests and lint.
- Editable install: `pip install -e ".[dev]"`
- Editable + native: `pip install -e ".[dev]" -Csetup-args=-Dnative_bridge=enabled`
- Debug build: `pip install -e ".[dev]" -Csetup-args=-Dbuildtype=debug`
- Release build: `pip install -e ".[dev]" -Csetup-args=-Dbuildtype=release`
- Meson default `release` (`-O3`); override `-Csetup-args=-Dbuildtype=<debug|release|debugoptimized>`
- Build wheel: `python -m build`
- Compliance: `python tools/compliance.py`
- Release readiness: `python tools/release.py`
- Footprint: `python tools/footprint.py`
- Artifact audit: `python tools/artifacts.py dist`
- All checks: `tox` (envs: `py313`, `py314`, `lint`; `dev` explicit)
- Tests only: `tox -e py313,py314`
- Dev-only tests: `tox -e dev`
- Lint only: `tox -e lint`
- Native tests: `tox -e py313,py314 -- -m requires_native`
- Native forced bridge: `tox -e py314-native -- -m requires_native`
- Single category: `tox -e py313,py314 -- -m unit` (also: `contract`, `integration`, `regression`, `negative`)
- Single file: `tox -e py313,py314 -- tests/unit/test_models.py`
- Single test: `tox -e py313,py314 -- tests/unit/test_models.py::test_name -v`

# Tests
- Native tests need `.sla` from `ghidra-sleigh`; coverage: DATA, x86, AARCH64, RISCV, MIPS.
- `tests/conftest.py` auto-applies category markers from directory names.
- Specs: `tests/specs/test_catalog.md` (45 defs, 5 categories), `tests/specs/fixtures.md` (10 fixtures).
- Workflow: `test_ci_workflow_spec.py`, `test_native_tox_env_spec.py`, `test_release_ci_workflow_spec.py` -- CI/publish invariants.
- Runtime/contract: `test_native_bridge_runtime_spec.py`, `test_runtime_data_spec.py`, `test_public_contract_spec.py`, `test_bridge_adapter_spec.py` -- runtime smoke, `.ldefs`, ADR-005/006, P7 enriched-output.
- Dev-tool: `test_compliance_spec.py`, `test_footprint_spec.py`, `test_artifact_audit_spec.py`; skip under wheel installs via `pytest.importorskip`.
- Regression/integration/negative: switch-site baseline + p95 budgets; native fixtures incl P7 use-def on `fx_add_elf64`.

# Vendored upstream
- `third_party/ghidra` -- submodule.
- `third_party/r2ghidra` -- read-only reference; ignored.

# Key data models (from specs.md)
- `DecompileRequest` -- `memory_image`, `base_address`, `function_address`, `language_id`, `compiler_spec`, `runtime_data_dir`, `function_size_hint`, `analysis_budget`, `include_enriched_output`
- `AnalysisBudget` -- `max_instructions`; default `100000`
- `DecompileResult` -- decompiled C, `FunctionInfo`, warnings, error, metadata, optional `EnrichedOutput`
- `FunctionInfo` -- name, entry_address, size, is_complete, prototype, local_variables, call_sites, jump_tables, diagnostics, varnode_count
- `FunctionPrototype` -- calling_convention, parameters, return_type, is_noreturn, has_this_pointer, recovery flags
- `TypeInfo` -- name, size, metatype
- `DiagnosticFlags` -- is_complete, has_unreachable_blocks, has_unimplemented, has_bad_data, has_no_code
- `LanguageCompilerPair` -- `language_id`, `compiler_spec`
- `EnrichedOutput` -- `pcode_ops`, `varnodes`
- `PcodeOpInfo` -- `id`, `opcode`, `instruction_address`, `sequence_time`, `sequence_order`, `input_varnode_ids`, `output_varnode_id`
- `VarnodeInfo` -- `id`, `space`, `offset`, `size`, `flags`, `defining_op_id`, `use_op_ids`
- `VarnodeFlags` -- `is_constant`, `is_input`, `is_free`, `is_implied`, `is_explicit`, `is_read_only`, `is_persist`, `is_addr_tied`
- `WarningItem` -- `code`, `message`, `phase`
- `ErrorItem` -- `category`, `message`, `retryable`
- `VersionInfo` -- `flatline_version`, `decompiler_version`
- `FlatlineError` -- `invalid_argument`, `unsupported_target`, `invalid_address`, `decompile_failed`, `configuration_error`, `internal_error`
