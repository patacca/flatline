Role: Software architect/spec writer.

Objective: Produce an SDD (Spec-Driven Development) plan for a Python library (temp name `ghidralib`) that provides a stable Python interface over the Ghidra Decompiler (C++), similar in purpose to r2ghidra (use only as inspiration; exclude r2ghidra-specific details from deliverables). No implementation specifics yet.

Read these first:
- notes/api/decompiler_inventory.md (primary: decompiler surface/contract)
- notes/api/mvp_contract.md (merge; parts obsolete—reconcile)
- notes/r2ghidra/integration_map.md (reference only)
- notes/experiments/ (test inspiration)

Baseline:
- Ghidra tag: Ghidra_12.0.3_build
- commit: 09f14c92d3da6e5d5f6b7dea115409719db3cce1 (2026-02-10)
- C++ path: third_party/ghidra/Ghidra/Features/Decompiler/src/decompile/cpp

Constraints:
- In-process decompiler execution is mandatory (Python↔C++ bridge required; don’t propose binding/build details yet).
- Package must be usable out-of-the-box via pip; users must not build/provide Ghidra. Plan for shipping the decompiler and address licensing/redistribution strategy.
- Target OS: Linux/macOS/Windows. MVP: Linux first; prioritize choices that preserve future cross-platform feasibility.
- Python versions: 3.13+.
- Version policy: support only the latest Ghidra decompiler (no multi-version ghidralib). Python API must be stable while Ghidra internals may change.

Methodology: SDD (Spec-Driven Development) + TDD planning. Deliver strategy, architecture choices, and test plan; NO code-level implementation specifics (no binding code, build scripts, class/method bodies, or packaging recipes).

Deliverables (create/overwrite):
1) docs/specs.md
   - Goals/non-goals, personas/use-cases
   - Public Python API contract: concepts, operations, data model, error model, stability guarantees + SemVer rules
   - Decompiler-facing contract (from decompiler_inventory.md): capabilities/invariants/limits; mapping to public API
   - Architecture decision space (no implementation):
     * Decompilation scope options: (A) bytes+arch/function-level vs (B) full program/binary using loaders vs hybrids
     * Pros/cons, risks, impact on determinism, performance, UX, fixtures, packaging, cross-platform
     * Recommendation(s) + explicit decision points requiring user choice
   - Strategy for “stable Python API over unstable Ghidra”: adapter boundaries, contract tests, change-detection process
   - Cross-cutting: determinism/oracles, concurrency model, perf budgets, security boundaries, logging, configuration, extensibility
   - MVP vs Next; merge mvp_contract.md, marking obsolete items and replacements
   - End with: Open Questions + Assumptions

2) docs/roadmap.md
   - Phases/milestones with entry/exit criteria (Linux MVP first; cross-platform later)
   - Risk register + mitigations (ABI drift, determinism, package size, CI/toolchains, license compliance, Windows risk, etc.)
   - ADR backlog (title + question answered + when needed)
   - Release/versioning plan aligned with “latest Ghidra only”

3) tests/ (definitions only)
   - Propose tests/ layout; write test-spec files (markdown and/or pytest skeletons) without real integration calls
   - For each test: purpose, fixtures, steps, assertions, oracle strategy, determinism constraints
   - Include unit/integration/regression/negative/contract tests
   - Define minimal fixture set (sample binaries) and expected-output strategy; how fixtures update when Ghidra changes

Style:
- Concise; bullets/tables preferred.
- Attribute spec items to note files when derived from them.
- Do not include r2ghidra-specific details in outputs.