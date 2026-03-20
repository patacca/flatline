# Enumerate Languages

Before decompiling, you need to know which `language_id` and `compiler_spec` values
are valid for your target. flatline ships runtime data for all bundled Ghidra processor
families. This guide shows how to enumerate them.

## One-shot enumeration

The quickest path is the module-level convenience function. It creates a session
internally, collects results, and closes the session for you.

```python
import flatline

pairs = flatline.list_language_compilers()

for pair in pairs:
    print(pair.language_id, pair.compiler_spec)
```

`list_language_compilers()` returns a list of `LanguageCompilerPair` objects. Each
object has two fields:

- `language_id` — the architecture identifier string (e.g. `"x86:LE:64:default"`)
- `compiler_spec` — the compiler model (e.g. `"gcc"`, `"windows"`)

## Session-based enumeration

If you already have a `DecompilerSession` open, call the method directly to avoid
the overhead of constructing a second session.

```python
from flatline import DecompilerSession, DecompileRequest

with DecompilerSession() as session:
    pairs = session.list_language_compilers()

    # Use the same session for decompilation
    result = session.decompile_function(request)
```

## Filtering by ISA family

`language_id` values are plain strings, so you can filter them with a list
comprehension. The prefix before the first `:` is the processor family name.

```python
import flatline

pairs = flatline.list_language_compilers()

# All x86 variants (32-bit and 64-bit)
x86_pairs = [p for p in pairs if p.language_id.startswith("x86:")]

# All AArch64 variants
aarch64_pairs = [p for p in pairs if p.language_id.startswith("AARCH64:")]

# All RISC-V variants
riscv_pairs = [p for p in pairs if p.language_id.startswith("RISCV:")]

# All MIPS variants
mips_pairs = [p for p in pairs if p.language_id.startswith("MIPS:")]
```

## Understanding the language_id format

A `language_id` is a colon-separated string with four components:

```
processor:endianness:bitsize:variant
```

| Component | Values | Example |
|-----------|--------|---------|
| `processor` | ISA family name | `x86`, `AARCH64`, `RISCV`, `MIPS` |
| `endianness` | `LE` (little-endian) or `BE` (big-endian) | `LE` |
| `bitsize` | Address size in bits | `32`, `64` |
| `variant` | Architecture variant or extension set | `default`, `v8A` |

Some examples from the fixture-backed ISAs:

| `language_id` | Architecture |
|---------------|-------------|
| `x86:LE:64:default` | x86-64 (AMD64) |
| `x86:LE:32:default` | x86 32-bit (IA-32) |
| `AARCH64:LE:64:v8A` | ARMv8-A (AArch64) |
| `RISCV:LE:64:RV64I` | RISC-V 64-bit |
| `MIPS:LE:32:default` | MIPS32 |

!!! tip
    Pass the `language_id` string directly to `DecompileRequest`. flatline raises
    `UnsupportedTargetError` at request time if the value is not recognized, so
    there is no need to pre-validate it against the enumerated list — but
    enumerating first is useful when building UIs or selecting targets programmatically.
