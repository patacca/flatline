# ghidralib Roadmap

## 0. Baseline and Policy

Pinned baseline for this roadmap:
- Ghidra tag: `Ghidra_12.0.3_build`
- Commit: `09f14c92d3da6e5d5f6b7dea115409719db3cce1` (2026-02-10)

Product policy:
- Linux MVP first.
- Cross-platform expansion after Linux contract stability gates.
- One upstream decompiler version supported at a time (latest only).

## 1. Phases and Milestones

| Phase | Focus | Entry criteria | Exit criteria |
| --- | --- | --- | --- |
| P0 | Spec lock | Inventory, MVP contract, experiment notes exist | `docs/specs.md` and this roadmap accepted; open questions tracked |
| P1 | Contract test harness | P0 complete | Definitions-only test suites and oracle strategy committed |
| P2 | Linux MVP delivery | P1 complete | Linux x86_64 function decompilation contract satisfied for core fixture matrix |
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

### M1: Contract harness ready
- Inputs:
- test catalog with unit/integration/regression/negative/contract coverage
- fixture strategy and normalization/oracle rules
- Exit checks:
- every API contract clause maps to at least one test ID
- unsupported/invalid flows have explicit negative tests

### M2: Linux MVP behavior complete
- Inputs:
- session startup, pair enumeration, single-function decompile behavior
- Exit checks:
- known-function and jump-table fixtures produce deterministic pass under oracle rules
- invalid-address, unsupported-language/compiler produce structured failures

### M3: Packaging and compliance complete
- Inputs:
- bundled runtime data policy and legal artifact manifest
- Exit checks:
- package installs without external Ghidra checkout
- license/compliance review checklist signed off

### M4: Release readiness
- Inputs:
- changelog, upgrade notes, regression/perf data
- Exit checks:
- SemVer classification approved
- contract tests green on release matrix

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
| Runtime package size grows beyond acceptable limits | Medium | Medium | Curated asset set for MVP; add size budget and gate in release checklist | Artifact size threshold breach |
| ABI/bridge stability regressions | Medium | High | Strict contract tests and explicit stability tiers | Failing contract suite |
| License/redistribution non-compliance | Low | High | Compliance checklist, notice bundling, source-attribution audit | Release candidate review |
| CI/toolchain variance causes flaky results | Medium | Medium | Stable build/test matrix and deterministic fixture harness | Flake rate trend in CI |
| Windows portability blockers discovered late | Medium | High | Separate Windows ADR and early feasibility spike before commitment | Start of P6 |
| Security/resource exhaustion on malformed binaries | Medium | High | Bounded analysis budgets and defensive error taxonomy | Fuzz/negative test failures |

## 4. ADR Backlog

| ADR title | Question answered | Needed by |
| --- | --- | --- |
| ADR-001 Public Scope Model | MVP uses full-binary scope only or reserves hybrid API now? | End of P0 |
| ADR-002 Bridge Surface Stability | What exact boundary is considered stable API vs internal? | End of P1 |
| ADR-003 Determinism Oracle Level | How strict should C output comparison be (canonical text vs semantic tokens)? | End of P1 |
| ADR-004 Runtime Asset Policy | Which language/compiler assets are mandatory for MVP package? | End of P2 |
| ADR-005 Analysis Budget Defaults | What are default time/resource limits per request? | End of P2 |
| ADR-006 Logging and Redaction | Which diagnostic fields are emitted and redacted by default? | End of P2 |
| ADR-007 License Compliance Process | What release-time checks are mandatory for redistribution? | End of P3 |
| ADR-008 Cross-Platform Order | macOS-first or Windows-first after Linux MVP? | Start of P6 |

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
3. Re-run full fixture and contract matrix.
4. Classify changes:
- Contract preserved -> minor release.
- Contract changed -> major release with migration notes.

Deprecation policy:
- Minimum one minor release of deprecation notice before removing public API elements.
- Emergency removals allowed only for security/compliance issues and require explicit release-note callout.

## 6. Ownership and Tracking

Required recurring artifacts per phase:
- Decision log (ADR status).
- Risk review update.
- Contract-test coverage map.
- Fixture/version manifest.

Minimum weekly checks during active delivery:
- Open risks by severity.
- Determinism regression trend.
- Performance budget trend.
- Packaging size and compliance status.
