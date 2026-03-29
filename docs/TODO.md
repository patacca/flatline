# flatline TODO

This file tracks next-scope work that remains relevant after the main planning
and specification docs were archived.
For current design posture, use `docs/design.md`. For historical full-detail
context, use `docs/archived/`.
All phases (P0-P7) and milestones (M0-M6) are closed; latest release is
`0.1.1`.

## Next-Scope Features

- [ ] **Binary convenience layer (Option C)**: file-loading convenience API over the core memory-image contract, handling ELF/PE/Mach-O parsing and memory extraction so callers can pass a file path instead of a raw memory image.
- [ ] **Multi-region memory input**: extend `DecompileRequest` with multi-region input and section metadata (readonly ranges, symbols).
- [ ] **Batch decompilation APIs**: decompile many functions in one call with bounded resources.
- [ ] **Enriched-output follow-ons**: CFG/basic-block exports, richer symbol/type links on pcode and varnodes, broader fixture coverage, and additional end-to-end downstream validations beyond the current use-def graph slice.

## Host and Platform Expansion

- [ ] **Linux aarch64 host promotion**: currently published-wheel-only; needs dedicated native contract lane and host-promotion evidence to become a supported runtime host.
- [ ] **macOS x86_64 host promotion**: currently published-wheel-only; same evidence bar as Linux aarch64.
- [ ] **32-bit Linux/Windows wheels**: deferred by ADR-013.
- [ ] **musllinux wheels**: deferred by ADR-013.
- [ ] **Windows ARM64 wheels**: deferred by ADR-013.
- [ ] **macOS universal2 wheels**: deferred by ADR-013.
- [ ] **Free-threaded CPython (3.13t)**: deferred until nanobind declares stable free-threaded support; concurrency model currently assumes GIL or caller-provided serialization.

## ISA Coverage

- [ ] **Extended ISA fixture coverage**: non-priority Ghidra-supported ISAs beyond the current fixture-backed set (x86 32/64, ARM64, RISC-V 64, MIPS32).
- [ ] **ISA variant fixtures**: ARM32/Thumb, RV32, MIPS64, microMIPS are best-effort with no dedicated fixtures.

## API and Contract Extensions

- [ ] **Wall-clock timeout**: deferred until the upstream callable surface provides a compatible cancellation mechanism (currently only instruction-count budget via `Architecture::max_instructions`).
- [ ] **TypeInfo sub-type details**: struct fields, pointer target, array element type; flat `name`/`size`/`metatype` was sufficient for MVP.
- [ ] **Parallel decompilation**: requires explicit session isolation policy; not exposed in current API.
- [ ] **General-purpose logging sink**: P2 emits diagnostics only through `RuntimeWarning` and structured `WarningItem`/`ErrorItem`; no user-configurable logging or redaction controls.

## Risks Still Open

- Upstream callable-surface drift on any Ghidra bump (high likelihood, high impact).
- Deterministic output drift across environments (medium likelihood, high impact).
- Runtime package size growth (medium-high likelihood, medium impact).
- ISA-specific Sleigh spec immaturity (medium likelihood, medium impact).
- Free-threaded CPython ABI breaking nanobind assumptions (medium likelihood, medium impact).
- CI cost for full matrix across all platforms and Python versions (medium likelihood, medium impact).
