# Maintenance
- Update only when repo instructions or durable project facts change; do not touch this file for routine code, CI, dependency-pin, or scanner-remediation edits.
- Prefer short commit message. One line if possible.
- **NEVER use `git add -f` / `--force` to override `.gitignore`.**

# Overview
- `flatline`: pip-installable Python wrapper around Ghidra C++ decompiler (surface only).
- Version `0.1.3.dev0` in `pyproject.toml`, `meson.build`, `src/flatline/_version.py`.
- Latest public release: `0.1.2`.
- Enriched output: `Enriched.pcode` + `Pcode.to_graph()` for graph traversal/drawing.
- Utility: `src/flatline/xray/` ships `flatline-xray` / `python -m flatline.xray` (tkinter pcode viewer).
- Docs: `https://patacca.github.io/flatline/`; README covers local MkDocs access.
- Hosts: Linux x86_64, macOS arm64, Windows x86_64 (Tier 1); Linux aarch64, macOS x86_64 (Pending).
- Wheels: CPython 3.13/3.14, 64-bit; manylinux x86_64/aarch64, Windows x86_64, macOS x86_64/arm64.
- Deps: `ghidra-sleigh` (runtime data), `networkx` (pcode graph); `ghidra_sleigh.get_runtime_data_dir()`.
- Submodules: `third_party/ghidra` (active); `third_party/r2ghidra` (ignored).
- Fixture ISAs: x86_64, x86_32, AArch64, RISC-V 64, MIPS32; `tests/fixtures/*.hex`.

# Design posture
- User-centered; focus on user convenience.
- Only test functional changes; packaging/CI fixes use direct artifact validation instead of new tests, unless they change a durable release/support/native-build contract.

# Architecture (3-layer adapter)
- Public: `DecompilerSession` + one-shot wrappers `_session.py`; `models/`; `_errors.py`.
- Enriched: `Enriched` -> `Pcode`; `PcodeOpInfo`, `VarnodeInfo`, `VarnodeFlags`.
- `Pcode` keeps raw values, O(1) ID lookup, `to_graph()` returns `networkx.MultiDiGraph`.
- Bridge: nanobind `native/module.cpp` + Python fallback `bridge/core.py`; pre-validates language/compiler, `.ldefs` fallback; unstable internal.
- Native: 82 upstream .cc via Meson into static `ghidra_decompiler` (zlib required).
- Flow: `SleighArchitecture` -> `LoadImage` -> action perform -> `docFunction` -> `FunctionInfo`.

# Conventions
- Max 600 lines/file (except docs). Contract-first/TDD. ASCII-only in source/build files.
- Use code comments extensively to explain concepts, intent, and non-obvious logic; save re-derivation time and reduce documentation burden.
- Clear tree structure and self-explanatory names for files, modules, classes, functions, variables.
- Python: ALWAYS guard type-hint imports behind `if TYPE_CHECKING:`.
- Hard errors on invalid input; warnings on degraded success; no silent fallbacks.
- Frozen value copies; no native pointers cross ABI.
- Tests: structured format parsing, not grep; workflow tests only for durable release/support/native-build invariants.
- Build UX: no user-facing `CPPFLAGS`/`LDFLAGS`/`PKG_CONFIG_PATH`.
- CI: Windows must not use `ilammy/msvc-dev-cmd`; all checkout steps set `persist-credentials: false`; explicit `permissions: contents: read`.
- Use C++20 std
- Coding style: `docs/code_style.md`

# Baseline and policy
- Vendored: `third_party/ghidra` submodule.
- ISA priority: x86/ARM/RISC-V/MIPS 32+64; fixture-backed x86 32/64, ARM64, RISC-V 64, MIPS32.
- Stable public API over unstable internals. Always use venv.

# Source of truth
- `docs/design.md`: durable posture, boundaries, heuristics, risks.
- `docs/adr/`: accepted architecture decision records.
- `docs/TODO.md`: next-scope features, platform expansion, open work.
- `docs/archived/`: archived historical docs; **PERMANENTLY READ-ONLY**.
- `docs/code_style.md`: coding style guide.
- `CHANGELOG.md`: release history; **NEVER modify dated release entries**.
- `mkdocs.yml` + `docs-site/`: documentation site structure.
- `docs/ai/`: active AI working docs.
- `NOTICE`: attribution pointers; `LICENSE`: root license.
- `docs/release_notes.md`: `0.1.x` contract; `docs/release_review.md`: checklist.
- `docs/release_workflow.md`: operator steps; `docs/adr/adr-013.md`: wheel policy.

# Repo structure (non-vendored)
- Build: `pyproject.toml`, `mkdocs.yml`, `.github/workflows/`, `meson.build`, `src/flatline/meson.build`, `meson_options.txt`.
- Package: `src/flatline/`: `_session.py`, `bridge/`, `runtime/`, `models/`, `native/`, `xray/`, `_errors.py`, `_version.py`.
- Dev tools: `tools/flatline_dev/`; `compliance.py`, `footprint.py`, `release.py`, `artifacts.py`.
- Tests: `tests/`, `tests/_native_fixtures.py`, `tests/fixtures/*.hex`, `tests/fixtures/sources/`.
- Docs: `docs/`, `docs-site/`, `docs/ai/`, `docs/plans/`, `notes/`.

# Build & development commands
- **Run ALL Python commands inside the venv**: `source .venv/bin/activate` first, then `python`, `pip`, `tox`, etc. No exceptions.
- Editable: `pip install -e ".[dev]"`.
- Native: `pip install -e ".[dev]" -Csetup-args=-Dnative_bridge=enabled`.
- Build types: `-Csetup-args=-Dbuildtype=<debug|release|debugoptimized>`.
- Windows: `--vsenv` via `[tool.meson-python.args]`; do NOT pre-activate MSVC (Meson skips `--vsenv` if `cl.exe`/`VSINSTALLDIR` present).
- Wheel: `python -m build`.
- Audit: `python tools/compliance.py`, `python tools/release.py`, `python tools/footprint.py`.
- Artifacts: `python tools/artifacts.py dist`.
- Tox: `tox` (py313, py314, lint); `tox -e py314-native` (native bridge).
- **MUST run full tox before claiming any feature complete**: `tox`
- Tests: `tox -e py313,py314 -- -m <unit|contract|integration|regression|negative>`.
- Native tests: `tox -e py313,py314 -- -m requires_native`.
- Single file: `tox -e py313,py314 -- tests/unit/test_bridge_adapter_spec.py`.
- Single test: `tox -e py313,py314 -- tests/unit/test_bridge_adapter_spec.py::test_name -v`.

# Tests
- Native tests require `.sla` from `ghidra-sleigh`; covers DATA, x86, AARCH64, RISCV, MIPS.
- Category markers auto-applied via `tests/conftest.py`.
- Specs: `tests/specs/test_catalog.md` (52 defs, 5 categories), `tests/specs/fixtures.md` (10 fixtures).
- Workflow: `test_ci_workflow_spec.py`, `test_native_tox_env_spec.py`, `test_release_ci_workflow_spec.py`.
- Runtime: `test_native_bridge_runtime_spec.py`, `test_runtime_data_spec.py`, `test_public_contract_spec.py`, `test_bridge_adapter_spec.py`.
- Dev-tool: `test_compliance_spec.py`, `test_footprint_spec.py`, `test_artifact_audit_spec.py`; skip under wheel installs via `pytest.importorskip`.
- Integration: switch-site baseline + p95 budgets; `fx_add_elf64` graph reachability.
- **NEVER write tautological tests**: tests that merely restate the implementation without asserting meaningful behavior.

# Vendored upstream
- `third_party/ghidra` (submodule).
- `third_party/r2ghidra` (read-only reference; ignored).

# Key data models
- `DecompileRequest`: `memory_image`, `base_address`, `function_address`, `language_id`, `compiler_spec`, `runtime_data_dir`, `function_size_hint`, `analysis_budget`, `enriched`, `tail_padding`.
- `AnalysisBudget`: `max_instructions` (default `100000`).
- `DecompileResult`: C code, `FunctionInfo`, warnings, error, metadata, `Enriched`.
- `FunctionInfo`: name, entry_address, size, is_complete, prototype, local_variables, call_sites, jump_tables, diagnostics, varnode_count.
- `FunctionPrototype`: calling_convention, parameters, return_type, is_noreturn, has_this_pointer, recovery flags.
- `TypeInfo`: name, size, metatype.
- `DiagnosticFlags`: is_complete, has_unreachable_blocks, has_unimplemented, has_bad_data, has_no_code.
- `LanguageCompilerPair`: `language_id`, `compiler_spec`.
- `Enriched`: `pcode`, `instructions`.
- `Pcode`: `pcode_ops`, `varnodes`; `get_pcode_op()`, `get_varnode()`, `to_graph()`.
- `PcodeOpInfo`: `id`, `opcode`, `instruction_address`, `sequence_time`, `sequence_order`, `input_varnode_ids`, `output_varnode_id`.
- `VarnodeInfo`: `id`, `space`, `offset`, `size`, `flags`, `defining_op_id`, `use_op_ids`.
- `VarnodeFlags`: `is_constant`, `is_input`, `is_free`, `is_implied`, `is_explicit`, `is_read_only`, `is_persist`, `is_addr_tied`.
- `WarningItem`: `code`, `message`, `phase`.
- `ErrorItem`: `category`, `message`, `retryable`.
- `VersionInfo`: `flatline_version`, `decompiler_version`.
- `FlatlineError`: `invalid_argument`, `unsupported_target`, `invalid_address`, `decompile_failed`, `configuration_error`, `internal_error`.
