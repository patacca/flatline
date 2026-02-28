# Preplanning Doc for `ghidralib` Standalone Python Decompiler

## Summary
Create this document as an execution guide for the discovery phase before implementation.
Scope is a Linux x86_64 MVP that decompiles a single function through Python, using a C-facing shim consumed via `cffi`/`ctypes`, and using plain local clones of upstream repos for analysis (`ghidra`, `r2ghidra`).

## 1. Goal and Non-Goals

### Goal
Identify the minimal callable decompiler API surface from Ghidra's C++ decompiler and define a Python-first wrapper architecture with no radare2 dependency.

### Non-Goals
- Full feature parity with `r2ghidra`.
- Multi-platform support in MVP.
- Batch/whole-program decompilation in MVP.

## 2. Workspace Bootstrap

Run these commands in the repository root:

```bash
git init
mkdir -p third_party docs notes
git clone https://github.com/NationalSecurityAgency/ghidra third_party/ghidra
git clone https://github.com/radareorg/r2ghidra third_party/r2ghidra
mkdir -p notes/api notes/r2ghidra notes/experiments
```

Expected result:
- `third_party/ghidra` exists and is clonable/reproducible.
- `third_party/r2ghidra` exists and is clonable/reproducible.
- Documentation workspace exists under `docs/` and `notes/`.

## 3. Analysis Track A: Ghidra Decompiler API Extraction

Primary target directory:
- `third_party/ghidra/Ghidra/Features/Decompiler/src/decompile/cpp`

Output file:
- `notes/api/decompiler_inventory.md`

Inventory every symbol required for standalone decompilation with one table row per symbol and these columns:
- Symbol name
- File path
- Kind (`class`, `function`, `enum`, `typedef`)
- Inputs/outputs
- Ownership/lifetime model
- Required initialization order
- Error propagation mechanism
- Thread-safety notes
- MVP relevance (`required`, `optional`, `ignore`)

Mandatory first-pass files:
- `ifacedecomp.hh` / `ifacedecomp.cc`
- `architecture.hh` / `architecture.cc`
- `funcdata.hh` / `funcdata.cc`
- `coreaction.hh` / `coreaction.cc`
- `type.hh` / `type.cc`
- `loadimage.hh` / `loadimage.cc`
- `context.hh` / `context.cc`
- `comment.hh` / `comment.cc`
- `prettyprint.hh` / `prettyprint.cc`
- Any additional file exposing decompilation entrypoints

## 4. Analysis Track B: `r2ghidra` Integration Mapping

Inspect `third_party/r2ghidra` and produce:
- `notes/r2ghidra/integration_map.md`

Capture:
- Where `r2ghidra` instantiates decompiler state
- How it provides binary bytes/memory model
- How it builds architecture/context metadata
- How it invokes decompilation
- How it collects text output and errors
- Which parts are radare2 adapters vs generic decompiler glue

For each major integration block, classify as:
- `Reusable as-is`
- `Reimplement in ghidralib`
- `Not needed for MVP`

## 5. Analysis Track C: Minimal Standalone Contract

Define the minimal data contract required to decompile one function.
Output file:
- `notes/api/mvp_contract.md`

Contract checklist:
- Language/processor spec identifier
- Endianness and pointer size
- Address space + function entry address
- Backing bytes provider (`LoadImage` abstraction)
- Symbol/function boundaries (if required)
- Optional calling-convention hints
- Output options (syntax/style)

Include a textual sequence diagram from Python call to decompiled C string.

## 6. Proposed Public Interfaces (Planning Only)

No implementation in this phase; define and freeze interface drafts.

### Python API draft

```python
result = decompile_function(
    binary_path: str,
    function_address: int,
    language_id: str,
    compiler_spec: str | None = None,
    options: DecompileOptions | None = None,
) -> DecompileResult
```

`DecompileResult` fields:
- `c_code: str`
- `warnings: list[str]`
- `error: str | None`
- `metadata: dict[str, Any]` (normalized function address, language info)

### C shim ABI draft

- `ghl_context_create(...) -> ghl_context*`
- `ghl_context_destroy(ghl_context*)`
- `ghl_decompile_function(ghl_context*, uint64_t addr, ghl_result*) -> int`
- `ghl_result_free(ghl_result*)`
- `ghl_last_error(ghl_context*) -> const char*`

Error convention:
- Return `0` on success.
- Return non-zero on failure.
- Retrieve details via `ghl_last_error`.

## 7. Risks and Validation Gates

Track these risks explicitly:
- API instability across upstream Ghidra revisions
- Hidden assumptions in loader/context setup
- C++ exception boundaries crossing C ABI
- Memory ownership and lifetime leaks
- Thread safety of shared decompiler state

Exit criteria for preplanning:
- API inventory completed
- `r2ghidra` call flow mapped end-to-end
- MVP contract written and reviewed
- C shim ABI draft frozen for MVP
- Unknown blockers reduced to explicit experiments

## 8. Experiment Plan (No Product Code Yet)

Create one note per experiment in `notes/experiments/`:
- `E1_compile_driver.md`
- `E2_init_minimal.md`
- `E3_decompile_known_func.md`
- `E4_invalid_address.md`

Each experiment note must contain:
- Exact command
- Expected outcome
- Observed outcome
- Blocker status

## 9. Test Scenarios to Include in Planning

Predefine acceptance tests for later implementation:
- Successful single-function decompilation on Linux x86_64 ELF
- Invalid function address returns structured error
- Unsupported language spec returns structured error
- Repeated decompiles in one process do not leak obvious memory
- Two sequential contexts remain isolated

## 10. Milestones

- `M0`: repo/bootstrap and discovery docs scaffolded
- `M1`: Ghidra API inventory complete
- `M2`: `r2ghidra` mapping complete
- `M3`: MVP contract + C ABI draft complete
- `M4`: implementation-ready technical spec (`docs/implementation-plan.md`)

## Important Public API / Interface Additions
- New Python package contract centered on `decompile_function(...)`
- New C shim ABI (`ghl_*`) as the only FFI boundary
- Standardized `DecompileResult` and structured error model

## Test Cases and Scenarios
- Single-function success path
- Invalid address failure path
- Unsupported architecture/language failure path
- Reuse context for multiple calls
- Context teardown/resource cleanup

## Assumptions and Defaults
- External repos are plain clones under `third_party/`.
- MVP target is Linux x86_64 only.
- MVP scope is one-function decompilation (not batch).
- Initial Python bridge uses `cffi`/`ctypes` over a C ABI shim.
- Upstream code is analyzed in-place; no modifications to vendored repos during preplanning.
