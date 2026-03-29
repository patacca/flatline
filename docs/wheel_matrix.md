# Platform/Architecture Wheel Matrix

Canonical record: `docs/adr/adr-013.md`.

Status: GitHub CI and the `2026-03-28` TestPyPI rehearsal validated this
10-wheel-plus-sdist matrix end to end, and the same matrix reached production
PyPI later that day as `0.1.1`.

## Decision

Ship 64-bit CPython wheels for every Tier-1 host family we can build on
standard GitHub-hosted runners:

| Host family | Arch | Wheel tag family | GitHub runner |
| --- | --- | --- | --- |
| Linux | x86_64 | `manylinux_2_28_x86_64` | `ubuntu-latest` |
| Linux | aarch64 | `manylinux_2_28_aarch64` | `ubuntu-24.04-arm` |
| Windows | x86_64 | `win_amd64` | `windows-latest` |
| macOS | x86_64 | `macosx_*_x86_64` | `macos-15-intel` |
| macOS | arm64 | `macosx_*_arm64` | `macos-15` |

Python versions: CPython 3.13 and 3.14.

Per release, this yields 10 wheels plus 1 sdist.

## Why This Matrix

- It matches the current product direction: 64-bit only.
- It covers every Tier-1 host family flatline intends to support.
- GitHub-hosted runners currently provide native x64 Linux, arm64 Linux, x64
  Windows, Intel macOS, and arm64 macOS capacity.
- `cibuildwheel` supports the corresponding CPython 3.13/3.14 wheel tags.

## Policy Notes

- Linux wheels use the `manylinux_2_28` policy.
- macOS wheels keep `MACOSX_DEPLOYMENT_TARGET=11.0`.
- Wheel builds run the repo smoke script
  `tools/flatline_dev/wheel_smoke.py` through `cibuildwheel` so each built
  wheel must import, auto-discover `ghidra-sleigh`, and decompile the
  x86_64 `add(a,b)` fixture before publish.

## Deferred Targets

The following stay out of the locked matrix:

- 32-bit Linux and Windows wheels
- musllinux wheels
- Windows ARM64 wheels
- macOS universal2 wheels

These are deferred for demand or maintenance reasons, not because the public
API contract requires them.

## Decision Snapshot

ADR-013 is accepted with the following outcomes:

- Interpreter family: CPython only
- Python versions: `>= 3.13`, currently 3.13 and 3.14
- Build tool: `cibuildwheel`
- Locked wheel matrix: Linux x86_64 + Linux aarch64 + Windows x86_64 +
  macOS x86_64 + macOS arm64
- Linux policy: `manylinux_2_28`
- macOS deployment target: `11.0`
