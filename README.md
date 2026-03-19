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
  fixture-backed confidence for x86 (32/64), ARM64, RISC-V 64, and MIPS32;
  other bundled ISAs remain best-effort.
- **Packaged runtime data** -- compiled Sleigh runtime assets come from the
  companion `ghidra-sleigh` package, so production installs do not depend on a
  vendored `third_party/ghidra` tree.
- **Deterministic** -- repeated decompiles of the same input produce
  structurally equivalent output.

## Requirements

- Python 3.13+
- Supported runtime host contract: Linux x86_64
- Published wheels: Linux x86_64/aarch64, Windows x86_64, macOS x86_64/arm64
- C++20 compiler (for source builds or forced native builds)
- Ninja (for source builds or forced native builds)

## Installation

```bash
pip install flatline
```

`pip install flatline` uses pre-built wheels on Linux x86_64/aarch64, Windows
x86_64, and macOS x86_64/arm64, so those installs work without a local
compiler. Platforms outside that wheel matrix fall back to source builds and
therefore need a C++20 compiler plus Ninja.

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
Without it the Python API is fully importable, but every `decompile_function`
call returns a `configuration_error` result.  `list_language_compilers` still
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

## Release Notes

Project history lives in [CHANGELOG.md](CHANGELOG.md). Update it for every
release using the Keep a Changelog structure already in the file.
The release-facing contract guarantees, support tiers, known-variant limits,
and upgrade policy for the first public release live in
[docs/release_notes.md](docs/release_notes.md).
The public artifact review checklist and manual approval hold point live in
[docs/release_review.md](docs/release_review.md).
The initial public release workflow and the `0.1.0` SemVer recommendation live
in [docs/release_workflow.md](docs/release_workflow.md).
GitHub Actions release publishing lives in
[.github/workflows/release.yml](.github/workflows/release.yml): published
GitHub releases go to PyPI, while manual dispatch uploads to TestPyPI.
Redistribution/compliance guidance lives in [NOTICE](NOTICE) and
[docs/compliance.md](docs/compliance.md). The current default-install footprint
baseline and size-policy note live in [docs/footprint.md](docs/footprint.md).
The current P6 host-expansion feasibility record lives in
[docs/host_feasibility.md](docs/host_feasibility.md).

## Project status

The `0.1.0` MVP release is available. P5 initial public release is complete,
with release-facing guarantees and support-policy notes captured in
[docs/release_notes.md](docs/release_notes.md) and the release/tag procedure
recorded in [docs/release_workflow.md](docs/release_workflow.md). The manual
artifact-review gate remains documented in [docs/release_review.md](docs/release_review.md)
for future reference. The current roadmap focus is the P6.5 wheel distribution
matrix, with the locked Tier-1 wheel set recorded in
[docs/wheel_matrix.md](docs/wheel_matrix.md) while host-promotion evidence
continues in [docs/host_feasibility.md](docs/host_feasibility.md). See
[docs/roadmap.md](docs/roadmap.md) for the phase plan.

## License

Apache-2.0. See [LICENSE](LICENSE) for the project license and [NOTICE](NOTICE)
for redistribution-time attribution.
