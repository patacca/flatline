# Preplanning Doc for `flatline` Standalone Python Decompiler

## Summary
This document defines the discovery-phase plan for a standalone Python library that wraps the Ghidra decompiler.
The MVP targets Linux x86_64, decompiles one function, uses a C ABI consumed by Python (`cffi`/`ctypes`), and is installable via `pip` without requiring a separate Ghidra checkout at runtime.

## 0. Hard Constraints (Must Hold)

### Upstream pin (mandatory)
- MVP discovery is pinned to:
  - Ghidra tag: `Ghidra_12.0.4_build`
  - Ghidra commit: `e40ed13014025f82488b1f8f7bca566894ac376b`
  - Tag commit date: `2026-03-03`
- All analysis notes and experiments must explicitly reference this pin.
- Any later upgrade requires a dedicated revalidation pass (API inventory diff + experiment rerun).

### Distribution model (mandatory)
- `flatline` MVP must be independently installable from `pip`.
- Runtime must not require a full external Ghidra repository.
- MVP ships a curated x86_64 language-spec bundle required for decompilation.

### ABI freeze policy (mandatory)
- During discovery, freeze only ABI principles, not final function signatures.
- Final `ghl_*` function signatures can be frozen only after end-to-end success in E3 and E5.

## 1. Goal and Non-Goals

### Goal
Identify the minimal callable decompiler API surface from Ghidra C++ and define a Python-first standalone architecture with no radare2 dependency.

### Non-Goals
- Full feature parity with `r2ghidra`
- Multi-platform support in MVP
- Whole-program/batch decompilation in MVP

## 2. Analysis Track A: Ghidra Decompiler API Extraction

Primary target:
- `third_party/ghidra/Ghidra/Features/Decompiler/src/decompile/cpp`

Output:
- `notes/api/decompiler_inventory.md`

Inventory columns (one row per symbol):
- Symbol name
- File path
- Kind (`class`, `function`, `enum`, `typedef`)
- Inputs/outputs
- Ownership/lifetime model
- Required initialization order
- Error propagation mechanism
- Thread-safety notes
- MVP relevance (`required`, `optional`, `ignore`)
- Pin reference (must include `Ghidra_12.0.4_build`)

Mandatory first-pass files:
- `ifacedecomp.hh/.cc`
- `architecture.hh/.cc`
- `funcdata.hh/.cc`
- `coreaction.hh/.cc`
- `type.hh/.cc`
- `loadimage.hh/.cc`
- `context.hh/.cc`
- `comment.hh/.cc`
- `prettyprint.hh/.cc`

## 3. Analysis Track B: `r2ghidra` Integration Mapping

Target:
- `third_party/r2ghidra`

Output:
- `notes/r2ghidra/integration_map.md`

Map and classify:
- Decompiler state initialization
- Binary bytes/memory model
- Architecture/context setup
- Decompilation call path
- Text output and error collection
- Radare2 adapters vs generic glue

Required classification per block:
- `Reusable as-is`
- `Reimplement in flatline`
- `Not needed for MVP`

## 4. Analysis Track C: Language / Compiler Spec Sourcing (Required)

Output:
- `notes/api/mvp_contract.md` (authoritative contract)

Must define:
- Where `language_id` and `compiler_spec` values come from
- How valid `(language_id, compiler_spec)` pairs are enumerated
- Required on-disk runtime layout for language specs
- Minimal subset of language resources needed for x86_64

Minimum resource analysis scope:
- `third_party/ghidra/Ghidra/Processors/.../data/languages/`
- `.ldefs`, `.pspec`, `.cspec`, `.slaspec` and compiled outputs needed at runtime

### Runtime data-directory contract
The plan must define:
- Bundled default layout inside package/wheel (primary path)
- Optional override path for development/debug
- How the location is passed to the C layer (context params, not global hidden state)

Default decision for MVP:
- Ship curated x86_64 language bundle in `flatline` package.
- Do not require full Ghidra checkout at runtime.

## 5. Analysis Track D: Function Boundary and CFG Assumptions

MVP behavior must be explicit:
- Default mode: best-effort decompilation from entrypoint.
- Optional hints supported in API contract:
  - function size/end address (if available)
  - symbol/function-boundary metadata (if available)

Best-effort failure modes must be documented and surfaced as structured errors/warnings:
- inability to recover full control-flow/function extent
- unresolved indirect branches/jump tables
- timeout/analysis budget exceeded

Add dedicated validation for hard CFG cases (jump tables/switches).

## 6. Interface Direction (Planning Stage)

### Python API direction (not final)
```python
result = decompile_function(
    binary_path: str,
    function_address: int,
    language_id: str,
    compiler_spec: str | None = None,
    options: DecompileOptions | None = None,
    runtime_data_dir: str | None = None,
    function_size: int | None = None,
) -> DecompileResult
```

`DecompileResult` minimum:
- `c_code: str`
- `warnings: list[str]`
- `error: str | None`
- `metadata: dict[str, Any]`

### C ABI principles (freeze now)
- Pure C boundary (`extern "C"`), no C++ exceptions crossing ABI
- Explicit ownership (`*_free`, `*_destroy`)
- Structured status codes + retrievable error text
- Caller-controlled context/options (no hidden globals)

### C ABI signatures (do **not** freeze yet)
- Keep exact `ghl_context_create`/`ghl_decompile_function` parameters flexible until E3 and E5 complete.
- Prefer a params-struct-based create API to avoid repeated breaking changes.

## 7. Risks and Validation Gates

Track risks:
- Upstream API drift beyond pinned Ghidra revision
- Hidden initialization assumptions in loader/context
- C++ exception leakage across C ABI
- Memory ownership/lifetime leaks
- Thread-safety of shared state
- Incomplete packaged language bundle

Preplanning exit gates:
- API inventory complete at pinned revision
- `r2ghidra` mapping complete
- Language/compiler spec sourcing and runtime bundle layout defined
- MVP function-boundary policy documented with error model
- E3 and E5 successful on pinned revision
- C ABI signatures frozen only after above gates
- Unknown blockers reduced to explicit, tracked experiments

## 8. Experiment Plan (No Product Code Yet)

Create/maintain experiment notes under `notes/experiments/`.

- `E1_compile_driver.md`
  - Build and link minimal standalone driver against selected decompiler components.
- `E2_init_minimal.md`
  - Initialize decompiler with minimal synthetic input.
- `E3_decompile_known_func.md`
  - Decompile one known function successfully.
- `E4_invalid_address.md`
  - Validate structured error path for invalid address.
- `E5_jump_table_switch.md` (new, mandatory)
  - Decompile function containing jump table/switch and record whether extra metadata (size/symbol boundaries) is required.

Each experiment note must contain:
- Exact command
- Expected outcome
- Observed outcome
- Blocker status
- Ghidra pin reference

## 9. Test Scenarios to Predefine for MVP

- Successful single-function decompilation on Linux x86_64 ELF
- Invalid function address returns structured error
- Unsupported language/compiler spec returns structured error
- Enumeration API returns valid bundled `language_id`/`compiler_spec` pairs
- Repeated decompiles in one process do not show obvious leaks
- Sequential contexts remain isolated
- Jump-table/switch case behavior is documented and deterministic

## 10. Milestones

- `M0`: repo/bootstrap and docs scaffolded
- `M1`: pinned API inventory complete (`Ghidra_12.0.4_build`)
- `M2`: `r2ghidra` mapping complete
- `M3`: language-spec sourcing + bundle layout + enumeration plan complete
- `M4`: experiments E1-E5 completed with results on pinned revision
- `M5`: C ABI signatures frozen (post-E3/E5), implementation-ready spec finalized in `docs/implementation-plan.md`

## Important Public API / Interface Additions
- Python contract centered on `decompile_function(...)`
- Runtime language/compiler-spec enumeration capability
- C shim ABI (`ghl_*`) as only FFI boundary
- Structured decompilation result and error model

## Assumptions and Defaults
- External repos are plain clones under `third_party/` for discovery.
- MVP target is Linux x86_64 only.
- MVP scope is single-function decompilation.
- Python bridge uses `cffi`/`ctypes` over C ABI.
- Runtime package bundles required x86_64 language specs (no full Ghidra dependency at runtime).
