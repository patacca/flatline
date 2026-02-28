# MVP Standalone Contract

## Scope
Single-function decompilation on Linux x86_64 through Python, with a C shim ABI used by `cffi`/`ctypes`.

## Minimal Required Inputs
- Binary source: path to ELF input (`binary_path`)
- Function target: entry address (`function_address`)
- Language spec: Ghidra language id (`language_id`)
- Compiler spec: optional compiler spec id (`compiler_spec`)
- Decompile options: optional syntax/style settings

## Runtime Context Requirements
- Endianness and pointer size must match selected language spec.
- Address space must be correctly initialized before function lookup/decompile.
- Load-image provider must map requested address ranges to backing bytes.
- Function boundary metadata requirements must be documented from API inventory findings.
- Calling convention hints are optional in MVP unless proven required by experiments.

## Output Contract
`DecompileResult`:
- `c_code: str`
- `warnings: list[str]`
- `error: str | None`
- `metadata: dict[str, Any]`

## C Shim ABI Draft
- `ghl_context_create(...) -> ghl_context*`
- `ghl_context_destroy(ghl_context*)`
- `ghl_decompile_function(ghl_context*, uint64_t addr, ghl_result*) -> int`
- `ghl_result_free(ghl_result*)`
- `ghl_last_error(ghl_context*) -> const char*`

Error convention:
- `0` means success.
- Non-zero means failure.
- Human-readable details available through `ghl_last_error`.

## Sequence Diagram (Textual)
1. Python caller invokes `decompile_function(binary_path, function_address, language_id, ...)`.
2. Python FFI layer creates/obtains `ghl_context` via `ghl_context_create(...)`.
3. C shim initializes Ghidra decompiler architecture/context and load-image mapping.
4. Python FFI calls `ghl_decompile_function(ctx, function_address, out_result)`.
5. C shim runs decompiler pipeline and populates `ghl_result`.
6. Python converts `ghl_result` into `DecompileResult`.
7. On error, Python reads `ghl_last_error(ctx)` and sets `DecompileResult.error`.
8. Python calls `ghl_result_free(...)` and eventually `ghl_context_destroy(...)`.
