# Host Feasibility

This document records the evidence that closed the P6 host-expansion work and
feeds the remaining P6.5 public-publish step. Linux x86_64, macOS arm64, and
Windows x86_64 now meet the supported runtime-host bar. Linux aarch64 and
macOS x86_64 remain published-wheel targets until they gain dedicated
continuous host lanes.

## Current Audit

| Surface | Status | Notes |
| --- | --- | --- |
| `src/flatline/_session.py`, `src/flatline/_bridge.py`, `src/flatline/_runtime_data.py` | OK | Pure-Python request/session/runtime-data paths already use `Path`/`fspath` and do not depend on Linux-only APIs. |
| `src/flatline/meson.build` | OK | Shared native-build settings now resolve compiler-family warning/visibility flags directly in Meson, express staged nanobind headers via Meson include directories instead of raw `-I` / `/I` arguments, auto-discover Homebrew `zlib` on macOS, and auto-discover vcpkg `zlib` on Windows via `VCPKG_INSTALLATION_ROOT` without manual `CPPFLAGS` / `LDFLAGS` / `PKG_CONFIG_PATH` exports. Apple Clang and MSVC compilation are continuously exercised by CI and the release wheel matrix. |
| `src/flatline/_flatline_native.cpp` | OK | Standard C++20 plus zlib-backed upstream sources. Apple Clang and MSVC compilation plus native decompile behavior are now validated by dedicated contract lanes, while the release matrix also validates Linux aarch64 and Intel macOS wheel installs from published artifacts. |
| `.github/workflows/ci.yml` | OK | CI includes a dedicated macOS arm64 contract lane (`macos-15`, Python `3.14`) and a dedicated Windows x86_64 contract lane (`windows-latest`, Python `3.14`), both running `tox -e py314-native -- -m "not regression"` with `native_bridge=enabled`, so the installed-wheel contract matrix exercises the real native bridge on each host without manual compiler/linker flag exports. |
| `tests/fixtures/*.hex` and native regression fixtures | OK | Committed runtime fixtures are host-neutral test inputs. Their generation recipes use Linux-target cross toolchains, but that is maintainer-only fixture production rather than an end-user runtime dependency. |
| `ghidra-sleigh` dependency path | OK | The companion package currently publishes `ghidra-sleigh 12.0.4` as a `py3-none-any` wheel, so the macOS and Windows contract lanes plus the Tier-1 published-wheel smoke matrix can all install runtime data without introducing a host-specific packaging branch in flatline. |

## Current Status

- Supported runtime hosts: Linux x86_64, macOS arm64, Windows x86_64.
- Published-wheel-only targets: Linux aarch64, macOS x86_64.
- Evidence: `.github/workflows/ci.yml` keeps the dedicated macOS arm64 and
  Windows x86_64 native contract lanes green, and release workflow run
  `23694378228` on `2026-03-28` published `flatline 0.1.1.dev1` to TestPyPI,
  uploaded 10 wheels plus 1 sdist, and passed the full post-publish smoke
  matrix.
- Remaining P6.5 step: first production PyPI publish of the same Tier-1 wheel
  set.

## Decision Summary

Canonical record: `docs/adr/adr-008.md`.

Accepted order: macOS first, Windows second. This document records the current
feasibility evidence and support-promotion state that followed from that
decision.

## Equivalent Contract Coverage

A host is not considered feasible enough to promote into release-facing support
notes until it has equivalent contract coverage:

- source and wheel install paths complete with the native bridge enabled
- `DecompilerSession` startup, pair enumeration, and native decompile behavior
  match the existing public contract
- the committed fixture-backed matrix and negative tests run on that host
- CI contains a dedicated host lane proving the behavior continuously
- release notes and support messaging are updated in the same change set

Current promotion result:

- macOS arm64 and Windows x86_64 now satisfy this bar.
- Linux aarch64 and macOS x86_64 do not yet because the repo does not keep
  dedicated continuous source-install contract lanes for those targets.

## Remaining Follow-up

1. Keep the dedicated macOS arm64 and Windows x86_64 contract lanes green so
   the supported runtime-host promotions remain continuously proven.
2. Keep Linux aarch64 and macOS x86_64 labeled as published-wheel targets only
   until they gain dedicated equivalent-contract lanes.
3. Use the validated release workflow for the first production PyPI publish of
   the Tier-1 wheel set.
