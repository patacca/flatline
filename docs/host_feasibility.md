# Host Feasibility

This document records the active P6 deliverables: a source-controlled audit of
the post-`0.1.0` host-expansion path and the dedicated macOS CI lane that now
forces the native bridge and runs the existing non-regression tox matrix. It
does not change the public release contract for `0.1.0`; Linux
x86_64 remains the only supported host until a new host reaches equivalent
contract coverage.

## Current Audit

| Surface | Status | Notes |
| --- | --- | --- |
| `src/flatline/_session.py`, `src/flatline/_bridge.py`, `src/flatline/_runtime_data.py` | OK | Pure-Python request/session/runtime-data paths already use `Path`/`fspath` and do not depend on Linux-only APIs. |
| `src/flatline/meson.build` | Partial | Shared native-build settings now resolve compiler-family warning/visibility flags directly in Meson, express staged nanobind headers via Meson include directories instead of raw `-I` / `/I` arguments, and auto-discover Homebrew `zlib` on macOS without manual `CPPFLAGS` / `LDFLAGS` / `PKG_CONFIG_PATH` exports. Windows/MSVC feasibility still needs empirical validation. |
| `src/flatline/_flatline_native.cpp` | Unclear | The adapter is standard C++20 plus zlib-backed upstream sources, but native compilation still needs empirical validation on Apple Clang and on a Windows toolchain. |
| `.github/workflows/ci.yml` | OK | CI now includes a dedicated macOS contract lane (currently `macos-15`) on Python `3.14` that runs `tox -e py314-native -- -m "not regression"` with `native_bridge=enabled`, so the installed-wheel contract matrix exercises the real native bridge on macOS without manual compiler/linker flag exports. |
| `tests/fixtures/*.hex` and native regression fixtures | OK | Committed runtime fixtures are host-neutral test inputs. Their generation recipes use Linux-target cross toolchains, but that is maintainer-only fixture production rather than an end-user runtime dependency. |
| `ghidra-sleigh` dependency path | OK | The companion package currently publishes `ghidra-sleigh 12.0.4` as a `py3-none-any` wheel, so the macOS feasibility lane can install runtime data without introducing a host-specific packaging branch in flatline. |

## ADR-008 Decision

Decision: macOS first, Windows second.

Rationale:

1. The current native stack is Meson + nanobind + Ghidra C++ sources + zlib.
   Apple Clang and macOS keep the same general POSIX/process model and
   GCC-like compiler-argument syntax as the Linux MVP host, so they are the
   shortest path to the first non-Linux feasibility proof.
2. Windows adds a second layer of work: MSVC-style argument syntax, ABI
   validation, and runner/toolchain variance that the roadmap already tracks as
   a separate risk.
3. P6 should remove shared blockers once, then validate equivalent behavior on
   the closest host before taking on the Windows-specific tail work.

## Equivalent Contract Coverage

A host is not considered feasible enough to promote into release-facing support
notes until it has equivalent contract coverage:

- source and wheel install paths complete with the native bridge enabled
- `DecompilerSession` startup, pair enumeration, and native decompile behavior
  match the existing public contract
- the committed fixture-backed matrix and negative tests run on that host
- CI contains a dedicated host lane proving the behavior continuously
- release notes and support messaging are updated in the same change set

## Immediate P6 Steps

1. Keep `src/flatline/meson.build` and the native-forced tox env host-aware so
   shared native-build paths do not fail before host-specific feasibility work
   even begins, and keep low-level compiler/linker flag plumbing out of the
   user-facing install path.
2. Keep the dedicated macOS contract lane green long enough to treat it as
   the standing non-Linux feasibility signal before updating support notes.
3. Open a Windows-specific feasibility spike only after macOS closes the shared
   Meson/build assumptions and sustains the first non-Linux native contract
   pass.
