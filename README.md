# flatline

Python wrapper around the Ghidra decompiler. Provides a stable, pip-installable
interface for single-function decompilation with structured output -- no Ghidra
installation required.

Named after Dixie Flatline from William Gibson's *Neuromancer* (1984) -- a dead
hacker's ROM construct, a consciousness extracted from hardware. A fitting
metaphor for decompilation: extracting meaning from dead code.

## Features

- **Single-function decompilation** -- pass a memory image, base address, and
  function entry point; get back structured C output with diagnostics.
- **Multi-ISA** -- supports any Ghidra-supported target architecture. Priority
  coverage for x86 (32/64), ARM (32/64), RISC-V (32/64), and MIPS (32/64).
- **Self-contained** -- runtime data (language/compiler specs) is bundled in the
  wheel; no external Ghidra build needed.
- **Deterministic** -- repeated decompiles of the same input produce
  structurally equivalent output.

## Requirements

- Python 3.13+
- Linux x86_64 (macOS/Windows planned)
- C++20 compiler (for source builds with native bridge)
- Ninja

## Installation

```bash
pip install flatline
```

For development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Native bridge

Real decompilation requires the native bridge -- a compiled C++ extension
(`flatline._flatline_native`) that links against the Ghidra decompiler library.
Without it the Python API is fully importable, but every `decompile_function`
call returns an `internal_error` result and `list_language_compilers` returns
an empty list.

The build has three modes, controlled by the `native_bridge` Meson option:

| Mode | How to set | Behaviour |
|------|------------|-----------|
| `auto` (default) | omit the flag | Builds the extension when a C++20 compiler and Ninja are found; silently falls back to the pure-Python stub otherwise. |
| `enabled` | `-Dnative_bridge=enabled` | Forces the native build; fails at install time if prerequisites are missing. Use this to validate the full decompilation stack. |
| `disabled` | `-Dnative_bridge=disabled` | Skips the native build entirely. All decompilation calls return `internal_error`. |

Force the native build explicitly (requires a C++20 compiler and Ninja):

```bash
pip install -e ".[dev]" -Csetup-args=-Dnative_bridge=enabled
```

Disable the native build explicitly (pure-Python stub only):

```bash
pip install -e ".[dev]" -Csetup-args=-Dnative_bridge=disabled
```

Tests that require the native extension are marked `requires_native` and
auto-skip with an actionable reason when `flatline._flatline_native` is not
importable.

## Quick start

```python
from flatline import DecompileRequest, decompile_function

result = decompile_function(DecompileRequest(
    memory_image=raw_bytes,
    base_address=0x400000,
    function_address=0x401000,
    language_id="x86:LE:64:default",
    compiler_spec="gcc",
))

print(result.c_code)
```

## Development

```bash
# Activate the venv (required for all commands)
source .venv/bin/activate

# Run tests + lint across configured environments
tox

# Run lint only
tox -e lint

# Run unit tests only
tox -e py313,py314 -- -m unit

# Run native-dependent tests (skipped automatically when the extension is absent)
tox -e py313,py314 -- -m requires_native
```

## Project status

Early development (pre-MVP). The specification and test harness are complete;
implementation is in progress. See [docs/roadmap.md](docs/roadmap.md) for the
full plan.

## License

Apache-2.0
