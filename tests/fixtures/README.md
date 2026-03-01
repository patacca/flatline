# Fixture Inventory Placeholder

This directory will contain small redistributable fixture artifacts for the MVP matrix.
Fixtures are raw memory images per ADR-001 (Option A: memory + arch + function-level).

Planned fixture IDs:
- `fx_add_elf64` — memory image extracted from simple arithmetic function ELF (x86_64)
- `fx_switch_elf64` — memory image extracted from switch-case function ELF (x86_64)
- `fx_add_arm64` — memory image extracted from simple arithmetic function (AArch64)
- `fx_add_riscv64` — memory image extracted from simple arithmetic function (RISC-V 64-bit)
- `fx_add_mips32` — memory image extracted from simple arithmetic function (MIPS 32-bit)
- `fx_runtime_data_min` — curated language/compiler runtime data directory
- `fx_invalid_memory` — empty/zero-length memory image for negative testing

Logical test cases (no separate fixture file):
- `fx_invalid_addr_case` — uses `fx_add_elf64` with unmapped address input

Manifest requirements when fixtures are added:
- fixture id
- source recipe (including source binary and extraction method)
- SHA256
- base address and size
- target architecture (language_id)
- upstream pin used when generated
- license/redistribution note
