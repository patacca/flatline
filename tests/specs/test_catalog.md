# Test Catalog

All tests below are definitions-only for now. Each item includes purpose, fixtures, steps,
assertions, oracle strategy, and determinism constraints.

## 1. Unit Tests

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| U-001 | Validate request schema rejects missing required fields | None | Build request objects with omitted required fields | Structured `invalid_argument` classification | Schema/error-category oracle | Error category stable; message text may vary |
| U-002 | Validate unknown compiler id handling | None | Provide compiler id not in enumerated set | Hard error, not fallback | Category + code oracle | Never silently substitute default compiler |
| U-003 | Validate metadata envelope shape | None | Build synthetic result object from adapter stub | Required metadata keys present | Key-presence oracle | Required keys invariant across releases |
| U-004 | Validate function_size_hint passthrough | None | Build request with and without function_size_hint | Hint value is available to bridge layer; omission does not error | Presence/absence oracle | Advisory field; never causes hard error when omitted |
| U-005 | Validate FunctionInfo fields from stub | None | Build synthetic FunctionInfo from adapter stub with known values | All required fields present with correct types; DiagnosticFlags aggregation correct | Field-presence + type oracle | Required fields invariant across releases |
| U-006 | Validate analysis_budget passthrough | None | Build request with and without analysis_budget | Budget value is available to bridge layer; omission does not error | Presence/absence oracle | Advisory field; never causes hard error when omitted |
| U-007 | Validate session lifecycle semantics | None | Open/close a DecompilerSession via context manager and explicit close | Session closes deterministically and close() is idempotent | Lifecycle-state oracle | Closed state transitions are deterministic |
| U-008 | Validate closed-session rejection behavior | None | Close session, then call list/decompile methods | Calls fail with `invalid_argument` | Error-category oracle | Closed session never performs bridge operations |
| U-009 | Validate session-to-bridge delegation | None | Use a bridge test double and call list/decompile through session | Session forwards calls and request payload unchanged | Delegation oracle | Bridge call shape is stable |

## 2. Contract Tests

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| C-001 | Public result schema stability | None | Call API stub and inspect result keys/types | Required keys/types unchanged | JSON-schema-like oracle | Additive fields allowed only |
| C-002 | Error taxonomy stability | None | Trigger representative error categories in harness stubs | Category names stable | Enum/name oracle | Categories cannot be removed in minor/patch |
| C-003 | Version reporting contract | None | Query version endpoint | Includes flatline + upstream pin metadata | Field-presence oracle | Pin fields always populated |
| C-004 | Structured result object schema stability | None | Call API stub and inspect FunctionInfo, FunctionPrototype, TypeInfo fields/types | Required fields/types unchanged; metatype strings are stable enum values | JSON-schema-like oracle | Additive fields allowed only; metatype mapping is contract-stable |
| C-005 | Session API surface stability | None | Inspect `DecompilerSession` for required methods | Lifecycle and operation methods are present and callable | API-surface oracle | Required methods remain stable |
| C-006 | Top-level operation function availability | None | Inspect module-level operation callables and signatures | `decompile_function` and `list_language_compilers` exist with stable parameters | Signature oracle | Parameter names remain stable |

## 3. Integration Tests (future live calls)

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| I-001 | Known function decompilation success | `fx_add_elf64` | Decompile known entrypoint | Non-empty C output and success status; `function_info` populated with `is_complete` True | Normalized C text + status + structured-field oracle | Ignore whitespace/comments; preserve semantic tokens; structured field shapes stable |
| I-002 | Language/compiler enumeration validity | Runtime data fixture | Enumerate pairs and validate each pair assets exist | No invalid/missing-backed pairs returned | Asset-existence oracle | Returned pairs stable per fixture revision |
| I-003 | Sequential context isolation | `fx_add_elf64` | Run multiple sessions in sequence | No cross-session leakage in warnings/metadata | Session-isolation oracle | Stable results independent of previous session |
| I-004 | Startup and minimal load smoke path | `fx_runtime_data_min` | Start session, validate runtime data discovery, and execute minimal initialization/load flow | Startup succeeds with deterministic metadata and no leaked prior state | Startup-state oracle | Repeated startup/load remains deterministic under pinned upstream |
| I-005 | Known function produces populated FunctionInfo | `fx_add_elf64` | Decompile known function and inspect function_info | `function_info` is not None; `is_complete` True; `prototype` has expected parameter count and return type; `diagnostics` flags consistent | Structured-field oracle | Field shapes stable for same fixture and upstream pin |
| I-006 | Multi-ISA and multi-bitwidth known function decompilation | `fx_add_elf32`, `fx_add_arm64`, `fx_add_riscv64`, `fx_add_mips32` | Decompile known function for each additional priority ISA variant (x86_32, ARM64, RISC-V 64, MIPS32) | Non-empty C output and success status per ISA; `function_info` populated; no cross-ISA interference | Per-ISA normalized oracle | Each ISA evaluated independently; oracle baselines are ISA-specific |
| I-007 | Warning-only success with warning structure | `fx_warning_elf64` | Decompile function that produces warnings but succeeds | `c_code` non-empty; `error` is `None`; `function_info` populated; `warnings` non-empty with each item having `code` (str), `message` (str), `phase` (str) | Status + warning-structure oracle | Warning codes stable; message text informative only; phase values from defined set (`init`, `analyze`, `emit`) |

## 4. Regression Tests

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| R-001 | Preserve known simple function output behavior | `fx_add_elf64` | Decompile fixture function | Output matches normalized baseline; `function_info.prototype` shape and `varnode_count` stable | Canonical token stream + structured-data oracle | Stable across patch releases for same upstream pin |
| R-002 | Preserve jump-table output behavior | `fx_switch_elf64` | Decompile switch fixture | Output retains switch structure and expected case set; `function_info.jump_tables` target count and addresses stable | Structural AST/token + jump-table oracle | Case coverage, control structure, and jump table data stable |
| R-003 | Performance regression sentinel | `fx_add_elf64`, `fx_switch_elf64` | Measure decompile latency under controlled harness | Latency within budget threshold | Statistical budget oracle | Fail on sustained >15% p95 drift |
| R-004 | Multi-ISA regression baselines | `fx_add_elf32`, `fx_add_arm64`, `fx_add_riscv64`, `fx_add_mips32` | Decompile per-ISA fixture and compare to ISA-specific baseline | Output matches normalized baseline per ISA; structured data shapes stable | Per-ISA canonical token stream oracle | Baselines are ISA-specific; stable across patch releases for same upstream pin |

## 5. Negative Tests

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| N-001 | Invalid address hard failure | `fx_add_elf64` | Request decompile at unmapped/invalid address | Structured `invalid_address` error; `function_info` is `None`; `c_code` is `None` | Category/status oracle | Must not downgrade to warning-only success |
| N-002 | Unsupported language id failure | `fx_add_elf64` | Request unknown language id | Structured `unsupported_target` error; `function_info` is `None`; `c_code` is `None` | Category/status oracle | No fallback language substitution |
| N-003 | Unsupported compiler for valid language | `fx_add_elf64` | Request invalid compiler for known language | Structured `unsupported_target` error; `function_info` is `None`; `c_code` is `None` | Category/status oracle | No implicit compiler fallback |
| N-004 | Corrupt/missing runtime data directory | runtime data fixture | Start session with broken data dir | Deterministic startup failure | Startup error oracle | Error category stable across runs |
| N-005 | Invalid memory image input | `fx_invalid_memory` (empty/zero-length memory image) | Request decompile with empty or zero-length memory image | Structured `invalid_argument` error; `function_info` is `None`; `c_code` is `None` | Category/status oracle | Error category stable; message text may vary |

## 6. Contract-Clause-to-Test Traceability

| Spec clause (specs.md) | Contract requirement | Test IDs |
| --- | --- | --- |
| §3.2 `list_language_compilers()` | Enumerate valid pairs from runtime data | I-002 |
| §3.2 `decompile_function(request)` | Decompile one function; no native exceptions leak | I-001, I-005, I-006, U-009 |
| §3.1 `DecompilerSession` lifecycle | Long-lived session owns lifecycle of one bridge/native context | U-007, U-008, C-005 |
| §3.2 top-level operation wrappers | Public operation callables are exposed from package root | C-006 |
| §3.2 `get_version_info()` | Report flatline + upstream pin metadata | C-003 |
| §3.3 DecompileRequest required fields | Missing fields → `invalid_argument` | U-001 |
| §3.3 DecompileRequest `compiler_spec` validation | Unknown compiler → hard error | U-002, N-003 |
| §3.3 DecompileRequest `function_size_hint` | Advisory; omission not an error | U-004 |
| §3.3 DecompileRequest `analysis_budget` | Advisory; omission not an error | U-006 |
| §3.3 DecompileResult metadata keys | Required top-level keys always present | U-003, C-001 |
| §3.3 FunctionInfo fields + types | Required fields present, correct types, diagnostics consistent | U-005, I-005, C-004 |
| §3.3 FunctionPrototype fields | Calling convention, parameters, return type, flags | C-004, I-005 |
| §3.3 ParameterInfo, VariableInfo, TypeInfo | Stable required fields and metatype strings | C-004 |
| §3.3 CallSiteInfo, JumpTableInfo | Call/jump-table structured data | R-002, I-005 |
| §3.3 DiagnosticFlags | Aggregated boolean flags | U-005, I-005 |
| §3.3 LanguageCompilerPair | language_id + compiler_spec fields | I-002 |
| §3.3 WarningItem structure | code, message, phase fields | I-007 |
| §3.3 VersionInfo fields | flatline_version, upstream_tag, upstream_commit, runtime_data_revision | C-003 |
| §3.4 Unknown compiler → hard error | No implicit fallback | U-002, N-003 |
| §3.4 Unknown language → hard error | No fallback substitution | N-002 |
| §3.4 Invalid address → hard error | Not warning-only | N-001 |
| §3.4 Empty memory → hard error | `invalid_argument` | N-005 |
| §3.4 Error categories stable | Category names invariant across minor/patch | C-002 |
| §3.4 Warning-only → successful status | c_code valid, error None, function_info populated | I-007 |
| §3.4 Error set → function_info=None, c_code=None | Error model invariant | N-001, N-002, N-003, N-005 |
| §3.4 Success → function_info populated | Never None on success | I-005 |
| §3.5 Additive fields only in minor | Schema stability | C-001, C-004 |
| §7 Session isolation | No cross-session leakage | I-003 |
| §7 Startup determinism | Repeatable startup under pinned upstream | I-004 |
| §7 Performance budget | p95 latency within threshold | R-003 |
| Regression: simple function | Normalized output stable | R-001 |
| Regression: jump-table | Switch structure + jump table data stable | R-002 |
| Regression: multi-ISA | Per-ISA baselines stable | R-004 |
| Runtime data dir broken | Deterministic startup failure | N-004 |

## 7. Mapping to Source Documents

- Decompiler lifecycle and required callable behavior: `notes/api/decompiler_inventory.md`.
- Post-decompile structured data (FunctionInfo, prototype, symbols, types): `notes/api/decompiler_inventory.md` §§1-7.
- Public contract, runtime-data policy, and error semantics: `docs/specs.md`.
- Structured result object definitions: `docs/specs.md` §3.3.
- Milestones and release gates for deterministic behavior: `docs/roadmap.md`.
- Startup/minimal-load, known-function, invalid-address, and jump-table expectations are consolidated into this catalog from baseline experiment findings.
- Error category definitions and stability rules: `docs/specs.md` §3.4.
