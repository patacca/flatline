# Fixture Strategy

## 1. Minimal Fixture Set

| Fixture ID | Type | Purpose | Notes |
| --- | --- | --- | --- |
| `fx_add_elf64` | Memory image (x86_64) | Baseline known-function happy path | Raw memory extracted from simple arithmetic function ELF; `_elf64` suffix refers to source architecture |
| `fx_switch_elf64` | Memory image (x86_64) | Jump-table/switch CFG coverage | Raw memory extracted from switch-case ELF; `_elf64` suffix refers to source architecture |
| `fx_invalid_addr_case` | Logical case over `fx_add_elf64` | Invalid address negative behavior | Uses unmapped address input against `fx_add_elf64` memory image |
| `fx_runtime_data_min` | Runtime data directory | Pair enumeration and startup validation | Contains curated language/compiler assets required for MVP |
| `fx_invalid_memory` | Empty/zero-length memory image | Invalid memory image input | Tests structured error path for degenerate memory input |
| `fx_add_arm64` | Memory image (AArch64) | Multi-ISA known-function path (ARM) | Raw memory extracted from simple arithmetic function; ARM AArch64 |
| `fx_external_call_arm64` | Memory image (AArch64) | Exact-slice tail-padding coverage with out-of-span call targets | Raw memory extracted from hand-written ARM64 assembly; integration trims the main function so call targets resolve outside the supplied span |
| `fx_add_riscv64` | Memory image (RISC-V 64) | Multi-ISA known-function path (RISC-V) | Raw memory extracted from simple arithmetic function; RISC-V 64-bit |
| `fx_add_mips32` | Memory image (MIPS32) | Multi-ISA known-function path (MIPS) | Raw memory extracted from simple arithmetic function; MIPS 32-bit |
| `fx_delay_slot_branch_mips32` | Memory image (MIPS32) | Placeholder-op alias regression for `BUILD` -> `MULTIEQUAL` | Raw memory extracted from hand-written MIPS branch-delay-slot assembly that survives simplification with a merge node |
| `fx_delay_slot_call_mips32` | Memory image (MIPS32) | Placeholder-op alias regression for `DELAY_SLOT` -> `INDIRECT` | Raw memory extracted from hand-written MIPS call-delay-slot assembly that preserves an indirect side-effect op |
| `fx_add_elf32` | Memory image (x86_32) | x86 32-bit bitwidth coverage | Raw memory extracted from simple arithmetic function ELF; x86 32-bit; validates x86 family has both 32-bit and 64-bit fixture coverage |
| `fx_warning_elf64` | Memory image (x86_64) | Warning-inducing decompilation | Raw memory extracted from function with unreachable blocks, unimplemented instructions, or other warning-triggering patterns; used to validate warning-only success path and WarningItem structure |

Fixture format resolved by ADR-001 (Option A: memory + architecture + function-level).
Fixtures are raw memory images with accompanying metadata (base address, architecture).
Source binaries (ELF) are used during fixture generation but are not runtime test inputs.
Multi-ISA fixtures cover representative variants per ISA family: x86 (32+64), ARM64, RISC-V 64, MIPS32 (ADR-009).
Committed fixture artifacts live under `tests/fixtures/*.hex`.
Native tests resolve runtime data from the installed `ghidra-sleigh` package
via `ghidra_sleigh.get_runtime_data_dir()`.

## 2. Expected-Output Strategy

Textual outputs:
- Compare normalized token/structure representation, not raw formatting.
- Ignore whitespace-only differences and non-contractual comments.

Diagnostics:
- Assert stable error/warning categories and codes.
- Treat message strings as informative but not exact-match unless explicitly marked stable.

Metadata:
- Enforce required keys and value types.
- Allow additive keys in minor releases.

Regression baselines:
- `tests/_native_fixtures.py` carries the committed normalized C baselines, jump-table switch/target expectations, and warm-session p95 budgets used by the native regression suite.

## 3. Determinism Rules

- Freeze fixture binaries and runtime-data revision identifiers per release branch.
- Run regression suites under pinned upstream version only.
- Any fixture content change requires baseline regeneration in the same change set.

## 4. Fixture Update Process on Upstream Change

1. Create upstream bump branch and record new pin.
2. Re-run fixture generation pipeline and produce new revision ids.
3. Recompute normalized oracles and diff against prior baselines.
4. Label each delta:
- contract-preserving drift (accept with minor release notes), or
- contract-breaking drift (major release + migration notes).
5. Update `tests/fixtures/README.md` manifest and `tests/specs/test_catalog.md` references.
