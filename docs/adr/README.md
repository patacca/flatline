# Architecture Decision Records

This directory is the canonical home for accepted flatline architecture
decision records.

Maintained docs should describe the current policy or behavior and link here
when they need the underlying decision rationale.

## Accepted ADRs

| ID | Title | Summary |
| --- | --- | --- |
| [ADR-001](adr-001.md) | Public Scope Model | Keep single-function decompilation from caller-provided memory as the core contract. |
| [ADR-002](adr-002.md) | Bridge Surface Stability | Treat the public Python API as stable and the nanobind/native bridge as internal. |
| [ADR-003](adr-003.md) | Determinism Oracle Level | Measure deterministic behavior with normalized token/structure oracles, not exact pretty-printed C. |
| [ADR-004](adr-004.md) | Runtime Asset Policy | Default to auto-discovered `ghidra-sleigh` runtime data and keep lighter/custom setups explicit. |
| [ADR-005](adr-005.md) | Analysis Budget Defaults | Apply a fixed `AnalysisBudget(max_instructions=100000)` default with explicit caller override. |
| [ADR-006](adr-006.md) | Logging and Diagnostics | Use structured warnings/errors, allow helpful filesystem paths, and never emit raw memory bytes. |
| [ADR-007](adr-007.md) | License Compliance Process | Keep redistribution checks explicit through repo artifacts and deterministic audit tooling. |
| [ADR-008](adr-008.md) | Cross-Platform Order | Expand host support macOS first, then Windows. |
| [ADR-009](adr-009.md) | ISA Variant Scope | Promise fixture-backed confidence only for x86 32/64, ARM64, RISC-V 64, and MIPS32. |
| [ADR-010](adr-010.md) | Runtime Data Packaging | Ship compiled Sleigh runtime data through the separate `ghidra-sleigh` package. |
| [ADR-011](adr-011.md) | Setup Failure Taxonomy | Reserve `configuration_error` for user-fixable setup issues and `internal_error` for bugs. |
| [ADR-012](adr-012.md) | Enriched Output Design | Keep pcode/varnode output opt-in and expose it through `DecompileResult.enriched`. |
| [ADR-013](adr-013.md) | Wheel Distribution Strategy | Publish CPython 3.13/3.14 64-bit wheels for the locked Tier-1 host matrix. |
