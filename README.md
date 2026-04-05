# flatline

[![PyPI](https://img.shields.io/pypi/v/flatline)](https://pypi.org/project/flatline/)
[![Python](https://img.shields.io/pypi/pyversions/flatline)](https://pypi.org/project/flatline/)
[![Downloads](https://img.shields.io/pepy/dt/flatline)](https://pepy.tech/projects/flatline)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://patacca.github.io/flatline/)
[![CI](https://github.com/patacca/flatline/actions/workflows/ci.yml/badge.svg)](https://github.com/patacca/flatline/actions/workflows/ci.yml)

Python wrapper around the Ghidra decompiler. Provides a stable, pip-installable
interface for single-function decompilation with structured output -- no Ghidra
installation required.

Named after Dixie Flatline from William Gibson's *Neuromancer* (1984) -- a dead
hacker's ROM construct, a consciousness extracted from hardware. In the same
spirit, flatline brings Ghidra's decompiler into library form for extracting
meaningful structure from binaries.

## Features

- **Single-function decompilation** -- pass a memory image, base address, and
  function entry point; get back structured C output with diagnostics.
- **Multi-ISA** -- x86 (32/64), ARM64, RISC-V 64, and MIPS32 are
  fixture-backed; all other Ghidra-supported architectures are available
  best-effort.
- **Enriched output** -- opt-in pcode IR with use-def edges and a
  `networkx.MultiDiGraph` projection for data-flow analysis.
- **Packaged runtime data** -- compiled Sleigh assets come from the companion
  `ghidra-sleigh` package. No vendored Ghidra tree at runtime.
- **Deterministic** -- repeated decompiles of the same input produce
  structurally equivalent output.

## Installation

```bash
pip install flatline
```

Pre-built wheels are published for Linux x86_64/aarch64, Windows x86_64, and
macOS x86_64/arm64 (Python 3.13+). If no wheel matches your platform, pip
falls back to a source build.

### Build from source

Source builds require a C++20 compiler, Ninja, and zlib headers:

| Platform | Install command |
|----------|----------------|
| Ubuntu/Debian | `sudo apt-get install g++ ninja-build zlib1g-dev` |
| Fedora/RHEL | `sudo dnf install gcc-c++ ninja-build zlib-devel` |
| Arch Linux | `sudo pacman -S gcc ninja zlib` |
| macOS | `brew install ninja zlib` (Xcode provides the C++ compiler) |
| Windows | Visual Studio with C++ workload; `pip install ninja`; `vcpkg install zlib:x64-windows` |

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
```

The native C++ extension is built automatically when a compiler is found. The
published wheels already include it. Without it the Python API is fully
importable, but decompile calls return a `configuration_error` result. See the
[installation guide](https://patacca.github.io/flatline/latest/installation/)
for native bridge build modes and troubleshooting.

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

Runtime data is auto-discovered from `ghidra-sleigh`. Pass
`runtime_data_dir=...` only when overriding the default root.

Flatline zero-fills decoder lookahead past the end of `memory_image` by
default (`tail_padding=b"\x00"`), so exact function slices work without
manual caller padding.

### Enriched output

Request `enriched=True` to get the post-simplification pcode IR:

```python
result = decompile_function(DecompileRequest(
    memory_image=raw_bytes,
    base_address=0x400000,
    function_address=0x401000,
    language_id="x86:LE:64:default",
    compiler_spec="gcc",
    enriched=True,
))

pcode = result.enriched.pcode
graph = pcode.to_graph()          # networkx.MultiDiGraph
op = pcode.get_pcode_op(op_id)    # O(1) lookup
vn = pcode.get_varnode(vn_id)     # O(1) lookup
```

See the [API reference](https://patacca.github.io/flatline/latest/reference/enriched/)
for the full enriched-output contract.

### Flatline X-Ray

`flatline-xray` is a shipped interactive pcode viewer for caller-provided
memory images:

```bash
flatline-xray --help
```

The viewer uses Ghidra's Sleigh disassembly natively, so no extra install is
needed for decoded instructions.

See the [X-Ray docs](https://patacca.github.io/flatline/latest/xray/) for
usage and tutorial.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

tox                                          # tests + lint
tox -e lint                                  # lint only
tox -e py313,py314 -- -m unit                # unit tests only
tox -e py313,py314 -- -m requires_native     # native-dependent tests
```

Tox test envs build and install wheels, so the suite exercises the packaged
artifact. Release and diagnostic helpers live under `tools/` and are excluded
from distribution artifacts.

### Building the docs locally

```bash
pip install -e ".[docs]"
PYTHONPATH=src mkdocs serve        # http://127.0.0.1:8000
```

Full documentation is at <https://patacca.github.io/flatline/>.

## Changelog

See [CHANGELOG.md](CHANGELOG.md). Release policy and support tiers are
documented in [docs/release_notes.md](docs/release_notes.md).

## Acknowledgments

This project was developed with the support of [Quarkslab](https://github.com/quarkslab).

## License

Apache-2.0. See [LICENSE](LICENSE) for the project license and [NOTICE](NOTICE)
for redistribution-time attribution.
