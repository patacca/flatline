# flatline

**flatline** is a Python wrapper around the Ghidra decompiler engine. It gives
you programmatic access to decompilation — pass a raw memory image and a
function address, get back decompiled C code and structured metadata — without
requiring a Ghidra installation, a GUI, or a project database. The native
decompiler core is embedded directly in the package and driven through a stable
Python API.

## Features

- **Single-function decompilation from memory images** — provide bytes, a base
  address, and a function entry point; receive decompiled C source with no
  intermediate files or tooling.
- **Structured output** — every result includes both the C code string and a
  `FunctionInfo` object covering the function prototype, local variables, call
  sites, jump tables, and diagnostic flags.
- **Multi-ISA support** — fixture-backed confidence for x86 32/64, AArch64,
  RISC-V 64, and MIPS32; other Ghidra-supported architectures are available on
  a best-effort basis.
- **Deterministic resource limits** — `AnalysisBudget` caps the p-code
  instruction count per request, giving you a hard bound on analysis work
  regardless of input complexity.
- **Auto-discovered runtime data** — Sleigh processor definitions ship via the
  companion `ghidra-sleigh` package and are discovered automatically; no manual
  path configuration is needed.
- **Shipped X-Ray viewer** — `flatline-xray` is an optional interactive layer
  for the same memory-image contract, adding graph inspection and assembly
  browsing without changing the core API.

## Quick start

```python
import binascii
import flatline

# lea eax, [rdi+rsi]; ret  (x86-64, little-endian, with NOP padding)
image = binascii.unhexlify("8d0437c390909090909090909090909090909090")

request = flatline.DecompileRequest(
    memory_image=image,
    base_address=0x1000,
    function_address=0x1000,
    language_id="x86:LE:64:default",
    compiler_spec="gcc",
)

result = flatline.decompile_function(request)
print(result.c_code)
```

## Next steps

- [Installation](installation.md) — install flatline and verify the setup.
- [Getting Started](getting-started.md) — a step-by-step tutorial covering the
  core workflow.
- [X-Ray](xray/index.md) — learn the shipped viewer and how it fits the core
  request model.
