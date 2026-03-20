# ISA Support

flatline can decompile code for any architecture that the Ghidra decompiler
supports — but not all architectures carry the same confidence level. This
page explains the two tiers of support and how to find out what is available
in your installation.

## Two Tiers: Fixture-Backed vs Best-Effort

### Tier 1: Fixture-backed

For a small set of priority architectures, the flatline test suite maintains
known-good decompilation output as committed test fixtures. Each fixture
contains a compiled binary snippet and a reference decompilation result. The
regression test suite checks these fixtures on every CI run.

What this means in practice:

- decompilation is known to work for representative code patterns on these ISAs.
- regressions in decompilation quality or correctness are caught automatically.
- the output contract (c_code, FunctionInfo structure, diagnostic flags) has
  been validated against real inputs.

The five fixture-backed ISAs are:

| ISA | `language_id` example |
|-----|----------------------|
| x86 64-bit | `x86:LE:64:default` |
| x86 32-bit | `x86:LE:32:default` |
| ARM64 (AArch64) | `AARCH64:LE:64:v8A` |
| RISC-V 64-bit | `RISCV:LE:64:RV64I` |
| MIPS 32-bit | `MIPS:LE:32:default` |

### Tier 2: Best-effort bundled

All other Ghidra-supported architectures whose processor definition assets
ship with `ghidra-sleigh` are available to use. They will appear in
`list_language_compilers()`, and the decompiler will attempt to process code
for them. However:

- there are no committed test fixtures for these ISAs.
- decompilation quality has not been systematically validated.
- regressions may go undetected between flatline releases.

Best-effort does not mean broken — Ghidra has broad ISA support and these
architectures often work well. It means flatline makes no forward guarantees
about output consistency for them.

Examples of best-effort architectures include PowerPC, SPARC, 68000, ARM
Thumb variants, and many others. The exact list depends on the `ghidra-sleigh`
version installed.

## Discovering Available Targets

Use `list_language_compilers()` to see every `(language_id, compiler_spec)`
pair available in your installation:

```python
import flatline

pairs = flatline.list_language_compilers()
for pair in pairs:
    print(pair.language_id, pair.compiler_spec)
```

To filter for a specific processor family, match on the prefix of `language_id`:

```python
pairs = flatline.list_language_compilers()

x86_pairs = [p for p in pairs if p.language_id.startswith("x86:")]
arm_pairs  = [p for p in pairs if p.language_id.startswith("AARCH64:")]
riscv_pairs = [p for p in pairs if p.language_id.startswith("RISCV:")]
mips_pairs = [p for p in pairs if p.language_id.startswith("MIPS:")]
```

## Understanding `language_id`

A `language_id` is a colon-separated string with four fields:

```
processor:endianness:bitsize:variant
```

| Field | Meaning | Examples |
|---|---|---|
| `processor` | Processor family name | `x86`, `AARCH64`, `RISCV`, `MIPS`, `PowerPC` |
| `endianness` | Byte order | `LE` (little-endian), `BE` (big-endian) |
| `bitsize` | Address width in bits | `32`, `64` |
| `variant` | ISA sub-variant or extension set | `default`, `v8A`, `RV64I` |

For example, `x86:LE:64:default` identifies 64-bit x86 in little-endian byte
order using the default variant. `MIPS:LE:32:default` identifies 32-bit MIPS
in little-endian byte order.

The `language_id` values are defined by the Ghidra processor module `.ldefs`
files shipped with `ghidra-sleigh`. If you are unsure which `language_id` to
use for a target, call `list_language_compilers()` and look for the processor
family name.

## Support Confidence Summary

| Tier | Coverage | Regression Tests | Forward Guarantee |
|---|---|:---:|:---:|
| Tier 1: fixture-backed | x86 32/64, ARM64, RISC-V 64, MIPS32 | Yes | Yes |
| Tier 2: best-effort | All other bundled Ghidra ISAs | No | No |

If you need Tier 1 confidence for an ISA that is currently Tier 2, the path to
promotion is adding a test fixture: a representative compiled snippet plus a
reference decompilation oracle. See `tests/fixtures/` for the existing fixture
format and `tests/fixtures/generate_hex_fixtures.py` for how they are
generated.
