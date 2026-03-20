# Getting Started

This tutorial walks you through decompiling your first function with flatline.
By the end you will know how to construct a request, read the structured result,
and use a session for batch work.

## What flatline needs

flatline does not parse binary file formats. Instead it operates on a flat
memory image: a `bytes` object representing a contiguous region of the address
space, plus the virtual addresses that locate it and the function inside it.
This keeps the API format-agnostic — you can feed it raw bytes from a `bytes`
literal, from `mmap`, from a segment you extracted with a parser library, or
from anywhere else.

## Minimal example

The snippet below decompiles a short x86-64 function encoded directly as hex.
The function computes `eax = edi + esi` using a `lea` instruction, then returns.

```python
import binascii
import flatline

# Raw bytes: lea eax, [rdi+rsi]; ret  (with NOP padding)
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

Running this prints the decompiled C source. For this simple function you will
see something like:

```c
int FUN_00001000(int param_1, int param_2)
{
  return param_2 + param_1;
}
```

## Understanding DecompileRequest

Every decompilation starts with a `DecompileRequest`. Here is what each field
means:

**`memory_image`** (`bytes` or `bytearray`)
: The raw bytes of the memory region. Must be non-empty. flatline does not
  know about ELF sections, PE headers, or any other format — you provide the
  bytes directly.

**`base_address`** (`int`)
: The virtual address that corresponds to the first byte of `memory_image`. In
  the example above the image starts at `0x1000`, so byte index 0 in the image
  represents address `0x1000`.

**`function_address`** (`int`)
: The entry-point address of the function to decompile. Must fall within the
  range `[base_address, base_address + len(memory_image))`. Here the function
  starts at the very beginning of the image, so `function_address` equals
  `base_address`.

**`language_id`** (`str`)
: Identifies the target ISA. The format is
  `<arch>:<endian>:<bits>:<variant>`. Common values:

  | Architecture | `language_id` |
  |---|---|
  | x86-64 | `x86:LE:64:default` |
  | x86-32 | `x86:LE:32:default` |
  | AArch64 | `AARCH64:LE:64:v8A` |
  | RISC-V 64-bit | `RISCV:LE:64:RV64I` |
  | MIPS32 | `MIPS:LE:32:default` |

  Call `flatline.list_language_compilers()` to enumerate all pairs available
  in your installation.

**`compiler_spec`** (`str | None`)
: Selects the calling-convention model. `"gcc"` and `"windows"` are the most
  common values. Pass `None` to use the language's default.

**`runtime_data_dir`** (`str | None`)
: Path to a custom Ghidra runtime data directory. Omit this (or pass `None`)
  to use the auto-discovered path from `ghidra-sleigh`. You only need this when
  working with a non-standard installation.

**`analysis_budget`** (`AnalysisBudget | None`)
: Controls how much analysis work the decompiler may perform. Defaults to
  `AnalysisBudget(max_instructions=100_000)`. Increase this for very large or
  deeply recursive functions; decrease it for tighter latency budgets.

!!! note
    `function_size_hint` is an optional advisory hint (in bytes) that can
    improve decompilation quality for functions whose boundaries are hard for
    the decompiler to determine automatically. It is not required for most
    cases.

## Reading DecompileResult

`decompile_function` returns a `DecompileResult`. Its key attributes are:

**`c_code`** (`str | None`)
: The decompiled C source as a string. `None` if decompilation failed.

**`function_info`** (`FunctionInfo | None`)
: Structured data about the function. `None` if decompilation failed.

**`warnings`** (`list[WarningItem]`)
: Warnings emitted during the three decompiler phases (`init`, `analyze`,
  `emit`). Non-empty warnings do not necessarily mean failure — the C code
  may still be valid.

**`error`** (`ErrorItem | None`)
: Populated only when decompilation fails. Inspect `error.category` and
  `error.message` for details.

### Inspecting function_info

`result.function_info` gives you the structured view of the function:

```python
info = result.function_info

print(info.name)           # e.g. "FUN_00001000"
print(hex(info.entry_address))  # e.g. "0x1000"
print(info.size)           # size of the function body in bytes
print(info.is_complete)    # True if decompilation fully succeeded

proto = info.prototype
print(proto.calling_convention)  # e.g. "__cdecl"
print(proto.return_type.name)    # e.g. "int"

for param in proto.parameters:
    print(f"  param {param.index}: {param.type.name} {param.name}")

for var in info.local_variables:
    print(f"  local: {var.type.name} {var.name}")
```

### Checking for warnings

```python
for w in result.warnings:
    print(f"[{w.phase}] {w.code}: {w.message}")
```

!!! tip
    Always check `result.error` before accessing `result.c_code` or
    `result.function_info`. Both are `None` when an error is present.

    ```python
    if result.error:
        print(f"Decompilation failed ({result.error.category}): {result.error.message}")
    else:
        print(result.c_code)
    ```

## Session-based usage

`decompile_function` is a one-shot convenience wrapper: it creates a
`DecompilerSession`, runs one request, and closes the session. For batch work
— decompiling many functions in a loop — it is more efficient to manage the
session explicitly so you pay the initialization cost only once.

Use `DecompilerSession` as a context manager to ensure the session is always
closed even if an exception is raised:

```python
import binascii
import flatline

image = binascii.unhexlify("8d0437c390909090909090909090909090909090")

functions = [
    (0x1000, 0x1000),
    # add more (base_address, function_address) pairs here
]

with flatline.DecompilerSession() as session:
    for base_addr, func_addr in functions:
        request = flatline.DecompileRequest(
            memory_image=image,
            base_address=base_addr,
            function_address=func_addr,
            language_id="x86:LE:64:default",
            compiler_spec="gcc",
        )
        result = session.decompile_function(request)
        if result.error:
            print(f"  {hex(func_addr)}: error — {result.error.message}")
        else:
            print(f"  {hex(func_addr)}: {result.function_info.name}")
```

The session also exposes `list_language_compilers()` to enumerate valid
language/compiler pairs without needing a separate call:

```python
with flatline.DecompilerSession() as session:
    pairs = session.list_language_compilers()
    for pair in pairs[:5]:
        print(pair.language_id, pair.compiler_spec)
```

!!! tip
    Prefer the session form whenever you are decompiling more than one
    function. The session pays the decompiler library initialization and
    runtime data discovery cost once, so batch calls avoid redundant
    startup work compared to creating a new one-shot session each time.
