# ghidralib Specification (SDD)

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
- Decompile one function by memory image + architecture + entry address (ADR-001 resolved: Option A).
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
| `DecompilerSession` | Long-lived object owning one native `Architecture` instance and immutable startup config. Session lifecycle maps to Architecture construction through destruction. |
| `DecompileRequest` | Input payload for one function decompilation: memory image, base address, function entry address, language, optional compiler and analysis options. |
| `DecompileResult` | Output payload containing rendered C text, warnings, structured error (if any), and metadata. |
| `LanguageCompilerPair` | One valid `language_id` + `compiler_spec` entry known to current runtime data directory. |
| `GhidralibError` | Stable Python exception hierarchy mapped from status/error categories. |

Derived from:
- Consolidated MVP contract requirements in this specification.

### 3.2 Operations

| Operation | Purpose | Minimum behavior |
| --- | --- | --- |
| `list_language_compilers()` | Enumerate valid language/compiler pairs | Returns only pairs with required backing assets present in runtime data. |
| `decompile_function(request)` | Decompile one function | Returns `DecompileResult`; no native exceptions leak across public boundary. |
| `get_version_info()` | Report runtime versions | Includes ghidralib version, pinned upstream commit/tag, and runtime data revision id. |

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

`VersionInfo` fields:
- `ghidralib_version: str`
- `upstream_tag: str`
- `upstream_commit: str`
- `runtime_data_revision: str`

Derived from:
- Consolidated MVP data and error contract in this specification.
- Consolidated invalid-address hard-failure requirement carried into negative tests.

### 3.4 Error Model

Rules:
- Unknown compiler ids are hard errors (no implicit fallback).
- Invalid/unmapped addresses are hard errors, not warning-only degraded output.
- Error categories are contract-stable; text may change but remains human-readable.
- Warning-only outcomes must still return successful operation status when C output is valid.

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
| Language/compiler descriptions | `list_language_compilers()` | Enumerated pairs are valid and loadable; bridge must validate compiler IDs against enumerated set before native call, since `LanguageDescription::getCompiler()` silently falls back to first/default compiler for unknown IDs (§3.4) |
| Function lookup/materialization | `decompile_function(request)` address targeting | Missing/invalid function target returns structured error category |
| Action execution pipeline | Internal execution of request | Successful path yields `c_code` and optional warnings |
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
- Fixture strategy uses raw memory images extracted from reference binaries.

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

- Linux-first single-function scope.
- Runtime data directory contract with packaged default and explicit override.
- Pair enumeration from language descriptions with existence filtering.
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
- Cross-platform artifact parity (macOS/Windows).

## 9. Open Questions

- Should warning codes be globally namespaced now to prevent future collisions?
- Is canonicalized C output required as a hard contract, or only semantic/token-level stability?
- Should analysis-budget defaults vary by platform or remain globally fixed?
- How strict should package-size limits be for bundled runtime assets?
- Should session-level failure categories (startup, initialization) be defined explicitly in the `GhidralibError` hierarchy, or is the current `ErrorItem` taxonomy sufficient?

## 10. Assumptions

- Upstream baseline remains fixed until deliberate bump planning is triggered.
- Users accept latest-upstream-only support policy.
- MVP fixture binaries can be redistributed under project licensing policy.
- Linux-first release can ship before cross-platform parity without violating product goals.
