# flatline Roadmap

## 0. Baseline and Policy

Pinned baseline for this roadmap:
- Ghidra tag: `Ghidra_12.0.3_build`
- Commit: `09f14c92d3da6e5d5f6b7dea115409719db3cce1` (2026-02-10)

Product policy:
- Linux host MVP first; multi-ISA target from day one.
- Priority target ISAs for MVP: x86 (32/64), ARM (32/64), RISC-V (32/64), MIPS (32/64).
- All other Ghidra decompiler-supported ISAs available via bundled runtime data (best-effort, no dedicated fixtures).
- Cross-platform host expansion (macOS/Windows) after Linux contract stability gates.
- One upstream decompiler version supported at a time (latest only).

## 1. Phases and Milestones

| Phase | Focus | Entry criteria | Exit criteria |
| --- | --- | --- | --- |
| P0 | Spec lock | Inventory, MVP contract, experiment notes exist | `docs/specs.md` and this roadmap accepted; open questions tracked; structured result object definitions (fields, types, error model, ownership/lifetime) locked in `specs.md` §3.3 |
| P1 | Contract test harness | P0 complete | Definitions-only test suites and oracle strategy committed |
| P2 | Linux MVP delivery | P1 complete | Linux host function decompilation contract satisfied for priority-ISA fixture matrix (x86, ARM, RISC-V, MIPS) and enumeration/error contract for all bundled ISAs |
| P3 | Packaging + compliance hardening | P2 complete | Bundled runtime assets policy finalized; license notices/compliance checks pass |
| P4 | Stabilization and regression control | P3 complete | Determinism/perf regression gates enforced in CI for pinned matrix |
| P5 | Initial public release | P4 complete | Release notes include contract guarantees, known limits, upgrade policy |
| P6 | Cross-platform expansion | P5 complete | macOS and Windows feasibility validated with equivalent contract coverage |

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
- per-ISA fixture manifest covering all priority ISAs (x86, ARM, RISC-V, MIPS)
- Exit checks:
- every API contract clause maps to at least one test ID
- unsupported/invalid flows have explicit negative tests
- priority ISAs each have at least one known-function fixture and one regression baseline

### M2: Linux MVP behavior complete
- Inputs:
- session startup, pair enumeration, single-function decompile behavior
- priority-ISA fixture results (x86, ARM, RISC-V, MIPS) and enumeration coverage for all bundled ISAs
- Exit checks:
- known-function and jump-table fixtures produce deterministic pass under oracle rules for each priority ISA
- invalid-address, unsupported-language/compiler produce structured failures (ISA-independent)
- bridge ownership and lifetime contract verified by contract/integration definitions
- `list_language_compilers()` returns valid pairs spanning all priority ISAs and any additionally bundled ISAs
- per-ISA performance baselines captured for priority ISAs

### M3: Packaging and compliance complete
- Inputs:
- bundled runtime data policy and legal artifact manifest
- multi-ISA runtime asset inventory (language definitions, Sleigh specs, compiler specs for all bundled ISAs)
- Exit checks:
- package installs without external Ghidra checkout
- license/compliance review checklist signed off
- package size budget validated with multi-ISA asset footprint

### M4: Release readiness
- Inputs:
- changelog, upgrade notes, regression/perf data
- Exit checks:
- SemVer classification approved
- contract tests green on release matrix

Note: M4 covers the exit criteria of both P4 (Stabilization and regression control)
and P5 (Initial public release). A separate M4b gate may be introduced if stabilization
and release activities require distinct checkpoints.

### M5: Cross-platform readiness (post-MVP)
- Inputs:
- platform feasibility findings for macOS/Windows
- Exit checks:
- platform-specific risk register entries are closed or accepted

## 3. Risk Register

| Risk | Likelihood | Impact | Mitigation | Trigger/monitor |
| --- | --- | --- | --- | --- |
| Upstream callable-surface drift breaks bridge assumptions | High | High | Pin upstream per release; mandatory inventory diff + contract rerun before bump | Any upstream bump proposal |
| Deterministic output drift across environments | Medium | High | Use normalized oracles and stable warning/error codes; pin fixture matrix | CI output diff on pinned fixtures |
| Runtime package size grows beyond acceptable limits | Medium-High | Medium | Curated asset set per ISA; size budget gate in release checklist; consider optional ISA packs if total exceeds threshold | Artifact size threshold breach |
| ISA-specific Sleigh spec immaturity degrades decompilation quality | Medium | Medium | Priority ISAs validated by fixture matrix; non-priority ISAs best-effort with enumeration/error coverage only | Fixture failure or user-reported quality regression per ISA |
| ISA variant edge cases (Thumb, microMIPS, RV extensions) cause unexpected failures | Medium | Medium | Restrict MVP fixtures to common ISA variants; document known variant limitations | Negative test failures on variant-specific fixtures |
| ABI/bridge stability regressions | Medium | High | Strict contract tests and explicit stability tiers | Failing contract suite |
| License/redistribution non-compliance | Low | High | Compliance checklist, notice bundling, source-attribution audit | Release candidate review |
| CI/toolchain variance causes flaky results | Medium | Medium | Stable build/test matrix and deterministic fixture harness | Flake rate trend in CI |
| Windows portability blockers discovered late | Medium | High | Separate Windows ADR and early feasibility spike before commitment | Start of P6 |
| Security/resource exhaustion on malformed memory images | Medium | High | Bounded analysis budgets and defensive error taxonomy | Fuzz/negative test failures |

## 4. ADR Backlog

| ADR title | Question answered | Needed by |
| --- | --- | --- |
| ADR-001 Public Scope Model | What is the MVP input model: memory+arch (A), full-binary (B), or hybrid (C)? **Decided: Option A for MVP.** See `specs.md` §5.5. | End of P0 (decided) |
| ADR-002 Bridge Surface Stability | What exact boundary is considered stable API vs internal? **Decided: nanobind C++ extension module.** Stable boundary is the public Python API (`specs.md` §3); the nanobind extension and all C++ bridge code are unstable internals. See `specs.md` §6. | Start of P2 (decided) |
| ADR-003 Determinism Oracle Level | How strict should C output comparison be (canonical text vs semantic tokens)? **Decided: normalized token/structure comparison, not canonical text.** See `tests/specs/fixtures.md` §2. | End of P1 (decided) |
| ADR-004 Runtime Asset Policy | Which language/compiler assets per ISA are mandatory for MVP package? Must address: priority ISA full bundles, non-priority ISA inclusion/exclusion criteria, and package size budget. | End of P2 |
| ADR-005 Analysis Budget Defaults | What are default time/resource limits per request? | End of P2 |
| ADR-006 Logging and Redaction | Which diagnostic fields are emitted and redacted by default? | End of P2 |
| ADR-007 License Compliance Process | What release-time checks are mandatory for redistribution? | End of P3 |
| ADR-008 Cross-Platform Order | macOS-first or Windows-first after Linux host MVP? | Start of P6 |
| ADR-009 ISA Variant Scope | Which ISA variants (e.g., Thumb/Thumb-2, microMIPS, RV32 vs RV64 extensions) are in-scope for priority fixture coverage vs best-effort? **Decided: x86 has both 32-bit and 64-bit fixture coverage; other ISA families have one representative variant each — ARM64 (AArch64), RISC-V 64, MIPS32 — for diverse bitwidth coverage.** Other variants (ARM32/Thumb, RV32, MIPS64, microMIPS) are best-effort with no dedicated fixtures. See `tests/specs/fixtures.md` §1. | End of P1 (decided) |

## 5. Release and Versioning Plan

Release stream model:
- One active stream per latest upstream decompiler pin.
- Upstream bump replaces prior pin; no parallel support matrix across upstream versions.

Versioning rules:
- `MAJOR`: breaking Python API contract change.
- `MINOR`: backward-compatible capabilities, additive metadata/warnings, upstream bump that preserves public contract.
- `PATCH`: bug fixes and determinism improvements with unchanged contract shape.

Upstream bump protocol:
1. Create bump candidate branch with new upstream pin.
2. Regenerate decompiler inventory and diff callable contract.
3. Re-run full fixture and contract matrix across all priority ISAs (x86, ARM, RISC-V, MIPS).
4. Verify Sleigh spec compatibility for priority ISAs; flag any ISA-specific regressions.
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
- Contract-test coverage map (with per-ISA breakdown for priority ISAs).
- Fixture/version manifest (indexed by target ISA).

Minimum weekly checks during active delivery:
- Open risks by severity.
- Determinism regression trend.
- Performance budget trend.
- Packaging size and compliance status.
