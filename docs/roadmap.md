# flatline Roadmap

## 0. Baseline and Policy

Vendored decompiler source: `third_party/ghidra` git submodule.

Product policy:
- Linux host MVP first; multi-ISA target from day one.
- Fixture-backed confidence targets for MVP: x86 (32/64), ARM64, RISC-V 64, and MIPS32.
- Default runtime data exposes all bundled Ghidra decompiler-supported ISAs; non-fixture-backed ISAs and variants remain best-effort and must be documented as such in public support notes.
- Cross-platform host expansion (macOS/Windows) after Linux contract stability gates.
- One upstream decompiler version supported at a time (latest only).

## 1. Phases and Milestones

| Phase | Focus | Entry criteria | Exit criteria |
| --- | --- | --- | --- |
| P0 | Spec lock | Inventory, MVP contract, experiment notes exist | `docs/specs.md` and this roadmap accepted; open questions tracked; structured result object definitions (fields, types, error model, ownership/lifetime) locked in `specs.md` §3.3 |
| P1 | Contract test harness | P0 complete | Definitions-only test suites and oracle strategy committed |
| P2 | Linux MVP delivery | P1 complete | Linux host function decompilation contract satisfied for the fixture-backed confidence matrix (x86_64, x86_32, ARM64, RISC-V 64, MIPS32) and enumeration/error contract for all bundled ISAs |
| P3 | Packaging + compliance hardening | P2 complete | Redistribution/compliance policy finalized; license notices/compliance checks pass; default-install support messaging matches the actual product UX |
| P4 | Stabilization and regression control | P3 complete | Determinism/perf regression gates enforced in CI for pinned matrix |
| P5 | Initial public release | P4 complete | Release notes include contract guarantees, support tiers / known variant limits, and upgrade policy |
| P6 | Cross-platform expansion | P5 complete | macOS and Windows feasibility validated with equivalent contract coverage |
| P7 | Enriched structured output | P5 complete | Pcode ops and varnode graphs exposed as frozen Python types; at least one downstream use case (similarity, diffing, or data flow) validated end-to-end |

## 2. Detailed Milestone Gates

### M0: Planning closure
- Inputs:
  - `docs/specs.md`
  - `docs/roadmap.md`
  - `tests/specs/*`
- Exit checks:
  - Decision points resolved or explicitly deferred with owner/date.
  - Structured result object definitions (`FunctionInfo`, `FunctionPrototype`, `ParameterInfo`, `VariableInfo`, `TypeInfo`, `CallSiteInfo`, `JumpTableInfo`, `DiagnosticFlags`, `StorageInfo`, `LanguageCompilerPair`, `WarningItem`, `ErrorItem`, `VersionInfo`) with fields, types, error model, and ownership/lifetime locked in `specs.md` §3.3.

### M1: Contract harness ready
- Inputs:
- test catalog with unit/integration/regression/negative/contract coverage
- fixture strategy and normalization/oracle rules
- per-ISA fixture manifest covering the committed fixture-backed variants (x86_64, x86_32, ARM64, RISC-V 64, MIPS32)
- Exit checks:
- every API contract clause maps to at least one test ID
- unsupported/invalid flows have explicit negative tests
- each committed fixture-backed variant has at least one known-function fixture and one regression baseline

### M2: Linux MVP behavior complete
- Inputs:
- session startup, pair enumeration, single-function decompile behavior
- fixture-backed confidence-matrix results (x86_64, x86_32, ARM64, RISC-V 64, MIPS32) and enumeration coverage for all bundled ISAs
- Exit checks:
- known-function fixtures for each committed confidence variant and the committed jump-table fixture produce deterministic pass under oracle rules
- invalid-address, unsupported-language/compiler produce structured failures (ISA-independent)
- bridge ownership and lifetime contract verified by contract/integration definitions
- `list_language_compilers()` returns valid pairs spanning the fixture-backed confidence matrix and any additionally bundled ISAs
- per-ISA performance baselines captured for the fixture-backed confidence matrix, with the x86_64 jump-table fixture tracked separately

### M3: Packaging and compliance complete
- Inputs:
- legal artifact manifest and redistribution/compliance checklist (`docs/compliance.md`, `NOTICE`, `python tools/compliance.py`)
- multi-ISA runtime asset inventory (language definitions, Sleigh specs, compiler specs for all bundled ISAs)
- Exit checks:
- package installs without external Ghidra checkout
- license/compliance review checklist signed off
- default install footprint measured with `python tools/footprint.py` and documented in `docs/footprint.md` against product policy, with any required tradeoffs made explicitly rather than by silent default ISA pruning
- repo-only release tools under `tools/flatline_dev` and `tools/*.py` excluded from wheels and sdists; only the public runtime modules and optional native extension ship in distribution artifacts

### M4: Release readiness
- Inputs:
- changelog, upgrade notes, regression/perf data, support-tier notes
- `docs/release_notes.md` summarizing contract guarantees, support tiers /
  known-variant limits, and upgrade policy for the first public release
- `docs/release_review.md` capturing the public artifact-review checklist and
  the explicit external approval hold point for final human sign-off
- `docs/release_workflow.md` capturing the initial public release procedure and
  the `0.1.0` SemVer recommendation that finalized the prior `0.1.0.dev0`
  branch state
- built-artifact audit evidence from `python tools/artifacts.py`
- Exit checks:
- SemVer classification approved
- contract tests green on release matrix
- release-facing support matrix and known-variant limits are ready
- public artifact-review criteria are source-controlled and tied to the
  deterministic readiness evidence, while final human approval is reported
  outside the repo
- built wheel and sdist pass artifact audit for version/dependency metadata and
  shipped `LICENSE` / `NOTICE`
- dev-only release tools are not present in the built wheel or sdist (audit tools are repo-level commands run from editable installs)

Note: M4 covers the exit criteria of both P4 (Stabilization and regression control)
and P5 (Initial public release). A separate M4b gate may be introduced if stabilization
and release activities require distinct checkpoints.

### M5: Cross-platform readiness (post-MVP)
- Inputs:
- platform feasibility findings for macOS/Windows, recorded in `docs/host_feasibility.md`
- pinned macOS smoke/build CI evidence that forces the native bridge path
  before host-promotion work expands to the full contract matrix
- Exit checks:
- `docs/host_feasibility.md` records the current platform audit, the ADR-008 host order, and the equivalent contract-coverage bar for adding a supported host
- macOS native build/install and the existing contract matrix are validated before Windows becomes the active expansion target
- platform-specific risk register entries are closed or accepted

### M6: Enriched output readiness (post-MVP)
- Inputs:
- ADR-012 design decision on pcode/varnode representation and extraction strategy
- frozen Python types for pcode operations and varnode data flow graphs
- Exit checks:
- pcode ops and varnode graphs extracted at bridge boundary as frozen value types, no live C++ handles cross ABI
- at least one real-usage scenario (BSim-style similarity, binary diffing, or data flow analysis) demonstrated end-to-end
- enriched output fields integrated into `FunctionInfo` or a dedicated companion type under the existing `DecompileResult` contract

## 3. Risk Register

| Risk | Likelihood | Impact | Mitigation | Trigger/monitor |
| --- | --- | --- | --- | --- |
| Upstream callable-surface drift breaks bridge assumptions | High | High | Pin upstream per release; mandatory inventory diff + contract rerun before bump | Any upstream bump proposal |
| Deterministic output drift across environments | Medium | High | Use normalized oracles and stable warning/error codes; pin fixture matrix | CI output diff on pinned fixtures |
| Runtime package size grows beyond acceptable limits | Medium-High | Medium | Measure footprint against the one-package default UX, document the result, and require an explicit product/compliance decision before changing the default asset profile; lighter custom runtime-data roots remain an override path | Artifact size threshold breach |
| ISA-specific Sleigh spec immaturity degrades decompilation quality | Medium | Medium | The committed confidence variants are validated by fixture matrix; non-fixture-backed ISAs remain best-effort with enumeration/error coverage only | Fixture failure or user-reported quality regression per ISA |
| ISA variant edge cases (Thumb, microMIPS, RV extensions) cause unexpected failures | Medium | Medium | Restrict MVP fixtures to common ISA variants; document known variant limitations | Negative test failures on variant-specific fixtures |
| Users mistake bundled-ISA enumeration for fixture-backed support guarantees | Medium | High | Publish support tiers and known-variant limits in release notes/docs; keep top-level scope wording aligned with the committed confidence matrix | Confusion in issue reports or support requests from best-effort targets |
| ABI/bridge stability regressions | Medium | High | Strict contract tests and explicit stability tiers | Failing contract suite |
| License/redistribution non-compliance | Low | High | Compliance checklist, root NOTICE bundling, `python tools/compliance.py`, source-attribution audit | Release candidate review |
| CI/toolchain variance causes flaky results | Medium | Medium | Stable build/test matrix and deterministic fixture harness | Flake rate trend in CI |
| Windows portability blockers discovered late | Medium | High | ADR-008 resolves the host order to macOS first; complete a Windows-specific feasibility spike only after macOS closes the shared build/config blockers and equivalent contract coverage is defined | Start of P6 |
| Security/resource exhaustion on malformed memory images | Medium | High | Bounded analysis budgets and defensive error taxonomy | Fuzz/negative test failures |

## 4. ADR Backlog

| ADR title | Question answered | Needed by |
| --- | --- | --- |
| ADR-001 Public Scope Model | What is the MVP input model: memory+arch (A), full-binary (B), or hybrid (C)? **Decided: Option A for MVP.** See `specs.md` §5.5. | End of P0 (decided) |
| ADR-002 Bridge Surface Stability | What exact boundary is considered stable API vs internal? **Decided: nanobind C++ extension module.** Stable boundary is the public Python API (`specs.md` §3); the nanobind extension and all C++ bridge code are unstable internals. See `specs.md` §6. | Start of P2 (decided) |
| ADR-003 Determinism Oracle Level | How strict should C output comparison be (canonical text vs semantic tokens)? **Decided: normalized token/structure comparison, not canonical text.** See `tests/specs/fixtures.md` §2. | End of P1 (decided) |
| ADR-004 Runtime Asset Policy | Which `ghidra-sleigh` asset profile is flatline's default and how can users override it? **Decided:** flatline depends on `ghidra-sleigh` for the default runtime-data UX and auto-discovers its runtime-data root when `runtime_data_dir` is omitted. The default expectation is the full multi-ISA `ghidra-sleigh` install, which satisfies priority-ISA coverage plus bundled best-effort enumeration for other processors. Lighter builds such as `all_processors=false` remain supported only as explicit custom runtime-data roots passed via `runtime_data_dir`. Flatline does not add a second size gate in P2; size/compliance remains tracked for P3. Auto-discovered upstream tag/commit drift in `ghidra-sleigh` is surfaced as a runtime warning rather than a silent fallback. | End of P2 (decided) |
| ADR-005 Analysis Budget Defaults | What are default time/resource limits per request? **Decided:** flatline applies a fixed per-request `AnalysisBudget(max_instructions=100000)` default across the Linux MVP matrix, and callers may override `max_instructions` explicitly per request. No wall-clock timeout is exposed in P2 because the pinned Ghidra callable surface only provides instruction-count limiting via `Architecture::max_instructions`. See `specs.md` §3.3 and §7. | End of P2 (decided) |
| ADR-006 Logging and Diagnostics | Which diagnostic fields are emitted by default? **Decided:** P2 emits diagnostics only through startup/runtime-data `RuntimeWarning` messages and structured `WarningItem` / `ErrorItem` payloads. Diagnostic text may include full filesystem paths for debuggability; raw memory-image bytes are never emitted. No path redaction is applied because flatline is a library running in the caller's own process. No general-purpose logging sink is exposed in P2. | End of P2 (decided) |
| ADR-007 License Compliance Process | What release-time checks are mandatory for redistribution? **Decided:** releases must ship root `LICENSE` and `NOTICE`, keep the vendored Ghidra source attribution and declared `ghidra-sleigh` dependency recorded in `docs/compliance.md`, and pass `python tools/compliance.py` before tagging. The compliance, footprint, release-readiness, and artifact-audit helpers now live under `tools/flatline_dev` with `tools/*.py` wrappers as repo-only commands excluded from distribution artifacts (wheels and sdists). | End of P3 (decided) |
| ADR-008 Cross-Platform Order | macOS-first or Windows-first after Linux host MVP? **Decided:** macOS first, then Windows. P6 starts by removing shared build-system assumptions (for example GCC-only Meson flags), documenting the feasibility findings in `docs/host_feasibility.md`, and proving equivalent contract coverage on macOS before taking on MSVC/Windows-specific blockers. | Start of P6 (decided) |
| ADR-012 Enriched Output Design | What pcode/varnode representation do frozen Python types expose, and at which decompilation stage is data extracted? Covers opcode table mapping, varnode graph topology (inputs/outputs/def-use edges), extraction point in the action pipeline (pre- vs post-simplification), and whether enriched data lives inside `FunctionInfo` or a separate companion type. Target use cases: BSim-style similarity with custom hyperparameters, binary diffing, data flow / taint analysis, semantic understanding. | Start of P7 |
| ADR-009 ISA Variant Scope | Which ISA variants (e.g., Thumb/Thumb-2, microMIPS, RV32 vs RV64 extensions) are in-scope for priority fixture coverage vs best-effort? **Decided: x86 has both 32-bit and 64-bit fixture coverage; other ISA families have one representative variant each — ARM64 (AArch64), RISC-V 64, MIPS32 — for diverse bitwidth coverage.** Other variants (ARM32/Thumb, RV32, MIPS64, microMIPS) are best-effort with no dedicated fixtures. See `tests/specs/fixtures.md` §1. | End of P1 (decided) |
| ADR-010 Runtime Data Packaging | How are compiled `.sla` and runtime data files packaged and distributed? **Decided: separate `ghidra-sleigh` pip package** (import `ghidra_sleigh`). It builds `sleighc` from Ghidra C++ sources at package build time, compiles `.sla` files ahead of use, ships them as package data, and exposes `ghidra_sleigh.get_runtime_data_dir()` for consumers. ADR-004 now defines flatline's default dependency-backed asset policy on top of this mechanism. See `patacca/ghidra-sleigh`. | Start of P2 (decided) |
| ADR-011 Setup Failure Taxonomy | How should user-fixable install/startup/runtime-data failures be classified? **Decided:** expose `configuration_error` for missing/bad `runtime_data_dir`, unavailable default `ghidra-sleigh` runtime data, and other user-fixable setup failures; reserve `internal_error` for unexpected flatline/bridge/native bugs. | P3 (decided) |

## 5. Release and Versioning Plan

Release stream model:
- One active stream per latest upstream decompiler pin.
- Upstream bump replaces prior pin; no parallel support matrix across upstream versions.
- The initial public release for this stream is `0.1.0`, finalized from the
  earlier `0.1.0.dev0` release-candidate line.

Versioning rules:
- `MAJOR`: breaking Python API contract change.
- `MINOR`: backward-compatible capabilities, additive metadata/warnings, upstream bump that preserves public contract.
- `PATCH`: bug fixes and determinism improvements with unchanged contract shape.

Upstream bump protocol:
1. Create bump candidate branch with new upstream pin.
2. Regenerate decompiler inventory and diff callable contract.
3. Re-run full fixture and contract matrix across the committed confidence variants (x86_64, x86_32, ARM64, RISC-V 64, MIPS32).
4. Verify Sleigh spec compatibility for the committed confidence variants; flag any ISA-specific regressions.
5. Classify changes:
- Contract preserved -> minor release.
- Contract changed -> major release with migration notes.

Deprecation policy:
- Minimum one minor release of deprecation notice before removing public API elements.
- Emergency removals allowed only for security/compliance issues and require explicit release-note callout.

## 6. Ownership and Tracking

Required recurring artifacts per phase:
- Decision log (ADR status).
- Risk review update.
- Contract-test coverage map (with per-ISA breakdown for the committed confidence variants).
- Fixture/version manifest (indexed by target ISA).

Minimum weekly checks during active delivery:
- Open risks by severity.
- Determinism regression trend.
- Performance budget trend.
- Packaging size and compliance status.
