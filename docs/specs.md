# flatline Specification (SDD)

## 0. Scope and Sources

Pinned upstream baseline:
- Ghidra tag: `Ghidra_12.0.3_build`
- Commit: `09f14c92d3da6e5d5f6b7dea115409719db3cce1`
- Commit date: `2026-02-10`

Primary sources used for this spec:
- `notes/api/decompiler_inventory.md` (decompiler-facing callable contract)
- Consolidated MVP contract and experiment findings captured directly in this spec and `tests/specs/test_catalog.md`

Retired sources (content merged into this spec and test catalog):
- `notes/api/mvp_contract.md` (former MVP contract draft; obsolete items listed in §8.2)
- `notes/experiments/` (experiment findings captured as test definitions in `tests/specs/test_catalog.md`)

Hard constraints:
- In-process Python to native bridge is mandatory.
- Installable from `pip` without requiring users to provide/build Ghidra.
- MVP host platform: Linux x86_64; architecture must preserve macOS/Windows host feasibility.
- MVP target ISA scope: any Ghidra decompiler-supported binary architecture. Priority ISAs: x86 (32/64), ARM (32/64), RISC-V (32/64), MIPS (32/64). Runtime data must bundle language/compiler assets for all priority ISAs at minimum.
- Python: `3.13+`.
- Version policy: support only the latest Ghidra decompiler version.

## 1. Goals and Non-Goals

Goals:
- Provide a stable Python-first decompilation contract that remains consistent while upstream internals change.
- Expose single-function decompilation with explicit language/compiler selection and structured diagnostics.
- Support decompilation of any Ghidra-supported target ISA from a single installation, with priority coverage for x86, ARM, RISC-V, and MIPS families.
- Make runtime assets self-contained for out-of-the-box installation.
- Define testable behavioral guarantees before implementation details.

Non-goals:
- Full parity with every upstream decompiler feature in MVP.
- Whole-program project modeling in MVP.
- Supporting multiple Ghidra decompiler versions simultaneously.
- Defining build scripts, binding mechanics, or C/C++ implementation internals in this document.
- Guaranteeing identical decompilation quality across all ISAs; priority ISAs (x86, ARM, RISC-V, MIPS) have full fixture coverage, other Ghidra-supported ISAs are best-effort with enumeration and error-contract coverage only.

## 2. Personas and Use Cases

Personas:
- Reverse engineer automating decompilation pipelines from Python.
- Security engineer building repeatable triage workflows.
- CI operator requiring deterministic decompilation checks across releases.

Primary use cases:
- Decompile one function by memory image + architecture + entry address (ADR-001 resolved: Option A).
- Decompile functions from any Ghidra-supported target ISA (x86, ARM, RISC-V, MIPS, and others) by specifying the appropriate `language_id`.
- Enumerate valid `(language_id, compiler_spec)` pairs shipped in runtime data, spanning all bundled ISAs.
- Fail predictably on invalid addresses/unsupported language selection.
- Run repeated decompiles in one process with isolated request state.

Secondary (Next):
- Batch execution over many functions with bounded resources.
- Cross-platform parity (macOS/Windows).

## 3. Public Python API Contract

### 3.1 Concepts

| Concept | Contract |
| --- | --- |
| `DecompilerSession` | Long-lived object owning one native `Architecture` instance and immutable startup config. Session lifecycle maps to Architecture construction through destruction. |
| `DecompileRequest` | Input payload for one function decompilation: memory image, base address, function entry address, language, optional compiler and analysis options. |
| `DecompileResult` | Output payload containing rendered C text, structured function info, warnings, structured error (if any), and metadata. |
| `FunctionInfo` | Structured post-decompile data for one function: name, address, size, prototype, local variables, call sites, jump tables, diagnostics. Populated on success, `None` on error. |
| `FunctionPrototype` | Recovered function signature: calling convention, parameters, return type, and recovery-status flags. |
| `ParameterInfo` | One function parameter: name, type, index, and optional storage location. |
| `VariableInfo` | One local variable: name, type, and optional storage location. |
| `TypeInfo` | Recovered type descriptor: name, size, and stable metatype classification string. |
| `CallSiteInfo` | One call instruction within the function: instruction address and optional resolved target address. |
| `JumpTableInfo` | One recovered jump table: switch address, target count, and resolved target addresses. |
| `DiagnosticFlags` | Aggregated boolean diagnostic flags from the decompiler: completion, unreachable blocks, unimplemented instructions, bad data, no code. |
| `StorageInfo` | Variable/parameter storage location: address space name, byte offset, byte size. |
| `LanguageCompilerPair` | One valid `language_id` + `compiler_spec` entry known to current runtime data directory. |
| `FlatlineError` | Stable Python exception hierarchy mapped from status/error categories. |

Derived from:
- Consolidated MVP contract requirements in this specification.

### 3.2 Operations

| Operation | Purpose | Minimum behavior |
| --- | --- | --- |
| `DecompilerSession.list_language_compilers()` | Enumerate valid language/compiler pairs | Returns only pairs with required backing assets present in runtime data. Covers all bundled ISAs (priority: x86, ARM, RISC-V, MIPS; plus any other Ghidra-supported ISAs whose assets are included). |
| `DecompilerSession.decompile_function(request)` | Decompile one function | Returns `DecompileResult`; no native exceptions leak across public boundary. |
| `flatline.list_language_compilers(runtime_data_dir=None)` | One-shot convenience wrapper for pair enumeration | Creates a short-lived `DecompilerSession`, runs enumeration, and closes the session deterministically. |
| `flatline.decompile_function(request)` | One-shot convenience wrapper for decompilation | Creates a short-lived `DecompilerSession`, runs decompilation, and closes the session deterministically. |
| `get_version_info()` | Report runtime versions | Includes flatline version, pinned upstream commit/tag, and runtime data revision id. |

`DecompilerSession` is the canonical surface for repeated calls in one process.
Module-level operation functions are convenience wrappers for single-call workflows.

### 3.3 Data Model

`DecompileRequest` fields:
- `memory_image` (required): byte content of the target memory region
- `base_address` (required): virtual address of the start of `memory_image`
- `function_address` (required): entry point virtual address within the memory image
- `language_id` (required)
- `compiler_spec` (optional, explicit validation required)
- `runtime_data_dir` (optional override)
- `function_size_hint` (optional advisory)
- `analysis_budget` (optional deterministic budget object)

Input model resolved by ADR-001 (Option A: memory + architecture + function-level).
The caller provides a memory image covering the relevant address space. The library
does not perform binary format parsing; callers who work with binary files must
extract memory content before calling the API. Multi-region input and section metadata
are planned extensions (see §8.3).

`DecompileResult` fields:
- `c_code: str | None`
- `function_info: FunctionInfo | None` — populated on success, `None` on error
- `warnings: list[WarningItem]`
- `error: ErrorItem | None`
- `metadata: dict[str, Any]` with stable top-level keys:
  - `metadata["decompiler_version"]`
  - `metadata["language_id"]`
  - `metadata["compiler_spec"]`
  - `metadata["diagnostics"]` — legacy key; superseded by `function_info.diagnostics` when `function_info` is present

`FunctionInfo` fields:
- `name: str` — function name (from `Funcdata::getName()`)
- `entry_address: int` — function entry point virtual address (from `Funcdata::getAddress()`)
- `size: int` — function body size in bytes (from `Funcdata::getSize()`)
- `is_complete: bool` — whether decompilation completed fully (from `Funcdata::isProcComplete()`)
- `prototype: FunctionPrototype` — recovered function signature
- `local_variables: list[VariableInfo]` — local scope symbols
- `call_sites: list[CallSiteInfo]` — call instructions within the function
- `jump_tables: list[JumpTableInfo]` — recovered jump tables
- `diagnostics: DiagnosticFlags` — aggregated diagnostic status flags
- `varnode_count: int` — total Varnode count (complexity metric, from `Funcdata::numVarnodes()`)

`FunctionPrototype` fields:
- `calling_convention: str | None` — calling convention model name (from `FuncProto::getModelName()`)
- `parameters: list[ParameterInfo]` — recovered parameters
- `return_type: TypeInfo` — recovered return type
- `is_noreturn: bool` — function does not return (from `FuncProto::isNoReturn()`)
- `has_this_pointer: bool` — has implicit this parameter (from `FuncProto::hasThisPointer()`)
- `has_input_errors: bool` — parameter recovery incomplete (from `FuncProto::hasInputErrors()`)
- `has_output_errors: bool` — return type recovery incomplete (from `FuncProto::hasOutputErrors()`)

`ParameterInfo` fields:
- `name: str` — parameter name (from `Symbol::getName()`)
- `type: TypeInfo` — parameter type (from `Symbol::getType()`)
- `index: int` — parameter position in signature
- `storage: StorageInfo | None` — storage location if mapped

`VariableInfo` fields:
- `name: str` — variable name (from `Symbol::getName()`)
- `type: TypeInfo` — variable type (from `Symbol::getType()`)
- `storage: StorageInfo | None` — storage location if mapped

`TypeInfo` fields:
- `name: str` — type name (from `Datatype::getName()`)
- `size: int` — type size in bytes (from `Datatype::getSize()`)
- `metatype: str` — stable metatype classification string (from `Datatype::getMetatype()`)

Metatype string mapping (upstream C++ enum → stable Python string):
`TYPE_VOID`→`"void"`, `TYPE_BOOL`→`"bool"`, `TYPE_INT`→`"int"`, `TYPE_UINT`→`"uint"`, `TYPE_FLOAT`→`"float"`, `TYPE_PTR`→`"pointer"`, `TYPE_ARRAY`→`"array"`, `TYPE_STRUCT`→`"struct"`, `TYPE_UNION`→`"union"`, `TYPE_CODE`→`"code"`, `TYPE_ENUM_INT`/`TYPE_ENUM_UINT`→`"enum"`, `TYPE_UNKNOWN`→`"unknown"`.

Unmapped internal metatypes (not surfaced through the public API): `TYPE_PTRREL` (relative pointer), `TYPE_SPACEBASE` (stack/space base), `TYPE_PARTIALSTRUCT`, `TYPE_PARTIALUNION`, `TYPE_PARTIALENUM` (partial analysis artifacts). If a type with an unmapped metatype is encountered at the bridge boundary, it is mapped to `"unknown"`.

`CallSiteInfo` fields:
- `instruction_address: int` — address of the CALL instruction
- `target_address: int | None` — resolved callee address (`None` for indirect calls)

`JumpTableInfo` fields:
- `switch_address: int` — address of the switch/indirect-branch instruction
- `target_count: int` — number of resolved target addresses
- `target_addresses: list[int]` — resolved target addresses

`DiagnosticFlags` fields:
- `is_complete: bool` — `Funcdata::isProcComplete()`
- `has_unreachable_blocks: bool` — `Funcdata::hasUnreachableBlocks()`
- `has_unimplemented: bool` — `Funcdata::hasUnimplemented()`
- `has_bad_data: bool` — `Funcdata::hasBadData()`
- `has_no_code: bool` — `Funcdata::hasNoCode()`

`StorageInfo` fields:
- `space: str` — address space name (from `AddrSpace::getName()`)
- `offset: int` — byte offset within address space
- `size: int` — size in bytes

`LanguageCompilerPair` fields:
- `language_id: str` — language identifier (from `LanguageDescription::getId()`)
- `compiler_spec: str` — compiler specification name (from `CompilerTag::getName()`)

`WarningItem` fields:
- `code: str` — stable warning code using hierarchical namespace (`<phase>.<code>`, e.g., `analyze.W001`); stable across patch/minor releases; initial code enumeration deferred to P2 implementation
- `message: str` — human-readable warning text (informative, not exact-match stable)
- `phase: str` — phase that produced the warning (`init`, `analyze`, `emit`)

`ErrorItem` fields:
- `category: str` — stable error category (`invalid_argument`, `unsupported_target`, `invalid_address`, `decompile_failed`, `internal_error`)
- `message: str` — human-readable error text (informative, not exact-match stable)
- `retryable: bool` — whether the operation may succeed on retry with the same inputs

`VersionInfo` fields:
- `flatline_version: str`
- `upstream_tag: str`
- `upstream_commit: str`
- `runtime_data_revision: str`

All structured result objects (`FunctionInfo`, `FunctionPrototype`, `ParameterInfo`, `VariableInfo`, `TypeInfo`, `CallSiteInfo`, `JumpTableInfo`, `DiagnosticFlags`, `StorageInfo`, `LanguageCompilerPair`, `WarningItem`, `ErrorItem`, `VersionInfo`) are pure Python frozen value types. Data is extracted at the bridge boundary; no native pointers or references survive past the bridge call.

Error model for structured results:
- If `DecompileResult.error` is set, then `function_info` is `None` and `c_code` is `None`.
- If decompilation succeeds, `function_info` is populated (never `None`) and `c_code` is set.
- Recovery failures within `function_info` are signaled via `prototype.has_input_errors` / `has_output_errors` and `diagnostics` flags, not by making individual fields `None`.

Derived from:
- Consolidated MVP data and error contract in this specification.
- Consolidated invalid-address hard-failure requirement carried into negative tests.
- Structured object definitions derived from `notes/api/decompiler_inventory.md` §§1-7 (post-decompilation contract).

### 3.4 Error Model

Rules:
- Unknown compiler ids are hard errors (no implicit fallback). Error category: `unsupported_target`.
- Unknown/unsupported language ids are hard errors. Error category: `unsupported_target`.
- Invalid/unmapped addresses are hard errors, not warning-only degraded output. Error category: `invalid_address`.
- Empty or zero-length memory images are hard errors. Error category: `invalid_argument`.
- Calling session operations after `DecompilerSession.close()` is a hard error. Error category: `invalid_argument`.
- Error categories are contract-stable; text may change but remains human-readable.
- Warning-only outcomes must still return successful operation status when C output is valid.
- When `error` is set, `function_info` is always `None` and `c_code` is always `None`.
- When decompilation succeeds, `function_info` is always populated (never `None`).

Derived from:
- Consolidated fallback-rejection and error semantics in this specification.

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
- Each flatline release line tracks exactly one upstream Ghidra decompiler revision.
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
- Decompilation quality may vary across ISAs depending on upstream Sleigh specification maturity; priority ISAs (x86, ARM, RISC-V, MIPS) are validated by fixture matrix, other ISAs are best-effort.
- Some ISA variants (e.g., Thumb/Thumb-2 for ARM, microMIPS) inherit the upstream decompiler's support level without additional library-level guarantees.

### 4.4 Mapping to Public API

| Decompiler-facing capability | Public API behavior | User-visible contract |
| --- | --- | --- |
| Global startup and spec discovery | Session startup and runtime-data validation | Deterministic startup errors with actionable messages |
| Language/compiler descriptions | `list_language_compilers()` | Enumerated pairs are valid and loadable; bridge must validate compiler IDs against enumerated set before native call, since `LanguageDescription::getCompiler()` silently falls back to first/default compiler for unknown IDs (§3.4). If native enumeration is unavailable, bridge derives pairs from runtime-data `.ldefs` entries and filters compiler entries that do not have backing spec files. |
| Function lookup/materialization | `decompile_function(request)` address targeting | Missing/invalid function target returns structured error category |
| Action execution pipeline | Internal execution of request | Successful path yields `c_code` and optional warnings |
| Post-decompile structured data (Funcdata, FuncProto, Scope, Types) | `DecompileResult.function_info` | Structured function metadata, prototype, variables, call sites, jump tables, diagnostics extracted field-by-field at bridge boundary (not via XML serialization) |
| Warning propagation | `DecompileResult.warnings` | Warning codes are stable identifiers |
| Failure propagation | `DecompileResult.error` / exception mapping | No uncaught native exception reaches user |

## 5. Architecture Decision Space (No Implementation Details)

### 5.1 Structural Constraint: LoadImage Abstraction

The decompiler's memory access is fully abstracted through a `LoadImage` interface
(see `decompiler_inventory.md`). The decompiler does not include binary format parsers
(ELF/PE/Mach-O); in Ghidra proper, format parsing is handled by the Java framework
and exposed to the decompiler through `LoadImage`.

This means any binary-file-loading path requires sourcing or building format parsers
outside the decompiler codebase. This is the single largest scope differentiator
between options below.

### 5.2 Option Set

| Option | Description | Input model |
| --- | --- | --- |
| A. Memory + arch + function-level | Caller provides mapped memory region(s), architecture, and function entry point | Memory image or access callback, address, language/arch spec |
| B. Full binary loader path | Caller provides binary file path and function address; library handles format parsing and loading | File path, address, language/arch spec |
| C. Hybrid (A core + B convenience) | Memory-level API as foundational contract with optional binary-loading convenience layer | Either input model |

#### Option A: Memory + Architecture + Function-Level

The caller provides a memory image (or memory-access abstraction) covering the relevant
address space, selects the architecture/language, and specifies the function entry point.

Advantages:
- Directly aligns with the decompiler's native `LoadImage` abstraction — minimal glue.
- Smallest mandatory scope; no binary format parsing required in the library.
- Best composability: callers who already have memory maps (from other tools, emulators,
  debuggers, or custom loaders) use them directly without redundant re-loading.
- Strongest determinism: fewer internal processing steps between input and decompilation.
- Simplest packaging: no format-parser dependencies to ship or maintain.
- Simplest cross-platform story: no platform-specific loader concerns.

Disadvantages:
- Higher caller burden: user must supply mapped memory, not just a file path.
- No automatic section metadata (readonly regions) unless caller provides it.
- No automatic symbol discovery from binary headers.
- Function size hints may be needed for best results.

Risks:
- Decompiler quality may degrade if the caller-provided memory image is incomplete.
  The decompiler may request reads at arbitrary addresses during analysis
  (string references, pointer targets, vtable lookups), not just the target function bytes.
- Users unfamiliar with memory layout concepts face a steeper learning curve.

#### Option B: Full Binary Loader Path

The library accepts a binary file path, internally parses the format, maps the binary
into memory, and handles the decompilation transparently.

Advantages:
- Simplest user-facing API for the common case (decompile function from a file).
- Can leverage format metadata (sections, symbols, relocations) for better quality.
- Lower barrier for casual users.

Disadvantages:
- **Hidden constraint**: the decompiler does not include binary format parsers.
  Implementing or integrating ELF/PE/Mach-O parsing is a significant scope increase
  and ongoing maintenance burden independent of decompiler evolution.
- Format parser code is security-sensitive (processes untrusted input) and a well-known
  source of bugs; this adds attack surface disproportionate to the library's core purpose.
- Larger packaging footprint and more platform-specific concerns.
- Performance: cold-start cost includes format parsing and full memory mapping.
- Reduced composability: callers who already have loaded binaries must re-load from disk.
- Higher fixture complexity: tests need real binary files rather than minimal byte sequences.

Risks:
- Supporting multiple formats (ELF, PE, Mach-O) multiplies surface area; each format
  is itself a complex specification with version-specific edge cases.
- Format parser maintenance becomes a long-term obligation independent of decompiler updates.
- Licensing constraints may apply to third-party parser libraries.

#### Option C: Hybrid (A Core + B Convenience)

Default API uses memory-level input (Option A). An optional convenience layer handles
binary loading for common formats, delegating to the core memory-level API internally.

Advantages:
- Preserves Option A's simplicity and composability as the foundational contract.
- Addresses Option B's UX advantage without coupling the core API to format parsing.
- Convenience layer can be shipped as an optional dependency or separate module.
- Clean separation: core API stability is independent of format-parser evolution.
- Allows incremental format support without destabilizing the primary contract.

Disadvantages:
- Higher initial design complexity (two input paths, shared internals).
- Convenience layer still carries the format-parsing scope of Option B, but isolated.
- Risk of feature creep if users expect the convenience layer to be full-featured.

Risks:
- The convenience layer may become a de facto requirement if Option A proves too
  burdensome, undermining the clean separation.
- Two input paths may create user confusion about which is canonical.

### 5.3 Comparative Analysis

| Criterion | A (Memory+arch) | B (Full binary) | C (Hybrid) |
| --- | --- | --- | --- |
| Determinism | Highest | Moderate | Highest (core) |
| Per-call performance | Best | Good warm / slow cold | Best (core) |
| UX (file-based workflow) | Expert-oriented | Simplest | Good (both paths) |
| UX (tool/pipeline integration) | Best | Weakest (re-load from disk) | Best |
| Packaging complexity | Lowest | Highest | Moderate (optional parser) |
| Cross-platform risk | Lowest | Highest | Low core / moderate convenience |
| Fixture/test burden | Low (byte sequences) | High (real binaries) | Low core / moderate convenience |
| Security surface area | Smallest | Largest | Small core / moderate convenience |
| Upstream alignment | Direct (matches LoadImage) | Indirect (needs parsing layer) | Direct (core) |
| Format parser obligation | None | Major ongoing | Optional, isolated |

### 5.4 Blocking Points and Hidden Constraints

1. **No built-in format parsers** (§5.1): The upstream decompiler provides only
   the abstract `LoadImage` interface and a raw-memory implementation. Any binary-file
   loading path (Option B, or C's convenience layer) requires sourcing format parsers
   from outside the decompiler. This is the single largest architectural differentiator.

2. **Memory completeness for decompiler quality**: The decompiler may read arbitrary
   addresses during analysis, not just the target function bytes. Option A callers must
   provide a sufficiently complete memory image for good results. The library should
   document minimum coverage expectations and degrade gracefully on unavailable regions.

3. **Section metadata impact**: Readonly section information enables decompiler
   optimizations. Option A loses this unless the API provides a way to supply section
   metadata alongside the memory image. This is a design detail for the Option A surface.

4. **Symbol availability**: Format-aware loading (Option B / C convenience) can extract
   symbols for better decompilation. Option A callers must supply symbol information
   separately or accept reduced output quality for symbol-dependent analysis.

5. **Architecture detection**: Option B can auto-detect architecture from binary headers.
   Option A requires explicit caller specification. Not a blocker but affects UX.

6. **Target persona alignment**: The primary personas (reverse engineers, security engineers,
   CI operators) typically work with tools that already provide loaded memory and
   architecture information. This reduces the practical UX burden of Option A relative
   to the general case.

### 5.5 ADR-001 Decision: Option A for MVP

**Decided: Option A (Memory + Architecture + Function-Level) for MVP.**
Planned evolution toward Option C (convenience binary-loading layer) in Next scope.

Rationale:
- Direct alignment with the decompiler's `LoadImage` abstraction. Upstream source confirms
  that in-memory chunk-based LoadImage implementations are a proven pattern within the
  codebase (`LoadImageXml` in `loadimage_xml.hh` stores `map<Address, vector<uint1>>`
  and serves reads from memory).
- Avoids the binary format-parsing scope increase entirely. The decompiler contains no
  built-in format parsers; any binary-loading path requires sourcing or building
  ELF/PE/Mach-O parsing outside the decompiler — a disproportionate scope, security,
  and maintenance cost for MVP.
- Strongest determinism: fewer processing steps between input and decompilation output.
- Target personas (reverse engineers, security engineers, CI operators) typically have
  loaded memory maps available from existing tooling.
- Simplest packaging and cross-platform story: no format-parser dependencies to ship.

Consequences:
- MVP users provide memory images and base addresses, not file paths.
- `DecompileRequest` includes `memory_image` and `base_address` as required fields (§3.3).
- Option C convenience layer (binary file → memory extraction → decompile) is explicit
  Next-scope (§8.3).
- Fixture strategy uses raw memory images extracted from reference binaries, with fixtures covering each priority ISA (x86, ARM, RISC-V, MIPS).

### 5.6 Decision Points Requiring User Choice

1. **(ADR-001, decided)** MVP scope model: Option A (memory + arch + function-level).
   Option C convenience layer planned for Next scope. See §5.5.
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
- `Bridge Contract Layer`: strict translation between public models and native decompiler calls. Implemented as a nanobind C++ extension module (ADR-002). The extension module and all C++ code are unstable internals.
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
- Concurrency model assumes CPython GIL or caller-provided external serialization. Free-threaded Python (3.13t) support is post-MVP.

Performance budgets (planning targets):
- Session startup (warm): bounded target defined per release.
- Single-function decompile on MVP fixture set: p95 budget tracked in CI per priority ISA.
- Regression threshold policy: fail CI on sustained >15% regression for pinned matrix.
- Performance budgets are tracked independently per ISA family; different Sleigh specifications may have inherently different analysis costs.

Security boundaries:
- Untrusted memory images are treated as untrusted input.
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

## 8. MVP vs Next and Reconciliation Notes

### 8.1 MVP Commitments (Kept)

- Linux host-first single-function scope.
- Multi-ISA target support: any Ghidra decompiler-supported architecture. Priority ISAs (x86, ARM, RISC-V, MIPS) have bundled runtime data and representative fixture coverage per ADR-009: x86 (32+64-bit), ARM64, RISC-V 64, MIPS32. Other Ghidra-supported ISAs available through bundled runtime data with enumeration and error-contract coverage.
- Runtime data directory contract with packaged default and explicit override; bundles language/compiler assets for all priority ISAs.
- Pair enumeration from language descriptions with existence filtering across all bundled ISAs.
- Structured results with warnings/errors/metadata.

### 8.2 Items Marked Obsolete and Replaced

| Former MVP contract draft item | Status | Replacement in this spec |
| --- | --- | --- |
| Binding mechanism named as `ctypes`/`cffi` in normative scope | Obsolete as normative requirement | Replaced with bridge-agnostic in-process contract; binding choice deferred to ADR. |
| Implicitly narrow curated compiler list as fixed forever | Obsolete as permanent restriction | Replaced with MVP curated baseline plus additive expansion policy under SemVer minor releases. |
| Console-path behavior note as implementation framing | Obsolete as behavior reference | Replaced with explicit API rule: invalid addresses are structured hard errors. |
| Focus on C ABI wording as primary public contract | Obsolete for top-level spec | Replaced with Python-first contract and separate bridge contract boundary. |

### 8.3 Next-Scope Candidates

- Binary convenience layer: Option C file-loading convenience API over the core
  memory-image contract, handling ELF/PE/Mach-O parsing and memory extraction.
- Multi-region memory input and section metadata (readonly ranges, symbols) extensions
  to `DecompileRequest`.
- Batch decompilation APIs.
- Cross-platform host parity (macOS/Windows).
- Extended fixture coverage for non-priority Ghidra-supported ISAs beyond the MVP set.

## 9. Open Questions

Resolved:
- ~~Is canonicalized C output required as a hard contract, or only semantic/token-level stability?~~ **Resolved (ADR-003):** Normalized token/structure comparison, not canonical text. See `tests/specs/fixtures.md` §2.
- ~~For multi-ISA fixture variants: ARM64 vs ARM32? MIPS32 vs MIPS64?~~ **Resolved (ADR-009):** x86 gets both 32-bit and 64-bit fixture coverage; other ISA families have one representative variant each — ARM64, RISC-V 64, MIPS32 — for diverse bitwidth coverage. Other variants best-effort. See `tests/specs/fixtures.md` §1.

Open:
- Should warning codes be globally namespaced now to prevent future collisions? (Initial codes will be defined during P2 implementation.)
- Should analysis-budget defaults vary by platform or target ISA, or remain globally fixed?
- Should session-level failure categories (startup, initialization) be defined explicitly in the `FlatlineError` hierarchy, or is the current `ErrorItem` taxonomy sufficient?
- How strict should package-size limits or install-profile guidance be now that runtime data is distributed via `ghidra-sleigh` and its default build is multi-ISA?
- How should flatline pin or validate compatible `ghidra-sleigh` versions so runtime data matches flatline's pinned Ghidra upstream revision?
- ~~Should the runtime data package bundle all Ghidra-supported ISA assets or only the priority set (x86, ARM, RISC-V, MIPS), with an extension mechanism for others?~~ **Resolved (ADR-010):** `ghidra-sleigh` defaults to shipping compiled runtime data for all Ghidra processor families and also supports a lighter major-ISA build via `all_processors=false`. Flatline's default profile policy remains tracked in ADR-004.
- ~~Should ISA-specific Sleigh compilation (`.sla` files) happen at build time or install time?~~ **Resolved (ADR-010):** Build time. `ghidra-sleigh` builds `sleighc` from Ghidra C++ sources and ships the compiled `.sla` outputs as package data.
- ~~Should `TypeInfo` expose sub-type details (struct fields, array element type, pointer target) in MVP, or is the flat `name`/`size`/`metatype` sufficient?~~ **Resolved:** Flat `name`/`size`/`metatype` for MVP. Sub-type details (struct fields, pointer target, array element) deferred to post-MVP.
- Should `CallSiteInfo` include a `callee_name` field when the target is a known function symbol? (Affects bridge scope.)
- Should `JumpTableInfo` include an `is_complete` flag for partial recovery? (Affects test assertions.)

## 10. Assumptions

- Upstream baseline remains fixed until deliberate bump planning is triggered.
- Users accept latest-upstream-only support policy.
- MVP fixture binaries can be redistributed under project licensing policy.
- Linux host-first release can ship before cross-platform host parity without violating product goals.
- Upstream Sleigh specifications for priority ISAs (x86, ARM, RISC-V, MIPS) are sufficiently mature for production-quality decompilation.
- Bundling language/compiler assets for all priority ISAs does not exceed acceptable package size limits (tracked in risk register).
