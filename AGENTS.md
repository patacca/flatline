# Maintenance
- Update this file on every repo operation to reflect the current state.
- Keep updates minimal: only facts that save significant re-derivation time for future prompts.

# Overview
- Spec-first Python wrapper around the Ghidra decompiler (no production code yet).
- Phase P0 (Spec Lock) is **in progress**; consistency fixes applied, pending user acceptance to exit P0.

# Baseline and policy
- Upstream pin: `Ghidra_12.0.3_build` @ `09f14c92d3` (2026-02-10).
- MVP host: Linux x86_64, Python 3.13+, latest-upstream-only.
- MVP target ISAs: any Ghidra-supported; priority: x86, ARM, RISC-V, MIPS (32/64-bit each).
- Stable public Python API over unstable upstream internals.

# ADR status
- **ADR-001 (Public Scope Model): DECIDED — Option A** (Memory + Architecture + Function-Level).
  - Users provide `memory_image` + `base_address`, not file paths.
  - Convenience layer (binary file → memory → decompile) deferred to post-MVP.
  - Full rationale in `docs/specs.md` §5.5.
- ADR-002 through ADR-008: unresolved (see `docs/roadmap.md` for schedule).

# Source of truth
- `docs/specs.md` — SDD: API contract, data models, error taxonomy, cross-cutting requirements.
- `docs/roadmap.md` — 7 phases (P0–P6), 5 milestones (M1–M5), risk register, ADR backlog.
- `docs/planning.md` — original brief/requirements.
- `docs/preplanning.md` — discovery constraints and experiment plan (completed).
- `docs/refine_plan.md` — plan refinement checklist and cross-file consistency guide.

# Repo structure (non-vendored)
- `docs/` — specs, roadmap, planning artifacts.
- `notes/api/decompiler_inventory.md` — 18 required callable symbols with inputs/outputs, init order, thread-safety.
- `notes/r2ghidra/integration_map.md` — 5-section integration analysis; classifies each block as reusable / reimplement / skip. Keep as a reference implementation only.
- `tests/` — test catalog, fixture strategy, and pytest skeletons.

# Tests
- All tests are definitions-only; no live integration yet.
- `tests/specs/test_catalog.md` — 24 test definitions across 5 categories (unit, contract, integration, regression, negative).
- `tests/specs/fixtures.md` — fixture strategy with determinism rules and oracle approach.
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
- `VersionInfo` — `ghidralib_version`, `upstream_tag`, `upstream_commit`, `runtime_data_revision`.
- `GhidralibError` — 5 categories: `invalid_argument`, `unsupported_target`, `invalid_address`, `decompile_failed`, `internal_error`.
