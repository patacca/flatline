# flatline TODO

This file tracks next-scope work that remains relevant after the main planning
and specification docs were archived.
For current design posture, use `docs/design.md`. For historical full-detail
context, use `docs/archived/`.
All phases (P0-P7) and milestones (M0-M6) are closed; latest release is
`0.1.2`.

## Next-Scope Features

- [ ] **Binary convenience layer (Option C)**: file-loading convenience API over the core memory-image contract, handling ELF/PE/Mach-O parsing and memory extraction so callers can pass a file path instead of a raw memory image.
- [ ] **Multi-region memory input**: extend `DecompileRequest` with multi-region input and section metadata (readonly ranges, symbols).
- [ ] **Batch decompilation APIs**: decompile many functions in one call with bounded resources.
- [ ] **Enriched-output follow-ons**: CFG/basic-block exports, richer symbol/type links on pcode and varnodes, broader fixture coverage, and additional end-to-end downstream validations beyond the current use-def graph slice.
- [ ] **Resolve fspec/iop varnode offsets**: at extraction time in the native bridge, recover the real callee address from `FuncCallSpecs::getFspecFromConst()` for `IPTR_FSPEC` varnodes (and analogously for `IPTR_IOP`), replacing the dangling C++ heap pointer currently exposed as the varnode offset.
- [ ] **Resolve register-space offsets to symbolic names**: map `(space='register', offset, size)` varnodes to their architecture-specific register names (e.g. `x0`, `RAX`) using the Sleigh language spec at extraction time.

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

## Under Evaluation

- [ ] **Custom decompilation pipeline control**: expose optional enrichment allowing callers to select which analysis actions/rules are included in the decompilation pipeline and optionally inject custom ones (leveraging Ghidra's ActionDatabase group-filtering and clone mechanism). Needs design evaluation before acceptance — not yet approved as future work.
- [ ] **xray selection highlighting**: when selecting asm instructions, avoid overlay borders on nodes; instead use grey-opaque background filling covering everything except selected nodes and edges. Improves visual focus on selected elements.
- [ ] **xray disassembly accuracy**: the assembly panel currently shows instructions at addresses derived from post-simplification pcode (`Function::beginOpAlive()`), not a complete linear disassembly of the binary function. This means: (1) dead-code-eliminated instructions are missing, and (2) the presented assembly reflects the decompiler's internal IR state rather than the raw binary. Options: (a) document the current behavior clearly in xray docs as "pcode-derived assembly" vs "raw disassembly", or (b) implement proper linear disassembly via Sleigh for the full function address range and offer a toggle between both views.

## API and Contract Extensions

- [ ] **Wall-clock timeout**: deferred until the upstream callable surface provides a compatible cancellation mechanism (currently only instruction-count budget via `Architecture::max_instructions`).
- [ ] **TypeInfo sub-type details**: struct fields, pointer target, array element type; flat `name`/`size`/`metatype` was sufficient for MVP.
- [ ] **Parallel decompilation**: requires explicit session isolation policy; not exposed in current API.
- [ ] **General-purpose logging sink**: P2 emits diagnostics only through `RuntimeWarning` and structured `WarningItem`/`ErrorItem`; no user-configurable logging or redaction controls.
- [ ] **Bitwise flag properties**: replace `is_*` boolean attributes (e.g., `is_constant`, `is_input`) with a single `flags` bitfield and property-based access for more idiomatic Python usage and efficient flag checks.

## Risks Still Open

- Upstream callable-surface drift on any Ghidra bump (high likelihood, high impact).
- Deterministic output drift across environments (medium likelihood, high impact).
- Runtime package size growth (medium-high likelihood, medium impact).
- ISA-specific Sleigh spec immaturity (medium likelihood, medium impact).
- Free-threaded CPython ABI breaking nanobind assumptions (medium likelihood, medium impact).
- CI cost for full matrix across all platforms and Python versions (medium likelihood, medium impact).
