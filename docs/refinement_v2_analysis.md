# Refinement v2 Analysis

## Summary

- **Structured result objects are the primary gap**: `DecompileResult` exposes only C text; the decompiler inventory documents rich post-decompile data (function metadata, prototype, symbols, types, diagnostics, call sites, jump tables) not surfaced in the Python API contract.
- **P0 exit criteria must include structured object definitions**: roadmap P0/M0 gates do not require structured result model lock; `refine_plan.md` Task 5 flags this as P0-mandatory.
- **Fixture coverage is x86_64-only** despite multi-ISA being a day-one requirement: `specs.md` §8.1, `roadmap.md` M1, and `fixtures.md` are misaligned.
- **AGENTS.md test count is wrong**: claims 21 tests; catalog has 19 (→24 after vNext additions).
- **`metadata["diagnostics"]` is undefined**: listed as a stable key in `DecompileResult` but contents never specified.
- **Warning code taxonomy is deferred but needed for testability**: `WarningItem.code` declared stable but no codes enumerated.
- **`analysis_budget` shape is undefined**: listed as optional request field with no structure.
- **All existing deliverables are present and structurally sound**; gaps are additive rather than structural.

## Deliverables Gap Audit

| Deliverable | Baseline requirement | Status | Evidence | Minimal fix |
| --- | --- | --- | --- | --- |
| `specs.md` §1 Goals/non-goals | planning.md D1 | Present | §1 | — |
| `specs.md` §2 Personas/use-cases | planning.md D1 | Present | §2 | — |
| `specs.md` §3 Public API contract | planning.md D1 | **Partial** | §3.3: `DecompileResult` has `c_code`+metadata only; no structured objects | Add `FunctionInfo` et al. to §3.3 |
| `specs.md` §3.3 `metadata["diagnostics"]` | planning.md D1 | **Unclear** | Listed as stable key but undefined | Supersede with typed `DiagnosticFlags` object |
| `specs.md` §3.3 `analysis_budget` | planning.md D1 | **Unclear** | Optional field; no shape | Define minimal shape or defer to ADR-005 |
| `specs.md` §3 Warning codes | planning.md D1 | **Missing** | `WarningItem.code` stable; none enumerated | Defer to P1 (ADR-003 dependency) with note |
| `specs.md` §4 Decompiler contract | planning.md D1 | Present | §4 | — |
| `specs.md` §5 Architecture decisions | planning.md D1 | Present | §5, ADR-001 decided | — |
| `specs.md` §6 Stability strategy | planning.md D1 | Present | §6 | — |
| `specs.md` §7 Cross-cutting | planning.md D1 | Present | §7 | — |
| `specs.md` §8 MVP vs Next | planning.md D1 | Present | §8 | — |
| `specs.md` §§9-10 Open Q/assumptions | planning.md D1 | Present | §§9-10 | — |
| `roadmap.md` phases/milestones | planning.md D2 | Present | §§1-2 | Update P0/M0 exit to include structured objects |
| `roadmap.md` risk register | planning.md D2 | Present | §3 | — |
| `roadmap.md` ADR backlog | planning.md D2 | Present | §4 | — |
| `roadmap.md` release/versioning | planning.md D2 | Present | §5 | — |
| `test_catalog.md` | planning.md D3 | Present (19 tests) | test_catalog.md | Add structured-object + multi-ISA tests |
| `fixtures.md` | planning.md D3 | **Partial** | x86_64-only fixtures | Add per-ISA fixture entries |
| `tests/fixtures/README.md` | planning.md D3 | **Partial** | x86_64-only | Add per-ISA placeholders |
| pytest skeletons | planning.md D3 | Present (5 files) | tests/\*/ | Add new test skeletons |
| `AGENTS.md` accuracy | Internal consistency | **Incorrect** | Says "21 test definitions"; actual=19 → 24 | Fix count and add structured objects |

## Inconsistencies & Grey Areas

### Hard Conflicts

**HC-1: Structured result objects missing from API contract (P0 blocker)**
- Evidence: `specs.md` §3.3 defines `DecompileResult` with `c_code: str | None` only. `decompiler_inventory.md` §§1-7 documents `Funcdata`, `FuncProto`, `ScopeLocal`, `TypeFactory`, `FuncCallSpecs`, `JumpTable`, diagnostics flags — all extractable post-decompile.
- Impact: `refine_plan.md` Task 5 requires structured objects as P0. Without them, P0 exit criteria are unmet.
- Fix: Add `FunctionInfo` and related objects to `specs.md` §3.3; update P0/M0 exit criteria in `roadmap.md`.

**HC-2: Fixture set is x86_64-only vs multi-ISA requirement**
- Evidence: `fixtures.md` §1 lists only `fx_add_elf64`, `fx_switch_elf64` (x86_64). `roadmap.md` M1 requires "per-ISA fixture manifest covering all priority ISAs". `specs.md` §8.1 says "Priority ISAs with full fixture coverage."
- Impact: M1 exit gate cannot be met without per-ISA fixtures.
- Fix: Add fixture entries for ARM64, RISC-V 64, MIPS32 to `fixtures.md` and `tests/fixtures/README.md`.

**HC-3: AGENTS.md test count wrong**
- Evidence: `AGENTS.md` line 33 says "21 test definitions across 5 categories". `test_catalog.md` has 4+3+4+3+5 = 19.
- Fix: Update count to 24 after vNext additions.

### Soft Inconsistencies

**SI-1: `metadata["diagnostics"]` listed but undefined**
- Evidence: `specs.md` lines 105-109 list `metadata["diagnostics"]` as a stable key; no definition of contents.
- Fix: Supersede with typed `FunctionInfo.diagnostics` object; keep metadata key for backward compat.

**SI-2: N-002/N-003 error category mapping implicit**
- Evidence: `test_catalog.md` N-002 and N-003 both assert `unsupported_target`. `specs.md` §3.4 says "Unknown compiler ids are hard errors" without specifying the category.
- Fix: Add explicit category mappings in `specs.md` §3.4.

**SI-3: preplanning.md contains obsoleted API direction**
- Evidence: `preplanning.md` §6 shows `binary_path` parameter; ADR-001 decided Option A. Already marked as completed discovery doc.
- Fix: No change needed.

### Omissions

**OM-1: Warning code taxonomy not enumerated**
- Evidence: `specs.md` §3.3 declares `WarningItem.code` as stable; none defined. Upstream uses free-text `Comment::warning`/`warningheader`.
- Fix: Acknowledge as P1/ADR-003 scope with note in `specs.md`.

**OM-2: `analysis_budget` object shape undefined**
- Evidence: `specs.md` §3.3 lists optional field; no structure. Inventory confirms `max_instructions` (uint4, default 100000) as main mechanism; no wall-clock timeout in decompiler.
- Fix: Define minimal shape referencing ADR-005.

**OM-3: Session lifecycle not covered by test catalog**
- Evidence: `specs.md` §3.1 defines `DecompilerSession` lifecycle. No test validates create→use→destroy. I-003 tests isolation but not lifecycle.
- Fix: Not added in this iteration (lifecycle is implicitly tested by all integration tests); track as backlog.

## Architecture/Strategy Review

### Confirmed Prior Decisions

| Decision | Evidence | Assessment |
| --- | --- | --- |
| ADR-001: Option A (memory + arch + function-level) | `specs.md` §5.5 | Sound. Verified: `LoadImageXml` stores `map<Address, vector<uint1>>` and serves reads from memory (`loadimage_xml.hh`). |
| Three-layer adapter: Public → Bridge → Upstream | `specs.md` §6 | Sound. Clean isolation of stability tiers. |
| Latest-upstream-only version policy | `specs.md` §3.5 | Sound. Simplifies CI/packaging. |
| Multi-ISA target from day one | `roadmap.md` §0, `specs.md` §1 | Sound but **fixture gap** (HC-2). Architecture supports it; test infrastructure doesn't yet. |
| Normalized textual oracle for determinism | `specs.md` §7, `fixtures.md` §2 | Sound. Token/structure-aware comparison avoids false positives. |
| Session-scoped Architecture instances | `specs.md` §3.1 | Sound. Verified: `Architecture::init()` fully initializes owned subsystems. |
| Request-isolated decompilation | `specs.md` §4.2 | Sound. Verified: each `Funcdata` is independent; decompiling another function does NOT invalidate prior results (`decompiler_inventory.md` §Post-Decompilation Contract). |

### Grey Areas and Unstated Assumptions

**GA-1: Structured data extraction path (encode vs field-by-field)**
- Inventory documents `Funcdata::encode(Encoder&, uint8, bool)` producing XML-encoded output. Alternative: extract fields individually via C++ accessors.
- Recommendation: Field-by-field extraction for MVP. Avoids XML parsing overhead, allows explicit field selection, keeps bridge surface minimal. Add note to `specs.md` §4.4.

**GA-2: `LoadImage::getReadonly()` for section metadata**
- `specs.md` §5.4.3 mentions readonly section info. `DecompileRequest` has no field for it.
- Recommendation: Not blocking for MVP. Track in §8.3 (already listed as Next-scope).

**GA-3: GIL and thread-safety interaction**
- Under CPython GIL, concurrent Python calls to same session are serialized. Free-threaded Python (3.13t) changes this.
- Recommendation: Add note that concurrency model assumes GIL or caller-provided serialization.

**GA-4: `analysis_budget` maps to `max_instructions` only**
- Inventory confirms: `Architecture::max_instructions` (uint4, default 100000). No wall-clock timeout in decompiler; external cancellation required.
- Recommendation: Define minimal shape wrapping `max_instructions`; defer full API to ADR-005.

## Python Interface Expansion

### Design Principles

- All objects are pure Python value types (frozen dataclasses).
- Data is extracted at the bridge boundary; no native references survive.
- All fields trace to inventory methods marked `required` in MVP relevance.
- New objects are additive; existing fields unchanged.

### Updated `DecompileResult`

```
c_code: str | None                    # existing
function_info: FunctionInfo | None    # NEW — populated on success, None on error
warnings: list[WarningItem]           # existing
error: ErrorItem | None               # existing
metadata: dict[str, Any]              # existing, stable keys preserved
```

### Object Definitions

#### `FunctionInfo`

| Field | Type | Source (inventory) | Consumer need |
| --- | --- | --- | --- |
| `name` | `str` | `Funcdata::getName()` §1 | Display, logging |
| `entry_address` | `int` | `Funcdata::getAddress()` §1 | Cross-referencing |
| `size` | `int` | `Funcdata::getSize()` §1 | Coverage metrics |
| `is_complete` | `bool` | `Funcdata::isProcComplete()` §1/§7 | Quality gating |
| `prototype` | `FunctionPrototype` | `Funcdata::getFuncProto()` §1 | Automation |
| `local_variables` | `list[VariableInfo]` | `ScopeLocal` iteration §4 | Symbol analysis |
| `call_sites` | `list[CallSiteInfo]` | `FuncCallSpecs` §6 | Call-graph |
| `jump_tables` | `list[JumpTableInfo]` | `JumpTable` §6 | Switch analysis |
| `diagnostics` | `DiagnosticFlags` | Funcdata flag accessors §7 | Quality assessment |
| `varnode_count` | `int` | `Funcdata::numVarnodes()` §1 | Complexity metric |

#### `FunctionPrototype`

| Field | Type | Source | Consumer need |
| --- | --- | --- | --- |
| `calling_convention` | `str \| None` | `FuncProto::getModelName()` | ABI analysis |
| `parameters` | `list[ParameterInfo]` | `Scope::getCategorySize(0)` + `getCategorySymbol(0,i)` §4 | Signature |
| `return_type` | `TypeInfo` | FuncProto return type | Signature |
| `is_noreturn` | `bool` | `FuncProto::isNoReturn()` | Control flow |
| `has_this_pointer` | `bool` | `FuncProto::hasThisPointer()` | OOP detection |
| `has_input_errors` | `bool` | `FuncProto::hasInputErrors()` §7 | Quality gate |
| `has_output_errors` | `bool` | `FuncProto::hasOutputErrors()` §7 | Quality gate |

#### `ParameterInfo`

| Field | Type | Source | Consumer need |
| --- | --- | --- | --- |
| `name` | `str` | `Symbol::getName()` §4 | Display |
| `type` | `TypeInfo` | `Symbol::getType()` §4/§5 | Type analysis |
| `index` | `int` | Category index from scope | Ordering |
| `storage` | `StorageInfo \| None` | `SymbolEntry::getAddr()`, `getSize()` §4 | Register/stack |

#### `VariableInfo`

| Field | Type | Source | Consumer need |
| --- | --- | --- | --- |
| `name` | `str` | `Symbol::getName()` §4 | Display |
| `type` | `TypeInfo` | `Symbol::getType()` §4/§5 | Type analysis |
| `storage` | `StorageInfo \| None` | `SymbolEntry` §4 | Location tracking |

#### `TypeInfo`

| Field | Type | Source | Consumer need |
| --- | --- | --- | --- |
| `name` | `str` | `Datatype::getName()` §5 | Display |
| `size` | `int` | `Datatype::getSize()` §5 | Layout analysis |
| `metatype` | `str` | `Datatype::getMetatype()` → stable string §5 | Classification |

Metatype mapping: `TYPE_VOID`→`"void"`, `TYPE_BOOL`→`"bool"`, `TYPE_INT`→`"int"`, `TYPE_UINT`→`"uint"`, `TYPE_FLOAT`→`"float"`, `TYPE_PTR`→`"pointer"`, `TYPE_ARRAY`→`"array"`, `TYPE_STRUCT`→`"struct"`, `TYPE_UNION`→`"union"`, `TYPE_CODE`→`"code"`, `TYPE_ENUM_INT`/`TYPE_ENUM_UINT`→`"enum"`, `TYPE_UNKNOWN`→`"unknown"`.

#### `CallSiteInfo`

| Field | Type | Source | Consumer need |
| --- | --- | --- | --- |
| `instruction_address` | `int` | `FuncCallSpecs::getOp()->getAddr()` §6 | Location |
| `target_address` | `int \| None` | `FuncCallSpecs::getEntryAddress()` §6 | Call graph |

#### `JumpTableInfo`

| Field | Type | Source | Consumer need |
| --- | --- | --- | --- |
| `switch_address` | `int` | JumpTable op address §6 | Location |
| `target_count` | `int` | Resolved target count §6 | Switch analysis |
| `target_addresses` | `list[int]` | Resolved targets §6 | Case analysis |

#### `DiagnosticFlags`

| Field | Type | Source | Consumer need |
| --- | --- | --- | --- |
| `is_complete` | `bool` | `isProcComplete()` §7 | Quality gate |
| `has_unreachable_blocks` | `bool` | `hasUnreachableBlocks()` §7 | Quality info |
| `has_unimplemented` | `bool` | `hasUnimplemented()` §7 | Quality info |
| `has_bad_data` | `bool` | `hasBadData()` §7 | Quality info |
| `has_no_code` | `bool` | `hasNoCode()` §7 | Error diagnosis |

#### `StorageInfo`

| Field | Type | Source | Consumer need |
| --- | --- | --- | --- |
| `space` | `str` | `AddrSpace::getName()` §6 | Location class |
| `offset` | `int` | Byte offset §6 | Address |
| `size` | `int` | Byte size §6 | Extent |

### Error Model

- `error` set → `function_info` is `None`, `c_code` is `None`.
- Decompilation succeeds → `function_info` populated (never `None`), `c_code` set.
- Recovery failures within `function_info` signaled via `prototype.has_input_errors`/`has_output_errors` and `diagnostics` flags, not by making individual fields `None`.

### Ownership/Lifetime

- All structured objects are value-copied at bridge boundary into frozen Python dataclasses.
- No native pointers or references survive past bridge call.
- Bridge extracts structured data before releasing native `Funcdata`/`Architecture`.

### Compatibility

- Existing fields (`c_code`, `warnings`, `error`, `metadata`) unchanged.
- `function_info` is additive (`None` when decompilation fails).
- `metadata["diagnostics"]` superseded by `function_info.diagnostics` but kept for backward compatibility.
- SemVer: minor release (additive, backward-compatible).

### Tests/Docs Impact

New tests (5):
- **C-004**: Structured result object schema stability (`FunctionInfo`, `FunctionPrototype`, `TypeInfo`).
- **U-005**: `FunctionInfo` fields populated from adapter stub data.
- **I-005**: Known function produces populated `FunctionInfo` with expected prototype shape.
- **I-006**: Multi-ISA known function decompilation (parameterized: ARM64, RISC-V 64, MIPS32).
- **R-004**: Multi-ISA regression baselines (parameterized: ARM64, RISC-V 64, MIPS32).

Updated existing tests:
- **I-001**: Add assertion that `function_info` is not None and `function_info.is_complete` is True.
- **R-001/R-002**: Add structured data to regression baselines.

## Proposed Updates

Patch-style edits by file/section follow. Applied directly to repo files.

### `docs/specs.md`

1. **§3.1 Concepts table**: Add new structured objects (`FunctionInfo`, `FunctionPrototype`, etc.).
2. **§3.3 Data Model**: Add `function_info` field to `DecompileResult`; add full definitions of all structured objects; define `metadata["diagnostics"]` as superseded by typed object.
3. **§3.4 Error Model**: Add explicit error category mappings for invalid language/compiler.
4. **§4.4 Mapping**: Add note about field-by-field extraction strategy.
5. **§9 Open Questions**: Remove resolved items; add new ones for structured objects.

### `docs/roadmap.md`

1. **§1 Phase table**: Update P0 exit criteria to include structured object definitions.
2. **§2 M0 gate**: Add structured result model to exit checks.

### `tests/specs/test_catalog.md`

1. Add U-005, C-004, I-005, I-006, R-004 test definitions.
2. Update I-001, R-001, R-002 with structured result assertions.

### `tests/specs/fixtures.md`

1. Add multi-ISA fixture entries: `fx_add_arm64`, `fx_add_riscv64`, `fx_add_mips32`.

### `tests/fixtures/README.md`

1. Add multi-ISA fixture placeholders.

### `tests/unit/test_public_contract_spec.py`

1. Add `test_u005_function_info_fields_from_stub` skeleton.

### `tests/contract/test_api_contract_spec.py`

1. Add `test_c004_structured_result_schema_stability` skeleton.

### `tests/integration/test_integration_spec.py`

1. Add `test_i005_known_function_produces_function_info` and `test_i006_multi_isa_known_function` skeletons.

### `tests/regression/test_regression_spec.py`

1. Add `test_r004_multi_isa_regression_baselines` skeleton.

### `AGENTS.md`

1. Fix test count (→24).
2. Add structured objects to key data models.

## Questions

1. **Metatype granularity**: Should `TypeInfo` expose sub-type details (e.g., struct fields, array element type, pointer target) in MVP, or is the flat `name`/`size`/`metatype` triple sufficient? Exposing sub-types adds recursion and complexity. Affects: `TypeInfo` definition, test count, bridge surface.

2. **Call-site callee name**: Should `CallSiteInfo` include a `callee_name: str | None` field when the target function is known in the symbol database? This is useful but requires cross-scope lookup. Affects: `CallSiteInfo` definition, bridge complexity.

3. **JumpTable completeness**: The decompiler's `JumpTable` recovery can be partial. Should `JumpTableInfo` include an `is_complete: bool` flag? Affects: `JumpTableInfo` definition, test assertions.

4. **Per-ISA fixture variant selection**: For ARM, should the fixture use AArch64 or ARM32 (or both)? For MIPS, MIPS32 or MIPS64? The current proposal uses ARM64/RISC-V64/MIPS32 to cover diverse bitwidths. Affects: fixture generation, regression baselines.
