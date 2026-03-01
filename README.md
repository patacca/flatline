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
- Meson 1.6+

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

## Quick start

```python
from flatline import decompile, DecompileRequest

result = decompile(DecompileRequest(
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

# Run tests
pytest              # all tests
pytest -m unit      # only unit tests

# Lint
ruff check src/ tests/

# Multi-version testing
tox
```

## Project status

Early development (pre-MVP). The specification and test harness are complete;
implementation is in progress. See [docs/roadmap.md](docs/roadmap.md) for the
full plan.

## License

Apache-2.0
