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

## 2. Contract Tests

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| C-001 | Public result schema stability | None | Call API stub and inspect result keys/types | Required keys/types unchanged | JSON-schema-like oracle | Additive fields allowed only |
| C-002 | Error taxonomy stability | None | Trigger representative error categories in harness stubs | Category names stable | Enum/name oracle | Categories cannot be removed in minor/patch |
| C-003 | Version reporting contract | None | Query version endpoint | Includes ghidralib + upstream pin metadata | Field-presence oracle | Pin fields always populated |

## 3. Integration Tests (future live calls)

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| I-001 | Known function decompilation success | `fx_add_elf64` | Decompile known entrypoint | Non-empty C output and success status | Normalized C text + status oracle | Ignore whitespace/comments; preserve semantic tokens |
| I-002 | Language/compiler enumeration validity | Runtime data fixture | Enumerate pairs and validate each pair assets exist | No invalid/missing-backed pairs returned | Asset-existence oracle | Returned pairs stable per fixture revision |
| I-003 | Sequential context isolation | `fx_add_elf64` | Run multiple sessions in sequence | No cross-session leakage in warnings/metadata | Session-isolation oracle | Stable results independent of previous session |
| I-004 | Startup and minimal load smoke path | `fx_runtime_data_min` | Start session, validate runtime data discovery, and execute minimal initialization/load flow | Startup succeeds with deterministic metadata and no leaked prior state | Startup-state oracle | Repeated startup/load remains deterministic under pinned upstream |

## 4. Regression Tests

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| R-001 | Preserve known simple function output behavior | `fx_add_elf64` | Decompile fixture function | Output matches normalized baseline | Canonical token stream oracle | Stable across patch releases for same upstream pin |
| R-002 | Preserve jump-table output behavior | `fx_switch_elf64` | Decompile switch fixture | Output retains switch structure and expected case set | Structural AST/token oracle | Case coverage and control structure stable |
| R-003 | Performance regression sentinel | `fx_add_elf64`, `fx_switch_elf64` | Measure decompile latency under controlled harness | Latency within budget threshold | Statistical budget oracle | Fail on sustained >15% p95 drift |

## 5. Negative Tests

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| N-001 | Invalid address hard failure | `fx_add_elf64` | Request decompile at unmapped/invalid address | Structured `invalid_address` error | Category/status oracle | Must not downgrade to warning-only success |
| N-002 | Unsupported language id failure | `fx_add_elf64` | Request unknown language id | Structured `unsupported_target` error | Category/status oracle | No fallback language substitution |
| N-003 | Unsupported compiler for valid language | `fx_add_elf64` | Request invalid compiler for known language | Structured `unsupported_target` error | Category/status oracle | No implicit compiler fallback |
| N-004 | Corrupt/missing runtime data directory | runtime data fixture | Start session with broken data dir | Deterministic startup failure | Startup error oracle | Error category stable across runs |
| N-005 | Invalid memory image input | `fx_invalid_memory` (empty/zero-length memory image) | Request decompile with empty or zero-length memory image | Structured `invalid_argument` error | Category/status oracle | Error category stable; message text may vary |

## 6. Mapping to Source Documents

- Decompiler lifecycle and required callable behavior: `notes/api/decompiler_inventory.md`.
- Public contract, runtime-data policy, and error semantics: `docs/specs.md`.
- Milestones and release gates for deterministic behavior: `docs/roadmap.md`.
- Startup/minimal-load, known-function, invalid-address, and jump-table expectations are consolidated into this catalog from baseline experiment findings.
- Error category definitions and stability rules: `docs/specs.md` §3.4.
