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
- **Multi-ISA** -- supports any Ghidra-supported target architecture. Priority
  fixture-backed confidence for x86 (32/64), ARM64, RISC-V 64, and MIPS32;
  other bundled ISAs remain best-effort.
- **Packaged runtime data** -- compiled Sleigh runtime assets come from the
  companion `ghidra-sleigh` package, so production installs do not depend on a
  vendored `third_party/ghidra` tree.
- **Deterministic** -- repeated decompiles of the same input produce
  structurally equivalent output.

## Requirements

- Python 3.13+
- Supported platforms: Linux x86_64/aarch64, Windows x86_64, macOS x86_64/arm64

## Installation

### Install from PyPI

```bash
pip install flatline
```

`pip install flatline` downloads a pre-built wheel when one is available.
Wheels are currently published for Linux x86_64/aarch64, Windows x86_64, and
macOS x86_64/arm64, so those installs do not need a local compiler or build
toolchain. If no wheel is available for your target, `pip` falls back to a
source build.

The platforms with published wheels are the supported platforms. Other
platforms may still work via a source build, but they are best effort.

### Build from source or install from a local checkout

Use this path when no pre-built wheel is available for your target, when you
want to install from a local checkout, or when you want to force a native
build.

Source builds require a C++20 compiler, Ninja, and zlib headers:

| Platform | Install command |
|----------|----------------|
| Ubuntu/Debian | `sudo apt-get install g++ ninja-build zlib1g-dev` |
| Fedora/RHEL | `sudo dnf install gcc-c++ ninja-build zlib-devel` |
| Arch Linux | `sudo pacman -S gcc ninja zlib` |
| macOS | `brew install ninja zlib` (Xcode provides the C++ compiler) |
| Windows | Visual Studio with C++ workload; `pip install ninja`; `vcpkg install zlib:x64-windows` |

Install from a local checkout:

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
```

For development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

`flatline` depends on `ghidra-sleigh` for its default runtime-data path, so
`DecompilerSession` and the one-shot wrappers auto-discover runtime data when
`runtime_data_dir` is omitted. `runtime_data_dir` remains available as an
explicit override for custom or reduced runtime-data roots.

### Native bridge

Real decompilation requires the native bridge -- a compiled C++ extension
(`flatline._flatline_native`) that links against the Ghidra decompiler library.
The published wheels already include this extension.
Without it the Python API is fully importable, but every `decompile_function`
call returns a `configuration_error` result. `list_language_compilers` still
returns runtime-data pairs discovered from the installed `ghidra-sleigh`
package.

The build has three modes, controlled by the `native_bridge` Meson option:

| Mode | How to set | Behaviour |
|------|------------|-----------|
| `auto` (default) | omit the flag | Builds the extension when a C++20 compiler and Ninja are found; silently falls back to the pure-Python stub otherwise. |
| `enabled` | `-Dnative_bridge=enabled` | Forces the native build; fails at install time if prerequisites are missing. Use this to validate the full decompilation stack. |
| `disabled` | `-Dnative_bridge=disabled` | Skips the native build entirely. All decompilation calls return `configuration_error`. |

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

Pass `runtime_data_dir=...` only when you need to override the dependency-backed
default runtime-data root.

Exact function slices do not need manual caller padding. Flatline zero-fills
decoder lookahead past the end of `memory_image` by default via
`tail_padding=b"\x00"`; set `tail_padding=None` or `tail_padding=b""` only
when you need strict tail-boundary failures.

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

`tox` test envs build and install `flatline[test]` wheels inside `.tox/`, so
the suite exercises the packaged artifact rather than `PYTHONPATH=src`.
Repo-only release and diagnostic helpers live under `tools/` and are
intentionally absent from wheel and sdist artifacts.

## Documentation

Documentation is available at <https://patacca.github.io/flatline/> or can be
built locally from this checkout.

Install the docs dependencies:

```bash
pip install -e ".[docs]"
```

**Local preview:**

```bash
PYTHONPATH=src mkdocs serve
```

Then open http://127.0.0.1:8000.

**Build static site:**

```bash
PYTHONPATH=src mkdocs build
```

Output goes to `site/`.

`PYTHONPATH=src` lets mkdocstrings import the pure-Python modules for API
reference generation without requiring a native build.

## Release Notes

Project history lives in [CHANGELOG.md](CHANGELOG.md). Update it for every
release using the Keep a Changelog structure already in the file.
The release-facing contract guarantees, support tiers, known-variant limits,
and upgrade policy for the public `0.1.x` line live in
[docs/release_notes.md](docs/release_notes.md).
The public artifact review checklist and manual approval hold point live in
[docs/release_review.md](docs/release_review.md).
Release publication workflow details live in
[docs/release_workflow.md](docs/release_workflow.md).
GitHub Actions release publishing lives in
[.github/workflows/release.yml](.github/workflows/release.yml): published
GitHub releases go to PyPI, while manual dispatch uploads to TestPyPI.
Manual TestPyPI dispatches require a unique version and now fail on duplicate
uploads instead of reusing an older TestPyPI artifact.
Redistribution/compliance guidance lives in [NOTICE](NOTICE) and
[docs/compliance.md](docs/compliance.md). The current default-install footprint
baseline and size-policy note live in [docs/footprint.md](docs/footprint.md).
The current P6 host-expansion feasibility record lives in
[docs/host_feasibility.md](docs/host_feasibility.md).

## Project status

The current public release is `0.1.1`. P6 and P6.5 are complete: supported
platforms are Linux x86_64/aarch64, Windows x86_64, and macOS x86_64/arm64.
P7 phase 1 has landed as opt-in enriched output.

Release-facing guarantees and support-policy notes live in
[docs/release_notes.md](docs/release_notes.md). `python tools/release.py`
audits the current release candidate, while
[docs/wheel_matrix.md](docs/wheel_matrix.md),
[docs/host_feasibility.md](docs/host_feasibility.md), and
[docs/roadmap.md](docs/roadmap.md) remain the source-of-truth phase documents.

## Acknowledgments

This project was developed with the support of [Quarkslab](https://github.com/quarkslab).

## License

Apache-2.0. See [LICENSE](LICENSE) for the project license and [NOTICE](NOTICE)
for redistribution-time attribution.
