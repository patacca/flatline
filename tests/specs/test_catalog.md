# Test Catalog

All tests below are the maintained contract catalog. Each item includes purpose,
fixtures, steps, assertions, oracle strategy, and determinism constraints.

## 1. Unit Tests

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| U-001 | Validate request schema rejects missing required fields | None | Build request objects with omitted required fields | Structured `invalid_argument` classification | Schema/error-category oracle | Error category stable; message text may vary |
| U-002 | Validate unknown compiler id handling | None | Provide compiler id not in enumerated set | Hard error, not fallback | Category + code oracle | Never silently substitute default compiler |
| U-006 | Validate analysis_budget defaulting and validation | None | Build request with omitted, object, and mapping-based `analysis_budget` values; also try unsupported keys and invalid limits | Omitted requests default to the pinned instruction cap, supported inputs coerce to `AnalysisBudget`, and unsupported keys/non-positive limits fail with `invalid_argument` | Value-normalization + error-category oracle | Default budget is deterministic; unsupported fields never silently degrade |
| U-007 | Validate session lifecycle semantics | None | Open/close a DecompilerSession via context manager and explicit close | Session closes deterministically and close() is idempotent | Lifecycle-state oracle | Closed state transitions are deterministic |
| U-008 | Validate closed-session rejection behavior | None | Close session, then call list/decompile methods | Calls fail with `invalid_argument` | Error-category oracle | Closed session never performs bridge operations |
| U-009 | Validate session-to-bridge delegation | None | Use a bridge test double and call list/decompile through session | Session forwards calls and request payload unchanged | Delegation oracle | Bridge call shape is stable |
| U-010 | Validate missing native-module fallback | None | Simulate native extension import failure when creating bridge session | Deterministic fallback bridge is selected | Runtime-selection oracle | Missing native extension does not crash import path |
| U-011 | Validate native bridge payload adaptation | None | Feed tuple/dict-shaped native payloads through bridge adapter | Public API receives `LanguageCompilerPair` and `DecompileResult` objects with expected values | Boundary-shape oracle | Bridge enforces stable Python value types at the boundary |
| U-012 | Validate native exception normalization | None | Simulate native exception during decompile | Returns structured `internal_error` result (no leaked native exception) and preserves filesystem paths in the public message for debuggability | Error-envelope oracle | Native bridge failures are deterministic and contract-shaped |
| U-013 | Validate runtime-data-backed language/compiler enumeration fallback | Synthetic runtime-data fixture (`.ldefs` + `.cspec`) | Enumerate pairs through bridge when native enumeration is unavailable/empty | Returns only valid `(language_id, compiler_spec)` pairs with existing backing spec files; native decompile validation uses the fallback pair set | Runtime-data enumeration oracle | Pair selection is deterministic and excludes entries with missing backing assets |
| U-014 | Validate startup rejection for missing runtime_data_dir | None | Start bridge session with a non-existent `runtime_data_dir` | Deterministic startup failure with structured `configuration_error` exception and the full failing path in the public message | Startup-path oracle | Missing runtime-data path never degrades to an empty/implicit default |
| U-015 | Validate tolerant malformed `.ldefs` behavior | Synthetic runtime-data fixture (valid + malformed `.ldefs`) | Enumerate pairs from a runtime-data root containing both valid and malformed `.ldefs` files | Returns valid pairs, emits one warning for skipped malformed files with full paths; raises deterministic `configuration_error` only when all `.ldefs` files are malformed | Runtime-data parse-tolerance oracle | Pair ordering deterministic; malformed-file observability stable |
| U-016 | Validate dependency-backed default runtime-data discovery | Installed `ghidra-sleigh` package or module double | Start a public session with omitted `runtime_data_dir`; also exercise explicit overrides | Auto-discovers `ghidra_sleigh.get_runtime_data_dir()` for the default path, preserves explicit overrides, and fails deterministically only when the dependency is unavailable | Default-runtime resolution oracle | Default runtime-data discovery is deterministic |
| U-017 | Validate release-compliance audit | Repo manifest + synthetic temp repo | Run the ADR-007 compliance audit against the committed repo and against a temp repo with a missing `NOTICE` file and missing dependency | Audit passes only when the required license/notice artifacts, vendored decompiler attribution, `ghidra-sleigh` dependency, and fixture redistribution note are present; missing notice files or missing dependency fail deterministically | Artifact-manifest oracle | Required redistribution artifacts and dependency references remain explicit across releases |
| U-018 | Validate default-install footprint measurement | Synthetic distribution manifests | Measure payload size from distribution file lists while excluding `__pycache__` | Footprint report totals are deterministic | Payload-size oracle | Measurement excludes interpreter-generated cache files |
| U-019 | Validate CI workflow smoke invariants | Committed `.github/workflows/ci.yml` | Parse the committed CI workflow definition | The test matrix still covers all supported Python versions (3.13/3.14), and a dedicated regression lane runs `tox -e py314 -- -m regression` against the installed wheel artifact | Workflow-smoke oracle | Critical CI lanes remain explicit without pinning incidental runner labels or step layout |
| U-022 | Validate built release artifact audit | Synthetic wheel/sdist archives + minimal repo `pyproject.toml` | Audit temp `dist/` artifacts for shipped notices plus version/dependency metadata | Built wheel and sdist pass only when both artifacts carry `LICENSE` / `NOTICE`, match the repo version, declare the `ghidra-sleigh` dependency, and keep `_flatline_native` inside every platform-specific wheel | Archive-manifest oracle | Artifact review stays deterministic and checks the built files, not just repo sources |
| U-025 | Validate release publish workflow structural invariants | Committed `.github/workflows/release.yml` | Parse the committed release workflow definition | Job dependency graph (dev-checks gates builds, validate depends on both, publish depends on validate, smoke depends on publish) is intact; all three platform families present in build and smoke matrices; publish routing routes manual dispatches to TestPyPI and releases to PyPI via trusted publishing; no `skip-existing`; no `ilammy/msvc-dev-cmd`; `twine check` and `artifacts.py` run in validate | Workflow-smoke oracle | Critical publish routing and job-graph structure stay explicit without pinning action versions, exact matrix entries, or build config literals |
| U-026 | Validate native-forced tox env and macOS contract-lane smoke invariants | Committed `pyproject.toml` + `.github/workflows/ci.yml` | Parse the native tox config and the macOS CI job | `py314-native` still forces `native_bridge=enabled`, and a dedicated macOS lane runs `tox -e py314-native -- -m "not regression"` without manual `CPPFLAGS` / `LDFLAGS` / `PKG_CONFIG_PATH` exports | Config-smoke oracle | Host-feasibility coverage stays explicit without pinning incidental workflow details |
| U-027 | Validate Windows contract-lane smoke invariants | Committed `.github/workflows/ci.yml` | Parse the committed CI workflow definition | A dedicated Windows lane runs `tox -e py314-native -- -m "not regression"` on a Windows runner without manual `CPPFLAGS` / `LDFLAGS` / `PKG_CONFIG_PATH` exports | Workflow-smoke oracle | Windows host-feasibility coverage stays explicit without pinning incidental workflow details |
| U-028 | Validate enriched-output bridge enforcement | None | Adapt native enriched-output payloads through the bridge; simulate a successful native response that omits the opt-in payload | The bridge serializes the opt-in flag and coerces pcode/varnode payloads to public value types, and successful opt-in requests fail hard if `enriched_output` is missing | Boundary-shape oracle | Opt-in enriched output never silently disappears on successful results |
| U-031 | Validate tail-padding request semantics | None | Build requests with default, custom, and disabled `tail_padding` values; serialize through the bridge; verify repeated custom bytes through the native load-image helper | Requests default to `tail_padding=b"\x00"`, normalize `None` / `b""` to disabled mode, preserve custom byte patterns in the native payload, and repeat custom padding bytes as needed | Value-normalization + payload-shape oracle | Tail padding stays caller-friendly by default while strict opt-out and custom patterns remain explicit and deterministic |

## 2. Contract Tests

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| C-001 | Public result schema stability | None | Call API stub and inspect result keys/types | Required keys/types unchanged | JSON-schema-like oracle | Additive fields allowed only |
| C-002 | Error taxonomy stability | None | Trigger representative error categories in harness stubs | Category names stable | Enum/name oracle | Categories cannot be removed in minor/patch |
| C-003 | Version reporting contract | None | Query version endpoint | Includes flatline + decompiler engine version | Field-presence oracle | Version fields always populated |
| C-004 | Structured result object schema stability | None | Call API stub and inspect FunctionInfo, FunctionPrototype, TypeInfo fields/types | Required fields/types unchanged; metatype strings are stable enum values | JSON-schema-like oracle | Additive fields allowed only; metatype mapping is contract-stable |
| C-005 | Session API surface stability | None | Inspect `DecompilerSession` for required methods | Lifecycle and operation methods are present and callable | API-surface oracle | Required methods remain stable |
| C-006 | Top-level operation function availability | None | Inspect module-level operation callables and signatures | `decompile_function` and `list_language_compilers` exist with stable parameters | Signature oracle | Parameter names remain stable |
| C-007 | Enriched-output schema stability | None | Inspect `DecompileRequest`, `DecompileResult`, and enriched companion dataclasses | The opt-in request flags plus `EnrichedOutput`, `PcodeOpInfo`, `VarnodeInfo`, and `VarnodeFlags` keep stable field names | JSON-schema-like oracle | Additive fields allowed only; enriched companion field names are contract-stable |

## 3. Integration Tests

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| I-001 | Known function decompilation success | `fx_add_elf64` | Decompile known entrypoint | Non-empty C output and success status; `function_info` populated with `is_complete` True | Normalized C text + status + structured-field oracle | Ignore whitespace/comments; preserve semantic tokens; structured field shapes stable |
| I-002 | Language/compiler enumeration validity | Runtime data fixture | Enumerate pairs and validate each pair assets exist | No invalid/missing-backed pairs returned | Asset-existence oracle | Returned pairs stable per fixture revision |
| I-003 | Sequential context isolation | `fx_add_elf64` | Run multiple sessions in sequence | No cross-session leakage in warnings/metadata | Session-isolation oracle | Stable results independent of previous session |
| I-004 | Startup and minimal load smoke path | `fx_runtime_data_min` | Start session, validate runtime data discovery, and execute minimal initialization/load flow | Startup succeeds with deterministic metadata and no leaked prior state | Startup-state oracle | Repeated startup/load remains deterministic under pinned upstream |
| I-005 | Known function produces populated FunctionInfo | `fx_add_elf64` | Decompile known function and inspect function_info | `function_info` is not None; `is_complete` True; `prototype` has expected parameter count and return type; `diagnostics` flags consistent | Structured-field oracle | Field shapes stable for same fixture and upstream pin |
| I-006 | Multi-ISA and multi-bitwidth known function decompilation | `fx_add_elf32`, `fx_add_arm64`, `fx_add_riscv64`, `fx_add_mips32` | Decompile known function for each additional priority ISA variant (x86_32, ARM64, RISC-V 64, MIPS32) | Non-empty C output and success status per ISA; `function_info` populated; no cross-ISA interference | Per-ISA normalized oracle | Each ISA evaluated independently; oracle baselines are ISA-specific |
| I-007 | Warning-only success with warning structure | `fx_warning_elf64` | Decompile function that produces warnings but succeeds | `c_code` non-empty; `error` is `None`; `function_info` populated; `warnings` non-empty with each item having `code` (str), `message` (str), `phase` (str) | Status + warning-structure oracle | Warning codes stable; message text informative only; phase values from defined set (`init`, `analyze`, `emit`) |
| I-008 | Opt-in enriched output supports use-def analysis | `fx_add_elf64` | Decompile the known add fixture with `include_enriched_output=True`, then walk the exported pcode/varnode graph | Default requests keep `enriched_output=None`; opt-in requests populate pcode ops and varnodes; a downstream walk from the `INT_ADD` result reaches a `RETURN` op through exported use-def edges | Use-def traversal oracle | Pcode-op IDs and varnode edges stay deterministic for the pinned fixture/upstream pair |
| I-009 | Exact function slices decompile without manual padding | `fx_add_elf64`, `fx_add_elf32`, `fx_add_arm64`, `fx_add_riscv64`, `fx_add_mips32` | Trim each fixture to its known function size and decompile with default request settings | Exact slices succeed without caller-added tail bytes and retain their normalized baseline output | Exact-slice normalized-output oracle | Default tail padding is deterministic and ISA-agnostic for the committed simple fixtures |
| I-010 | Tail-padding toggle preserves strict failure mode for exact slices with external calls | Inline AArch64 exact-slice sample with out-of-range call targets | Decompile with default tail padding, with a custom non-empty padding pattern, and with disabled padding | Default and custom-padding requests succeed with non-empty C output despite external call targets outside the supplied span; disabled padding returns structured `invalid_address` | Dual-path status oracle | Caller convenience stays default; strict opt-out and custom padding remain deterministic |

## 4. Regression Tests

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| R-001 | Preserve known simple function output behavior | `fx_add_elf64` | Decompile fixture function | Output matches normalized baseline; `function_info.prototype` shape and `varnode_count` stable | Canonical token stream + structured-data oracle | Stable across patch releases for same upstream pin |
| R-002 | Preserve jump-table output behavior | `fx_switch_elf64` | Decompile switch fixture | Output retains switch structure and expected case set; `function_info.jump_tables` switch address, target count, and target addresses stay stable | Structural AST/token + jump-table oracle | Case coverage, control structure, switch site, and jump table data stable |
| R-003 | Performance regression sentinel | `fx_add_elf64`, `fx_add_elf32`, `fx_add_arm64`, `fx_add_riscv64`, `fx_add_mips32`, `fx_switch_elf64` | Measure warm-session decompile latency under controlled harness per fixture | Fixture-specific warm p95 stays within the committed budget for each priority-ISA baseline plus the x86_64 switch fixture | Statistical budget oracle | Budgets tracked independently per fixture; fail on sustained p95 budget breach |
| R-004 | Multi-ISA regression baselines | `fx_add_elf32`, `fx_add_arm64`, `fx_add_riscv64`, `fx_add_mips32` | Decompile per-ISA fixture and compare to ISA-specific baseline | Output matches normalized baseline per ISA; structured data shapes stable | Per-ISA canonical token stream oracle | Baselines are ISA-specific; stable across patch releases for same upstream pin |

## 5. Negative Tests

| ID | Purpose | Fixtures | Steps | Assertions | Oracle strategy | Determinism constraints |
| --- | --- | --- | --- | --- | --- | --- |
| N-001 | Invalid address hard failure | `fx_add_elf64` | Request decompile at unmapped/invalid address | Structured `invalid_address` error; `function_info` is `None`; `c_code` is `None` | Category/status oracle | Must not downgrade to warning-only success |
| N-002 | Unsupported language id failure | `fx_add_elf64` | Request unknown language id | Structured `unsupported_target` error; `function_info` is `None`; `c_code` is `None` | Category/status oracle | No fallback language substitution |
| N-003 | Unsupported compiler for valid language | `fx_add_elf64` | Request invalid compiler for known language | Structured `unsupported_target` error; `function_info` is `None`; `c_code` is `None` | Category/status oracle | No implicit compiler fallback |
| N-004 | Corrupt/missing runtime data directory | runtime data fixture | Start session with broken data dir | Deterministic startup failure | Startup error oracle | Error category stable across runs |
| N-005 | Invalid memory image input | `fx_invalid_memory` (empty/zero-length memory image) | Construct a request with empty or zero-length memory image | `InvalidArgumentError` with category `invalid_argument` is raised before decompile | Exception-category oracle | Error category stable; message text may vary |

## 6. Contract-Clause-to-Test Traceability

| Spec clause (specs.md) | Contract requirement | Test IDs |
| --- | --- | --- |
| §3.2 `list_language_compilers()` | Enumerate valid pairs from runtime data | I-002, U-013, U-015, U-016 |
| §3.2 `decompile_function(request)` | Decompile one function; no native exceptions leak | I-001, I-005, I-006, U-009, U-012 |
| §3.1 `DecompilerSession` lifecycle | Long-lived session owns lifecycle of one bridge/native context | U-007, U-008, U-016, C-005 |
| §3.2 top-level operation wrappers | Public operation callables are exposed from package root | C-006 |
| §3.2 `get_version_info()` | Report flatline + decompiler version metadata | C-003 |
| §3.3 DecompileRequest required fields | Missing fields → `invalid_argument` | U-001 |
| §3.3 DecompileRequest `compiler_spec` validation | Unknown compiler → hard error | U-002, N-003 |
| §3.3 DecompileRequest `runtime_data_dir` | Omission uses dependency-backed default; explicit values remain overrides | U-016 |
| §3.3 DecompileRequest `analysis_budget` | Omission resolves to the pinned default budget; supported inputs normalize deterministically | U-006, U-011 |
| §3.3 DecompileRequest `tail_padding` | Exact slices succeed by default while strict tail-boundary failures and custom patterns remain opt-in | U-031, I-009, I-010 |
| §3.3 DecompileRequest `include_enriched_output` | Opt-in enriched output is explicit and defaults to `False` | U-028, C-007, I-001, I-008 |
| §3.3 `AnalysisBudget` | `max_instructions` is the stable budget field for P2 | U-006, C-004 |
| §3.3 DecompileResult metadata keys | Required top-level keys always present | C-001 |
| §3.3 DecompileResult `enriched_output` | Companion payload is absent by default and present on successful opt-in requests | U-028, C-001, C-007, I-001, I-008 |
| §3.3 FunctionInfo fields + types | Required fields present, correct types, diagnostics consistent | I-005, C-004 |
| §3.3 FunctionPrototype fields | Calling convention, parameters, return type, flags | C-004, I-005 |
| §3.3 ParameterInfo, VariableInfo, TypeInfo | Stable required fields and metatype strings | C-004 |
| §3.3 CallSiteInfo, JumpTableInfo | Call/jump-table structured data | R-002, I-005 |
| §3.3 DiagnosticFlags | Aggregated boolean flags | I-005 |
| §3.3 LanguageCompilerPair | language_id + compiler_spec fields | I-002 |
| §3.3 EnrichedOutput, PcodeOpInfo, VarnodeInfo, VarnodeFlags | Frozen companion schema and graph edges remain stable | U-028, C-007, I-008 |
| §3.3 WarningItem structure | code, message, phase fields | I-007 |
| §3.3 VersionInfo fields | flatline_version, decompiler_version | C-003 |
| §3.4 Unknown compiler → hard error | No implicit fallback | U-002, N-003 |
| §3.4 Unknown language → hard error | No fallback substitution | N-002 |
| §3.4 Invalid address → hard error | Not warning-only | N-001 |
| §3.4 Empty memory → hard error | `invalid_argument` | U-001, N-005 |
| §3.4 Invalid `analysis_budget` input | Unsupported fields/non-positive limits are `invalid_argument` | U-006 |
| §3.4 Missing default runtime dependency | Missing dependency is a `configuration_error` | U-016 |
| §3.4 Diagnostic path visibility policy | Full filesystem paths may appear in public diagnostics; raw memory bytes never emitted | U-012, U-014, U-015 |
| §3.4 Error categories stable | Category names invariant across minor/patch | C-002 |
| §3.4 Warning-only → successful status | c_code valid, error None, function_info populated | I-007 |
| §3.4 Error set → function_info=None, c_code=None | Error model invariant | N-001, N-002, N-003, N-005 |
| §3.4 Success → function_info populated | Never None on success | I-005 |
| §3.4 Opt-in enriched output is all-or-nothing | Successful opt-in requests never silently drop the companion payload | U-028, I-008 |
| §3.5 Additive fields only in minor | Schema stability | C-001, C-004 |
| §6 Contract-test strategy (build/workflow config tests) | Workflow/config tests stay smoke-level and assert only contract-critical CI behavior | U-019, U-025, U-026, U-027 |
| §7 Packaging and compliance | Release artifacts include notices and attribution; ADR-007 audit passes; built wheel/sdist metadata stay auditable; repo-only dev tooling stays outside shipped payloads; default-install footprint stays measured/documented with an explicit size-policy note | U-017, U-018, U-022 |
| §7 Public artifact review gate | The final human artifact review uses a source-controlled checklist tied to deterministic readiness evidence | U-022 |
| §7 Release automation | GitHub Actions release automation builds and audits distributions, publishes GitHub releases to PyPI, routes manual dispatches to TestPyPI, rejects duplicate manual-dispatch versions, keeps the locked wheel matrix explicit, and smoke-tests the published index artifacts on the Tier-1 matrix | U-025 |
| §7 Cross-platform feasibility policy | Dedicated macOS and Windows feasibility lanes force native builds and run the installed-wheel non-regression contract matrix before support notes can change | U-026, U-027 |
| §7 Session isolation | No cross-session leakage | I-003 |
| §7 Startup determinism | Repeatable startup under pinned upstream | I-004 |
| §6 Bridge contract layer | Bridge boundary translates native payloads into stable Python contract objects; native exceptions normalized to structured results | U-010, U-011, U-012 |
| §7 Performance budget | p95 latency within threshold and committed budgets are enforced by the pinned CI regression lane | R-003, U-019 |
| Regression: simple function | Normalized output stable | R-001 |
| Regression: jump-table | Switch structure + jump table data stable | R-002 |
| Regression: multi-ISA | Per-ISA baselines stable | R-004 |
| Runtime data dir broken | Deterministic startup failure | N-004, U-014 |

## 7. Mapping to Source Documents

- Decompiler lifecycle and required callable behavior: `notes/api/decompiler_inventory.md`.
- Post-decompile structured data (FunctionInfo, prototype, symbols, types): `notes/api/decompiler_inventory.md` §§1-7.
- Public contract, runtime-data policy, and error semantics: `docs/specs.md`.
- Structured result object definitions: `docs/specs.md` §3.3.
- Enriched pcode/varnode companion contract and extraction invariants: `docs/specs.md` §3.3 and `notes/api/decompiler_inventory.md` §3.
- Diagnostic path-visibility policy and public warning/error surfaces: `docs/specs.md` §3.4 and §7.
- Initial public release notes and support messaging: `docs/release_notes.md`.
- Redistribution/compliance manifest and release audit: `docs/compliance.md`.
- Milestones and release gates for deterministic behavior: `docs/roadmap.md`.
- Startup/minimal-load, known-function, invalid-address, and jump-table expectations are consolidated into this catalog from baseline experiment findings.
- Error category definitions and stability rules: `docs/specs.md` §3.4.
