# Fixture Inventory

Committed native-memory fixtures are ASCII `.hex` files storing one contiguous
raw memory image per ADR-001. All fixtures assume `base_address=0x1000` and
`function_address=0x1000`.

Regeneration entrypoint:
- `source .venv/bin/activate && python tests/fixtures/generate_hex_fixtures.py`

Padding rationale for the add fixtures:
- Flatline currently materializes a function symbol without a size bound, so Ghidra performs a small decode/lookahead past the terminal return. The add fixtures therefore carry the smallest mapped tail that still decompiles deterministically.

| Fixture ID | File | Source | Language / compiler | Size (bytes) | SHA256 | Extraction command | Note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fx_add_elf64` | `fx_add_elf64.hex` | `sources/fx_add_elf64.s` | `x86:LE:64:default` / `gcc` | 20 | `c256c0e67b4e9c9493982d00effc6ece20d1e296312034b675e35f72959b2ddb` | `clang --target=x86_64-linux-gnu -c ... && readelf -x .text ...` | Baseline happy-path fixture |
| `fx_add_elf32` | `fx_add_elf32.hex` | `sources/fx_add_elf32.s` | `x86:LE:32:default` / `gcc` | 25 | `d3d3e02046fef3b2cd6baab50c71b221996d84c2526a750cc15b4a33a79a8f24` | `clang --target=i386-linux-gnu -c ... && readelf -x .text ...` | x86 32-bit coverage |
| `fx_add_arm64` | `fx_add_arm64.hex` | `sources/fx_add_arm64.s` | `AARCH64:LE:64:v8A` / `default` | 24 | `9bfea10d7217396fb690a5727f3716948b218e9457c513a9c551642286e6d330` | `clang --target=aarch64-linux-gnu -c ... && readelf -x .text ...` | ARM64 coverage |
| `fx_add_riscv64` | `fx_add_riscv64.hex` | `sources/fx_add_riscv64.s` | `RISCV:LE:64:RV64I` / `gcc` | 20 | `a6318f84d1179297aac08cca3a0bcbf7b630202a7dc88363f28268d6501189b5` | `clang --target=riscv64-linux-gnu -c ... && readelf -x .text ...` | RISC-V 64 coverage |
| `fx_add_mips32` | `fx_add_mips32.hex` | `sources/fx_add_mips32.s` | `MIPS:LE:32:default` / `default` | 28 | `f312dbb7760a8c39a3582b09630b667d3999da7daa72a77ede41847397d1d14f` | `clang --target=mipsel-linux-gnu -c ... && readelf -x .text ...` | MIPS32 coverage |
| `fx_switch_elf64` | `fx_switch_elf64.hex` | `sources/fx_switch_elf64.c` | `x86:LE:64:default` / `gcc` | 4160 | `4c0dd28c39f5dd587bac1c842e21260cfdf7473c237f9d12f981f98cc2aa0b2b` | `clang -O2 -fno-pic -no-pie -nostdlib ... && objcopy -O binary -j .text -j .rodata ...` | Compiler-generated jump-table fixture |
| `fx_warning_elf64` | `fx_warning_elf64.hex` | `sources/fx_warning_elf64.s` | `x86:LE:64:default` / `gcc` | 68 | `ab27713e0e565347fb65a1c2e241240a235cfad69e73d4cc06b12d2ebf41eecc` | `clang --target=x86_64-linux-gnu -c ... && readelf -x .text ...` | Warning-only success fixture |

Logical test cases without separate artifact files:
- `fx_invalid_addr_case` reuses `fx_add_elf64` with an unmapped `function_address`.
- `fx_invalid_memory` is an empty memory-image request rejected during `DecompileRequest` construction.

Runtime data source for native tests: `ghidra_sleigh.get_runtime_data_dir()`.
Upstream pin used when generated: `Ghidra_12.0.3_build` @ `09f14c92d3da6e5d5f6b7dea115409719db3cce1`.
License / redistribution note: all fixture bytes are redistributable synthetic machine code authored in-repo or compiled from tiny in-repo source snippets without third-party binary payloads.
