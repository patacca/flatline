# flatline Specification (SDD)

## 0. Scope and Sources

Vendored decompiler source: `third_party/ghidra` git submodule (exact commit
tracked by the submodule pointer).

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
- MVP target ISA scope: any Ghidra decompiler-supported binary architecture. Flatline's default runtime data exposes all bundled processor families. Confidence-backed fixture coverage is committed for x86 (32/64), ARM64, RISC-V 64, and MIPS32; other ISA variants remain best-effort.
- Python: `3.13+`.
- Version policy: support only the latest Ghidra decompiler version.

## 1. Goals and Non-Goals

Goals:
- **User-centered design.** Every feature, default, error message, and API surface is designed from the caller's perspective first. No design decision should work against the user or force them to fight the API.
- Provide a stable Python-first decompilation contract that remains consistent while upstream internals change.
- Expose single-function decompilation with explicit language/compiler selection and structured diagnostics.
- Support decompilation of any Ghidra-supported target ISA from a single installation, while publishing stronger confidence guarantees only for the fixture-backed variants.
- Make runtime assets self-contained for out-of-the-box installation.
- Make support-confidence boundaries explicit so callers can distinguish bundled breadth from fixture-backed confidence.
- Define testable behavioral guarantees before implementation details.

Non-goals:
- Full parity with every upstream decompiler feature in MVP.
- Whole-program project modeling in MVP.
- Supporting multiple Ghidra decompiler versions simultaneously.
- Defining build scripts, binding mechanics, or C/C++ implementation internals in this document.
- Guaranteeing identical decompilation quality across all ISAs or ISA variants; only x86 (32/64), ARM64, RISC-V 64, and MIPS32 carry representative fixture-backed confidence, while other bundled targets are best-effort with enumeration and error-contract coverage only.

## 2. Personas and Use Cases

Personas:
- Reverse engineer automating decompilation pipelines from Python.
- Security engineer building repeatable triage workflows.
- Tooling engineer embedding deterministic decompilation checks into CI or release validation.
- Researcher building binary similarity or diffing tools from decompiler output.
- Security researcher performing data flow or taint analysis on decompiled functions.

Primary use cases:
- Decompile one function by memory image + architecture + entry address (ADR-001 resolved: Option A).
- Decompile functions from any Ghidra-supported target ISA (x86, ARM, RISC-V, MIPS, and others) by specifying the appropriate `language_id`.
- Enumerate valid `(language_id, compiler_spec)` pairs shipped in runtime data, spanning all bundled ISAs.
- Fail predictably on invalid addresses/unsupported language selection.
- Run repeated decompiles in one process with isolated request state.

Secondary (Next):
- Batch execution over many functions with bounded resources.
- Cross-platform parity (macOS/Windows).

P7 Opt-in Enriched Output:
- Extract pcode intermediate representation sequences for custom analysis pipelines.
- Access varnode data flow graphs as frozen Python value types for binary similarity computation (e.g., BSim reimplementation with custom hyperparameters and feature vectors).
- Build binary diffing pipelines using normalized function representations (pcode sequences, control flow graph edges, varnode topology).
- Perform semantic analysis or taint tracking over structured decompiler output without requiring knowledge of Ghidra C++ internals.

## 3. Public Python API Contract

### 3.1 Concepts

| Concept | Contract |
| --- | --- |
| `DecompilerSession` | Long-lived object owning one native bridge session and immutable startup config. Amortizes startup costs (library initialization, runtime data resolution, language/compiler enumeration) across calls. |
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
| `AnalysisBudget` | Deterministic per-request resource limits. MVP/P2 exposes only `max_instructions`. |
| `EnrichedOutput` | Optional P7 companion payload containing post-simplification pcode operations and varnode use-def graph data. |
| `PcodeOpInfo` | One pcode operation exported as a frozen value type with stable IDs and varnode references. |
| `VarnodeInfo` | One varnode exported as a frozen value type with stable IDs and defining/use op references. |
| `VarnodeFlags` | Stable boolean classification flags exported for one varnode. |
| `FlatlineError` | Stable Python exception hierarchy mapped from status/error categories. |

Derived from:
- Consolidated MVP contract requirements in this specification.

### 3.2 Operations

| Operation | Purpose | Minimum behavior |
| --- | --- | --- |
| `DecompilerSession.list_language_compilers()` | Enumerate valid language/compiler pairs | Returns only pairs with required backing assets present in runtime data. If `runtime_data_dir` was omitted at session startup, the session auto-discovers the installed `ghidra_sleigh` runtime-data root first. Covers all bundled ISAs (priority: x86, ARM, RISC-V, MIPS; plus any other Ghidra-supported ISAs whose assets are included). |
| `DecompilerSession.decompile_function(request)` | Decompile one function | Returns `DecompileResult`; no native exceptions leak across public boundary. |
| `flatline.list_language_compilers(runtime_data_dir=None)` | One-shot convenience wrapper for pair enumeration | Creates a short-lived `DecompilerSession`, auto-discovers the installed `ghidra_sleigh` runtime-data root when `runtime_data_dir` is omitted, runs enumeration, and closes the session deterministically. |
| `flatline.decompile_function(request)` | One-shot convenience wrapper for decompilation | Creates a short-lived `DecompilerSession`, auto-discovers the installed `ghidra_sleigh` runtime-data root when `request.runtime_data_dir` is omitted, runs decompilation, and closes the session deterministically. |
| `get_version_info()` | Report runtime versions | Includes flatline version and decompiler engine version. |

`DecompilerSession` is the canonical surface for repeated calls in one process.
Module-level operation functions are convenience wrappers for single-call workflows.

### 3.3 Data Model

`DecompileRequest` fields:
- `memory_image` (required): byte content of the target memory region
- `base_address` (required): virtual address of the start of `memory_image`
- `function_address` (required): entry point virtual address within the memory image
- `language_id` (required)
- `compiler_spec` (optional, explicit validation required)
- `runtime_data_dir` (optional explicit override over the dependency-provided default runtime-data root)
- `function_size_hint` (optional advisory)
- `analysis_budget` (optional `AnalysisBudget`; omitted requests default to `AnalysisBudget(max_instructions=100000)`)
- `include_enriched_output` (optional bool; default `False`) — when `True`, success requires `DecompileResult.enriched_output` to be populated with post-simplification pcode + varnode graph data

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
  - `metadata["decompiler_version"]` — version of the underlying Ghidra decompiler engine, not of flatline itself
  - `metadata["language_id"]`
  - `metadata["compiler_spec"]`
  - `metadata["diagnostics"]` — legacy key; superseded by `function_info.diagnostics` when `function_info` is present
- `enriched_output: EnrichedOutput | None` — populated only when `include_enriched_output=True` and decompilation succeeds

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

`AnalysisBudget` fields:
- `max_instructions: int` — positive per-request instruction cap applied to `Architecture::max_instructions`; default `100000`

P2 scope exposes only the instruction-count budget because the pinned upstream
callable surface has no wall-clock timeout or cancellation hook. Time-based
limits remain a future extension requiring explicit upstream-compatible
mechanisms.

`EnrichedOutput` fields:
- `pcode_ops: list[PcodeOpInfo]`
- `varnodes: list[VarnodeInfo]`

`PcodeOpInfo` fields:
- `id: int` — stable integer ID assigned by `Funcdata::beginOpAll()` order
- `opcode: str` — canonical Ghidra opcode name from `get_opname(OpCode)` (for example `INT_ADD`, `COPY`, `RETURN`)
- `instruction_address: int` — original instruction address for the pcode op (`PcodeOp::getAddr()`)
- `sequence_time: int` — sequence-number time field (`SeqNum::getTime()`)
- `sequence_order: int` — sequence-number order field (`SeqNum::getOrder()`)
- `input_varnode_ids: list[int]` — input varnode IDs in slot order
- `output_varnode_id: int | None` — output varnode ID when present

`VarnodeFlags` fields:
- `is_constant: bool`
- `is_input: bool`
- `is_free: bool`
- `is_implied: bool`
- `is_explicit: bool`
- `is_read_only: bool`
- `is_persist: bool`
- `is_addr_tied: bool`

`VarnodeInfo` fields:
- `id: int` — stable integer ID assigned on first encounter while walking pcode ops in ID order (output first, then inputs by slot)
- `space: str` — address-space name for the varnode storage/value
- `offset: int` — address-space offset or constant value offset
- `size: int` — varnode size in bytes
- `flags: VarnodeFlags`
- `defining_op_id: int | None` — pcode op that defines this varnode, if any
- `use_op_ids: list[int]` — pcode ops that read this varnode

`WarningItem` fields:
- `code: str` — stable warning code using hierarchical namespace (`<phase>.<code>`, e.g., `analyze.W001`); flatline reserves this namespace and may add new codes additively in minor releases
- `message: str` — human-readable warning text (informative, not exact-match stable); may include full filesystem paths for debuggability
- `phase: str` — phase that produced the warning (`init`, `analyze`, `emit`)

`ErrorItem` fields:
- `category: str` — stable error category (`invalid_argument`, `unsupported_target`, `invalid_address`, `decompile_failed`, `configuration_error`, `internal_error`)
- `message: str` — human-readable error text (informative, not exact-match stable); may include full filesystem paths for debuggability
- `retryable: bool` — whether the operation may succeed on retry with the same inputs

`VersionInfo` fields:
- `flatline_version: str`
- `decompiler_version: str` — version of the underlying Ghidra decompiler engine, not of flatline itself

All structured result objects (`FunctionInfo`, `FunctionPrototype`, `ParameterInfo`, `VariableInfo`, `TypeInfo`, `CallSiteInfo`, `JumpTableInfo`, `DiagnosticFlags`, `StorageInfo`, `LanguageCompilerPair`, `WarningItem`, `ErrorItem`, `VersionInfo`, `EnrichedOutput`, `PcodeOpInfo`, `VarnodeInfo`, `VarnodeFlags`) are pure Python frozen value types. Data is extracted at the bridge boundary; no native pointers or references survive past the bridge call.

Error model for structured results:
- If `DecompileResult.error` is set, then `function_info` is `None` and `c_code` is `None`.
- If `DecompileResult.error` is set, then `enriched_output` is `None`.
- If decompilation succeeds, `function_info` is populated (never `None`) and `c_code` is set.
- If `include_enriched_output` is `True` and decompilation succeeds, `enriched_output` is populated (never `None`).
- If `include_enriched_output` is `False`, `enriched_output` remains `None`.
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
- Unsupported `analysis_budget` fields or non-positive `analysis_budget.max_instructions` values are hard errors. Error category: `invalid_argument`.
- Missing or malformed runtime-data setup is a hard startup error. Explicit bad `runtime_data_dir` values, malformed runtime-data roots, or omitting `runtime_data_dir` when the `ghidra-sleigh` dependency is unavailable all use error category: `configuration_error`.
- Calling session operations after `DecompilerSession.close()` is a hard error. Error category: `invalid_argument`.
- Error categories are contract-stable; text may change but remains human-readable.
- Public warning/error text may include full filesystem paths for debuggability; raw memory-image bytes must never be emitted in diagnostics.
- Warning-only outcomes must still return successful operation status when C output is valid.
- When `error` is set, `function_info` is always `None` and `c_code` is always `None`.
- When `error` is set, `enriched_output` is always `None`.
- When decompilation succeeds, `function_info` is always populated (never `None`).
- When `include_enriched_output` is `True`, successful results must populate `enriched_output`; flatline must fail hard rather than silently dropping the companion payload.
- Auto-discovered `ghidra-sleigh` runtime data that does not match flatline's pinned upstream baseline must emit an observable warning, not degrade silently. Explicit `runtime_data_dir` overrides are treated as user-managed custom assets.

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
- The first public flatline release finalizes the existing `0.1.0.devN`
  development line as `0.1.0`; that tag establishes the initial public SemVer
  baseline for later major/minor/patch classification.

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
- Decompilation quality may vary across ISAs depending on upstream Sleigh specification maturity; fixture-backed confidence is committed only for x86 (32/64), ARM64, RISC-V 64, and MIPS32, while other ISAs are best-effort.
- Some ISA variants (e.g., Thumb/Thumb-2 for ARM, microMIPS) inherit the upstream decompiler's support level without additional library-level guarantees.

### 4.4 Mapping to Public API

| Decompiler-facing capability | Public API behavior | User-visible contract |
| --- | --- | --- |
| Global startup and spec discovery | Session startup and runtime-data validation | Deterministic startup errors with actionable messages |
| Language/compiler descriptions | `list_language_compilers()` | Enumerated pairs are valid and loadable; bridge must validate compiler IDs against enumerated set before native call, since `LanguageDescription::getCompiler()` silently falls back to first/default compiler for unknown IDs (§3.4). If native enumeration is unavailable, bridge derives pairs from runtime-data `.ldefs` entries and filters compiler entries that do not have backing spec files. |
| Function lookup/materialization | `decompile_function(request)` address targeting | Missing/invalid function target returns structured error category |
| Action execution pipeline | Internal execution of request | Successful path yields `c_code` and optional warnings |
| Post-decompile structured data (Funcdata, FuncProto, Scope, Types) | `DecompileResult.function_info` | Structured function metadata, prototype, variables, call sites, jump tables, diagnostics extracted field-by-field at bridge boundary (not via XML serialization) |
| Post-simplification IR graph (PcodeOp, Varnode) | `DecompileResult.enriched_output` when `include_enriched_output=True` | Pcode ops and varnode use-def edges are exported as frozen value types with stable integer IDs; opt-in requests must not silently degrade |
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
   tooling engineers integrating CI/release checks) typically work with tools that already provide loaded memory and
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
- Target personas (reverse engineers, security engineers, tooling engineers integrating CI/release checks) typically have
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
4. **(ADR-005, decided)** Default analysis budget behavior:
   - Fixed bounded default: `AnalysisBudget(max_instructions=100000)` on every request.
   - Explicit override: callers may raise or lower `max_instructions` per request.
   - Out of scope for P2: wall-clock timeout, because the pinned upstream callable surface
     exposes only instruction-count limiting (`Architecture::max_instructions`).

## 6. Stable Python API over Unstable Upstream Strategy

Adapter boundaries:
- `Public Contract Layer`: Python request/result models and error taxonomy.
- `Bridge Contract Layer`: strict translation between public models and native decompiler calls. Implemented as a nanobind C++ extension module (ADR-002). The extension module and all C++ code are unstable internals.
- `Upstream Adapter Layer`: handles upstream callable surface and lifecycle changes.

Contract-test strategy:
- API contract tests validate field presence/types/error categories.
- Behavior tests validate deterministic outcomes for pinned fixtures.
- Negative tests ensure structured errors for unsupported language/compiler/addresses.
- Build/workflow config tests are smoke checks over contract-critical behavior;
  they should avoid pinning incidental YAML/TOML structure, step names, cache
  settings, or exact shell formatting when equivalent behavior is preserved.
- Add workflow/config tests only when the asserted behavior is a durable product
  or release contract boundary such as the published wheel matrix, release
  routing, native-build enforcement, or another user-visible support guarantee.
- Do not add dedicated tests for routine CI/workflow toggles, security-tool
  enablement, housekeeping, or other changes whose failure mode is already
  visible in GitHub Actions itself rather than in shipped package behavior.

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
- Single-function decompile on MVP fixture set: committed warm-session p95 budgets tracked per
  fixture in `tests/_native_fixtures.py`.
- Regression threshold policy: the pinned Linux CI regression lane fails when any committed
  fixture exceeds its source-controlled normalized-output or warm-session p95 budget.
- Performance budgets are tracked independently per ISA family; different Sleigh specifications may have inherently different analysis costs.

Security boundaries:
- Untrusted memory images are treated as untrusted input.
- No implicit execution of external tools in request path.
- Resource budgets are part of the operational contract.
- P2 enforces only the per-request instruction budget (`AnalysisBudget.max_instructions`);
  wall-clock timeout support is deferred until the upstream callable surface provides
  a compatible cancellation mechanism.

Logging and diagnostics:
- P2 does not expose a general-purpose structured logging sink or user-configurable redaction controls.
- Public diagnostics are emitted only through startup/runtime-data `RuntimeWarning` messages and structured `WarningItem` / `ErrorItem` payloads.
- `WarningItem.phase` remains the public phase enum (`init`, `analyze`, `emit`); startup/runtime-data discovery warnings stay outside that enum because they are emitted before result construction.
- Diagnostic text may include stable identifiers (warning code, error category, phase, language/compiler ids, upstream tag/commit), aggregate counts, filenames, and full filesystem paths.
- Raw request bytes and memory-image contents are never emitted in diagnostics.

Configuration:
- Explicit runtime data dir override.
- Explicit analysis budget control via `AnalysisBudget.max_instructions`.
- Deterministic defaults when options are omitted.

Packaging and compliance:
- Release artifacts must ship the root `LICENSE` and `NOTICE` files; `pyproject.toml` declares both through `license-files`.
- Wheels and sdists ship only the public runtime modules (`__init__`, `_bridge`,
  `_errors`, `_models`, `_runtime_data`, `_session`, `_version`) plus the
  optional native extension. Repo-only release tools now live under
  `tools/flatline_dev/` with thin `tools/*.py` wrappers; `tools/prune_dist.py`
  prunes that entire tree from Meson sdists, and the wheel never installs it.
  These repo-only commands are not end-user entry points.
- Redistribution review passes only when `python tools/compliance.py` succeeds from the repo root.
- The compliance audit verifies the vendored decompiler source attribution via the `third_party/ghidra` submodule, the `ghidra-sleigh` runtime dependency declaration, and the synthetic-fixture redistribution note in `tests/fixtures/README.md`.
- Built wheel and sdist artifacts are audited with `python tools/artifacts.py`
  before tagging so release review can verify the current version metadata, the
  `ghidra-sleigh` dependency, and the shipped `LICENSE` / `NOTICE`
  files from the actual artifacts rather than by repo contents alone.
  Platform-specific wheels must also carry the `_flatline_native` extension.
- `.github/workflows/release.yml` is the source-controlled publish pipeline for
  release artifacts. It runs only on GitHub `release.published` or
  `workflow_dispatch`, builds the ADR-013 Tier-1 wheel matrix via
  `cibuildwheel` (manylinux `x86_64` / `aarch64`, Windows `AMD64`, and macOS
  `x86_64` / `arm64` for CPython 3.13 and 3.14) plus the sdist, validates them with
  `twine check dist/*` plus `python tools/artifacts.py dist --repo-root .`,
  and trusted-publishes manual dispatches to TestPyPI while release-triggered
  publishes target PyPI. Manual TestPyPI dispatches must use a unique version;
  duplicate uploads are a hard failure, not a skipped publish.
- The Tier-1 wheel builds must run an installed-wheel smoke check through
  `cibuildwheel` before publish, exercising the public API with omitted
  `runtime_data_dir` so transitive `ghidra-sleigh` installation, default
  runtime-data discovery, and the x86_64 `add(a,b)` fixture decompile are all
  validated together.
- After publish, the release workflow must install the exact released version
  back from TestPyPI or PyPI on every Tier-1 platform/arch/Python combination,
  using binary-only install mode so the smoke path proves `pip install
  flatline` succeeds without a local compiler and still auto-discovers the
  transitive `ghidra-sleigh` runtime-data dependency.
- The final public-artifact review gate is documented in
  `docs/release_review.md`; it must stay source-controlled and tie the human
  sign-off to the deterministic evidence from `python tools/release.py`,
  `tox`, `python tools/compliance.py`, `python tools/footprint.py`,
  `python -m build`, and `python tools/artifacts.py dist`. The checklist stays
  in the repo, but the per-run approval notes and reviewed artifact identifiers
  are kept outside git and reported out-of-band.
- Default-install footprint is measured with `python tools/footprint.py`,
  using shipped payload files only (excluding interpreter-generated
  `__pycache__` / `.pyc` entries). `docs/footprint.md` records the current
  reference baseline and any explicit product-policy decision about keeping or
  changing the full multi-ISA default.

Release-facing policy:
- Each public release must publish or update a release-notes artifact that
  summarizes the contract guarantees users can rely on, the support tiers for
  the supported host and target matrix, the known ISA-variant limits, and the
  upgrade policy for that release line.
- When the published wheel-install matrix is broader than the supported host
  contract, release-facing notes must list wheel availability separately and
  say that published wheels mean `pip install flatline` succeeds without a
  local compiler on those targets, not that the host-support tier changed.
- Release-facing support notes must distinguish the Linux x86_64
  fixture-backed confidence matrix (x86 32/64, ARM64, RISC-V 64, MIPS32) from
  bundled best-effort ISAs or variants that are covered only by enumeration
  and error-contract tests.
- Release-facing upgrade notes must restate the latest-upstream-only policy,
  SemVer classification rules, the minimum one-minor deprecation window, and
  the caller-managed compatibility risk of custom `runtime_data_dir` roots.
- The initial public release must also keep the human artifact-review checklist
  in `docs/release_review.md` aligned with the release workflow, changelog, and
  release notes so the final sign-off criteria are explicit, with an external
  approval hold point before tagging and no requirement to commit review notes.
- The initial public release workflow and its `0.1.0` version recommendation
  are source-controlled in `docs/release_workflow.md` and audited by
  `python tools/release.py` before the release tag is created.

Cross-platform feasibility policy:
- Post-MVP host expansion proceeds macOS first and Windows second (ADR-008).
- Release-facing support notes list Linux x86_64, macOS arm64, and Windows
  x86_64 as supported runtime hosts because those targets now have both
  dedicated native contract lanes and index-backed wheel validation. Linux
  aarch64 and macOS x86_64 remain published-wheel targets until they gain the
  same continuous host evidence.
- Shared Meson/native-build paths must select compiler-argument syntax through
  Meson rather than hardcoding GCC-only flags in a way that prevents MSVC-family
  feasibility work from starting, and staged third-party header roots must flow
  through Meson include directories instead of compiler-specific `-I` / `/I`
  arguments.
- P6 feasibility keeps dedicated macOS arm64 and Windows x86_64 CI lanes on
  the installed-wheel non-regression tox matrix, using a native-forced tox env
  so `native_bridge=enabled` cannot silently fall back to the Python bridge.
  Published-wheel smoke on the Tier-1 release matrix covers Linux aarch64 and
  macOS x86_64 until those targets gain dedicated host-promotion evidence.
- `docs/host_feasibility.md` records the current platform audit, the ordered
  host-expansion rationale, and the concrete evidence required before a new host
  can move from feasibility to supported status.

Extensibility:
- Additive extension points via optional request fields and metadata keys.
- Future backends or advanced modes must preserve baseline contract semantics.

## 8. MVP vs Next and Reconciliation Notes

### 8.1 MVP Commitments (Kept)

- Linux host-first single-function scope.
- Multi-ISA target support: any Ghidra decompiler-supported architecture. The default runtime-data install exposes all bundled processor families, while fixture-backed confidence is committed only for the ADR-009 matrix: x86 (32+64-bit), ARM64, RISC-V 64, and MIPS32. Other bundled ISAs and variants are available with enumeration and error-contract coverage only.
- Runtime data directory contract with dependency-backed default and explicit override; flatline installs `ghidra-sleigh` for the default UX, auto-discovers its runtime-data root when no override is provided, and still accepts custom runtime-data paths.
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
- Enriched-output follow-ons: add CFG/basic-block exports, richer symbol/type
  links on pcode and varnodes, broader fixture coverage, and additional
  end-to-end downstream validations beyond the current use-def graph slice.

## 9. Open Questions

Resolved:
- ~~Is canonicalized C output required as a hard contract, or only semantic/token-level stability?~~ **Resolved (ADR-003):** Normalized token/structure comparison, not canonical text. See `tests/specs/fixtures.md` §2.
- ~~For multi-ISA fixture variants: ARM64 vs ARM32? MIPS32 vs MIPS64?~~ **Resolved (ADR-009):** x86 gets both 32-bit and 64-bit fixture coverage; other ISA families have one representative variant each — ARM64, RISC-V 64, MIPS32 — for diverse bitwidth coverage. Other variants best-effort. See `tests/specs/fixtures.md` §1.
- ~~How strict should package-size limits or install-profile guidance be now that runtime data is distributed via `ghidra-sleigh` and its default build is multi-ISA?~~ **Resolved (ADR-004):** Flatline's default install depends on `ghidra-sleigh` and therefore follows its full multi-ISA runtime-data profile for the out-of-the-box UX. `all_processors=false` remains supported only as a custom runtime-data choice via explicit `runtime_data_dir`. Flatline does not add a second wheel-size gate in P2; size/compliance remains a P3 concern.
- ~~How should flatline pin or validate compatible `ghidra-sleigh` versions so runtime data matches flatline's pinned Ghidra upstream revision?~~ **Resolved (ADR-004):** Flatline auto-discovers the installed `ghidra_sleigh` runtime-data root by default, warns when the companion package advertises a different upstream tag/commit than flatline's pin, and still allows explicit `runtime_data_dir` overrides for user-managed custom assets.
- ~~Should the runtime data package bundle all Ghidra-supported ISA assets or only the priority set (x86, ARM, RISC-V, MIPS), with an extension mechanism for others?~~ **Resolved (ADR-010):** `ghidra-sleigh` defaults to shipping compiled runtime data for all Ghidra processor families and also supports a lighter major-ISA build via `all_processors=false`. ADR-004 now defines flatline's default policy as depending on the full install while leaving lighter builds as explicit overrides.
- ~~Should ISA-specific Sleigh compilation (`.sla` files) happen at build time or install time?~~ **Resolved (ADR-010):** Build time. `ghidra-sleigh` builds `sleighc` from Ghidra C++ sources and ships the compiled `.sla` outputs as package data.
- ~~Should analysis-budget defaults vary by platform or target ISA, or remain globally fixed?~~ **Resolved (ADR-005):** P2 uses a single fixed default, `AnalysisBudget(max_instructions=100000)`, across the Linux MVP matrix. Callers may override `max_instructions` per request; wall-clock timeout remains out of scope until the upstream callable surface exposes a compatible cancellation mechanism.
- ~~Which diagnostic fields are emitted and redacted by default?~~ **Resolved (ADR-006):** P2 emits diagnostics only through startup/runtime-data `RuntimeWarning` messages plus structured `WarningItem` / `ErrorItem` results. Diagnostic text may include full filesystem paths for debuggability; raw memory-image bytes are never emitted. No path redaction is applied because flatline is a library running in the caller's own process, and its target personas (reverse engineers, security engineers, tooling engineers) benefit from full paths for troubleshooting.
- ~~What release-time checks are mandatory for redistribution?~~ **Resolved (ADR-007):** Releases must ship root `LICENSE` and `NOTICE`, record the vendored decompiler source attribution and `ghidra-sleigh` dependency in `docs/compliance.md`, and pass `python tools/compliance.py` from the repo root before tagging.
- ~~Should macOS or Windows be the first post-MVP host-expansion target?~~ **Resolved (ADR-008):** macOS first, then Windows. P6 starts by removing shared build-configuration assumptions and proving equivalent contract coverage on macOS before taking on the remaining Windows-specific blockers.
- ~~Which pre-built wheel matrix should flatline ship for P6.5?~~ **Resolved (ADR-013):** `cibuildwheel` builds CPython 3.13 and 3.14 wheels for manylinux `x86_64`, manylinux `aarch64`, Windows `AMD64`, macOS `x86_64`, and macOS `arm64`, using native GitHub-hosted runners where available; `manylinux_2_28` remains the Linux policy and macOS deployment target stays `11.0`. 32-bit and Windows ARM64 wheels stay deferred.
- ~~How should enriched structured output be surfaced once P7 starts: inside `FunctionInfo` or as a separate payload, and at what extraction point?~~ **Resolved (ADR-012):** P7 keeps `FunctionInfo` focused on the existing decompilation contract and adds an opt-in companion value type under `DecompileResult` for pcode ops plus varnode graph data. Extraction happens after `Action::perform()` from the post-simplification `Funcdata`, and graph relationships are encoded with stable integer IDs plus string opcode / address-space names so no native handles cross the ABI.
- ~~Should warning codes be globally namespaced now to prevent future collisions?~~ **Resolved:** Yes, within flatline's public surface. Warning codes use the stable hierarchical namespace `<phase>.Wxxx` (for example `analyze.W001`), and new codes are added only additively.
- ~~Should session-level failure categories (startup, initialization) be defined explicitly in the `FlatlineError` hierarchy, or is the current `ErrorItem` taxonomy sufficient?~~ **Resolved (ADR-011):** User-fixable install/startup/runtime-data failures use `configuration_error`, while unexpected flatline/bridge/native bugs remain `internal_error`.

Open:
- ~~Should `TypeInfo` expose sub-type details (struct fields, array element type, pointer target) in MVP, or is the flat `name`/`size`/`metatype` sufficient?~~ **Resolved:** Flat `name`/`size`/`metatype` for MVP. Sub-type details (struct fields, pointer target, array element) deferred to post-MVP.
- Should `CallSiteInfo` include a `callee_name` field when the target is a known function symbol? (Affects bridge scope.)
- Should `JumpTableInfo` include an `is_complete` flag for partial recovery? (Affects test assertions.)

## 10. Assumptions

- Upstream baseline remains fixed until deliberate bump planning is triggered.
- Users accept latest-upstream-only support policy.
- MVP fixture binaries can be redistributed under project licensing policy.
- Linux host-first release can ship before cross-platform host parity without violating product goals.
- Upstream Sleigh specifications for the committed confidence variants (x86 32/64, ARM64, RISC-V 64, MIPS32) are sufficiently mature for production-quality decompilation.
- Shipping the default full multi-ISA runtime-data install remains acceptable for the out-of-the-box UX, with footprint tracked explicitly as a release/compliance concern rather than an automatic trigger for default ISA fragmentation.
