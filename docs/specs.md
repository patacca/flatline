# ghidralib Specification (SDD)

## 0. Scope and Sources

Pinned upstream baseline:
- Ghidra tag: `Ghidra_12.0.3_build`
- Commit: `09f14c92d3da6e5d5f6b7dea115409719db3cce1`
- Commit date: `2026-02-10`

Primary source notes used for this spec:
- `notes/api/decompiler_inventory.md` (decompiler-facing callable contract)
- `notes/api/mvp_contract.md` (MVP runtime/data contract; reconciled below)
- `notes/experiments/E1_compile_driver.md`
- `notes/experiments/E2_init_minimal.md`
- `notes/experiments/E3_decompile_known_func.md`
- `notes/experiments/E4_invalid_address.md`
- `notes/experiments/E5_jump_table_switch.md`

Hard constraints:
- In-process Python to native bridge is mandatory.
- Installable from `pip` without requiring users to provide/build Ghidra.
- MVP target: Linux first; architecture must preserve macOS/Windows feasibility.
- Python: `3.13+`.
- Version policy: support only the latest Ghidra decompiler version.

## 1. Goals and Non-Goals

Goals:
- Provide a stable Python-first decompilation contract that remains consistent while upstream internals change.
- Expose single-function decompilation with explicit language/compiler selection and structured diagnostics.
- Make runtime assets self-contained for out-of-the-box installation.
- Define testable behavioral guarantees before implementation details.

Non-goals:
- Full parity with every upstream decompiler feature in MVP.
- Whole-program project modeling in MVP.
- Supporting multiple Ghidra decompiler versions simultaneously.
- Defining build scripts, binding mechanics, or C/C++ implementation internals in this document.

## 2. Personas and Use Cases

Personas:
- Reverse engineer automating decompilation pipelines from Python.
- Security engineer building repeatable triage workflows.
- CI operator requiring deterministic decompilation checks across releases.

Primary use cases:
- Decompile one function by binary path + entry address.
- Enumerate valid `(language_id, compiler_spec)` pairs shipped in runtime data.
- Fail predictably on invalid addresses/unsupported language selection.
- Run repeated decompiles in one process with isolated request state.

Secondary (Next):
- Batch execution over many functions with bounded resources.
- Cross-platform parity (macOS/Windows).

## 3. Public Python API Contract

### 3.1 Concepts

| Concept | Contract |
| --- | --- |
| `DecompilerSession` | Long-lived object owning one native context and immutable startup config. |
| `DecompileRequest` | Input payload for one function decompilation: binary target, function address, language, optional compiler and analysis options. |
| `DecompileResult` | Output payload containing rendered C text, warnings, structured error (if any), and metadata. |
| `LanguageCompilerPair` | One valid `language_id` + `compiler_spec` entry known to current runtime data directory. |
| `GhidralibError` | Stable Python exception hierarchy mapped from status/error categories. |

Derived from:
- `notes/api/mvp_contract.md` (required inputs, outputs, pair enumeration).

### 3.2 Operations

| Operation | Purpose | Minimum behavior |
| --- | --- | --- |
| `list_language_compilers()` | Enumerate valid language/compiler pairs | Returns only pairs with required backing assets present in runtime data. |
| `decompile_function(request)` | Decompile one function | Returns `DecompileResult`; no native exceptions leak across public boundary. |
| `get_version_info()` | Report runtime versions | Includes ghidralib version, pinned upstream commit/tag, and runtime data revision id. |

### 3.3 Data Model

`DecompileRequest` fields:
- `binary_path` (required)
- `function_address` (required)
- `language_id` (required)
- `compiler_spec` (optional, explicit validation required)
- `runtime_data_dir` (optional override)
- `function_size_hint` (optional advisory)
- `analysis_budget` (optional deterministic budget object)

`DecompileResult` fields:
- `c_code: str | None`
- `warnings: list[WarningItem]`
- `error: ErrorItem | None`
- `metadata: dict[str, Any]` with stable top-level keys:
- `metadata["decompiler_version"]`
- `metadata["language_id"]`
- `metadata["compiler_spec"]`
- `metadata["diagnostics"]`

`WarningItem` minimum keys:
- `code` (stable across patch/minor releases)
- `message`
- `phase` (`init`, `analyze`, `emit`)

`ErrorItem` minimum keys:
- `category` (`invalid_argument`, `unsupported_target`, `invalid_address`, `decompile_failed`, `internal_error`)
- `message`
- `retryable` (bool)

Derived from:
- `notes/api/mvp_contract.md` sections 6-8.
- `notes/experiments/E4_invalid_address.md` (invalid-address hard failure semantics).

### 3.4 Error Model

Rules:
- Unknown compiler ids are hard errors (no implicit fallback).
- Invalid/unmapped addresses are hard errors, not warning-only degraded output.
- Error categories are contract-stable; text may change but remains human-readable.
- Warning-only outcomes must still return successful operation status when C output is valid.

Derived from:
- `notes/api/mvp_contract.md` section 2 (fallback rejection) and section 8.
- `notes/experiments/E4_invalid_address.md` blocker.

### 3.5 Stability Guarantees and SemVer

Stability guarantees:
- Public Python names, payload fields, and error categories are stable API.
- New optional metadata keys may be added in minor releases.
- Existing required fields cannot be removed without a major release.

SemVer rules:
- Major: breaking Python API contract changes.
- Minor: backward-compatible features, new optional fields, new warnings.
- Patch: bug fixes with no contract shape changes.

Latest-upstream-only policy:
- Each ghidralib release line tracks exactly one upstream Ghidra decompiler revision.
- Upstream bump occurs in normal minor/major releases, never by supporting multiple upstream versions at once.

## 4. Decompiler-Facing Contract and Mapping

### 4.1 Required Native Capabilities

From `notes/api/decompiler_inventory.md`:
- Process-global startup/shutdown lifecycle.
- Language description discovery and compiler association.
- Architecture initialization lifecycle with explicit document/spec loading.
- Function lookup/materialization from entry address.
- Action pipeline ordering: reset -> perform -> emit.
- Structured warning and failure propagation at bridge boundary.

### 4.2 Invariants

Invariants exposed to Python contract:
- Startup path initialization is global and must be deterministic.
- Function decompilation is request-scoped: each request produces isolated result objects.
- Printer output requires successful action pipeline completion.
- Compiler/language resolution must be explicit and validated.

### 4.3 Limits

Known limits at baseline:
- Entry-point-only function targeting in MVP.
- CFG recovery can be best-effort; unresolved indirect flows may degrade output quality.
- Global startup/cache state implies constrained mutation semantics across threads.

### 4.4 Mapping to Public API

| Decompiler-facing capability | Public API behavior | User-visible contract |
| --- | --- | --- |
| Global startup and spec discovery | Session startup and runtime-data validation | Deterministic startup errors with actionable messages |
| Language/compiler descriptions | `list_language_compilers()` | Enumerated pairs are valid and loadable |
| Function lookup/materialization | `decompile_function(request)` address targeting | Missing/invalid function target returns structured error category |
| Action execution pipeline | Internal execution of request | Successful path yields `c_code` and optional warnings |
| Warning propagation | `DecompileResult.warnings` | Warning codes are stable identifiers |
| Failure propagation | `DecompileResult.error` / exception mapping | No uncaught native exception reaches user |

## 5. Architecture Decision Space (No Implementation Details)

### 5.1 Option Set

| Option | Description | Determinism | Performance | UX | Fixture burden | Packaging/Cross-platform risk |
| --- | --- | --- | --- | --- | --- | --- |
| A. Bytes + arch + function-level inputs | Caller provides low-level memory/function boundary context | High if caller supplies strong boundaries; variable otherwise | Good per-call overhead | Expert-heavy API | High (many synthetic edge fixtures) | Moderate (less loader dependence, more custom glue risk) |
| B. Full binary/program loader path | Caller provides binary path + function address; library handles loading | High for standard binaries | Good warm-path; heavier cold start | Simple for most users | Moderate | Lower semantic risk; higher runtime artifact size |
| C. Hybrid (B default + A advanced mode) | Default full-binary path with optional advanced low-level mode | High (default path); configurable advanced mode | Best long-term tradeoff | Best | Highest initial planning complexity | Highest design complexity but best extensibility |

### 5.2 Recommendation

Recommended direction:
- MVP: Option B.
- Next: evolve to Option C once contract tests are stable and cross-platform packaging is proven.

Rationale:
- Matches existing validated experiment flow for known-function and jump-table decompilation.
- Minimizes user-facing ambiguity around memory model and function reconstruction.
- Keeps room for advanced low-level mode without destabilizing primary API.

Derived from:
- `notes/experiments/E2_init_minimal.md`, `E3_decompile_known_func.md`, `E5_jump_table_switch.md`.

### 5.3 Decision Points Requiring User Choice

1. Keep MVP strictly Option B, or reserve public placeholders for future Hybrid mode now.
2. Define strictness of decompilation failure semantics:
- Recommended: invalid address always hard error.
- Alternative: allow warning-only degraded output class.
3. Define determinism profile level:
- Recommended: normalize metadata and warning codes only.
- Alternative: enforce stronger canonical C formatting guarantees.
4. Choose default analysis budget behavior:
- Recommended: bounded defaults with explicit override.
- Alternative: unbounded analysis unless caller sets a budget.

## 6. Stable Python API over Unstable Upstream Strategy

Adapter boundaries:
- `Public Contract Layer`: Python request/result models and error taxonomy.
- `Bridge Contract Layer`: strict translation between public models and native decompiler calls.
- `Upstream Adapter Layer`: handles upstream callable surface and lifecycle changes.

Contract-test strategy:
- API contract tests validate field presence/types/error categories.
- Behavior tests validate deterministic outcomes for pinned fixtures.
- Negative tests ensure structured errors for unsupported language/compiler/addresses.

Change-detection process for upstream bump:
1. Rebuild decompiler inventory diff from pinned upstream callable symbols.
2. Re-run fixture matrix and compare normalized oracle outputs.
3. Classify deltas as contract-preserving vs contract-breaking.
4. Update changelog, SemVer decision, and fixture baselines in one release unit.

## 7. Cross-Cutting Requirements

Determinism and oracles:
- Use normalized textual oracle strategy (token/structure-aware) for C output.
- Keep warning/error codes stable even when message text evolves.

Concurrency model:
- Session object is not implicitly shared across threads.
- Global startup/cache mutation is serialized.
- Parallel decompilation requires explicit session isolation policy.

Performance budgets (planning targets):
- Session startup (warm): bounded target defined per release.
- Single-function decompile on MVP fixture set: p95 budget tracked in CI.
- Regression threshold policy: fail CI on sustained >15% regression for pinned matrix.

Security boundaries:
- Untrusted binaries are treated as untrusted input.
- No implicit execution of external tools in request path.
- Resource budgets (time/memory) are part of operational contract.

Logging and diagnostics:
- Structured log events by phase (`startup`, `resolve`, `analyze`, `emit`).
- Redaction policy for filesystem paths configurable by user.

Configuration:
- Explicit runtime data dir override.
- Explicit analysis budget and warning policy controls.
- Deterministic defaults when options are omitted.

Extensibility:
- Additive extension points via optional request fields and metadata keys.
- Future backends or advanced modes must preserve baseline contract semantics.

## 8. MVP vs Next and Reconciliation with `mvp_contract.md`

### 8.1 MVP Commitments (Kept)

- Linux-first single-function scope.
- Runtime data directory contract with packaged default and explicit override.
- Pair enumeration from language descriptions with existence filtering.
- Structured results with warnings/errors/metadata.

### 8.2 Items Marked Obsolete and Replaced

| Item in `notes/api/mvp_contract.md` | Status | Replacement in this spec |
| --- | --- | --- |
| Binding mechanism named as `ctypes`/`cffi` in normative scope | Obsolete as normative requirement | Replaced with bridge-agnostic in-process contract; binding choice deferred to ADR. |
| Implicitly narrow curated compiler list as fixed forever | Obsolete as permanent restriction | Replaced with MVP curated baseline plus additive expansion policy under SemVer minor releases. |
| Console-path behavior note as implementation framing | Obsolete as behavior reference | Replaced with explicit API rule: invalid addresses are structured hard errors. |
| Focus on C ABI wording as primary public contract | Obsolete for top-level spec | Replaced with Python-first contract and separate bridge contract boundary. |

### 8.3 Next-Scope Candidates

- Batch decompilation APIs.
- Cross-platform artifact parity (macOS/Windows).
- Hybrid low-level input mode for advanced workflows.

## 9. Open Questions

- Should warning codes be globally namespaced now to prevent future collisions?
- Is canonicalized C output required as a hard contract, or only semantic/token-level stability?
- Should analysis-budget defaults vary by platform or remain globally fixed?
- How strict should package-size limits be for bundled runtime assets?

## 10. Assumptions

- Upstream baseline remains fixed until deliberate bump planning is triggered.
- Users accept latest-upstream-only support policy.
- MVP fixture binaries can be redistributed under project licensing policy.
- Linux-first release can ship before cross-platform parity without violating product goals.
