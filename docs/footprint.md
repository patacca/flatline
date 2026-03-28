# Default-Install Footprint

## Scope

This document records flatline's current default-install footprint baseline for
P3 packaging/compliance hardening.

Measurement policy:
- Measure shipped payload files only.
- Exclude interpreter-generated `__pycache__` / `.pyc` files so the baseline
  stays stable across Python micro-version differences.
- Measure the default install as `flatline` plus its default runtime dependency
  `ghidra-sleigh`.
- Treat lighter runtime-data profiles such as `all_processors=false` as
  explicit user-managed overrides, not as silent default ISA pruning.

Reference command:
- `python tools/footprint.py`

Reference environment for the committed baseline:
- Date: `2026-03-28`
- Host: Linux x86_64
- Python: `3.14.3`
- Install shape: editable install in `.venv`

## Current Baseline

Captured from `.tox/py314/bin/python tools/footprint.py`:

| Component | Bytes | MiB | Files | Notes |
| --- | ---: | ---: | ---: | --- |
| `flatline` distribution | `28,299` | `0.03` | `11` | Editable-install payload measured from the installed package metadata in `.venv` |
| `ghidra-sleigh` distribution | `24,810,838` | `23.66` | `847` | Companion runtime-data package payload |
| `ghidra-sleigh` runtime data | `24,688,937` | `23.55` | `841` | Runtime-data subset inside the package |
| Combined default install | `24,839,137` | `23.69` | `858` | `flatline` + `ghidra-sleigh` payloads |

Runtime-data share of combined footprint: `99.4%`.

## Product Interpretation

- The default one-package UX remains acceptable at the current pinned baseline:
  combined payload is about `23.69 MiB`, and the bundled runtime data accounts
  for nearly all of it.
- The current baseline does not justify changing the default asset profile.
- If future footprint growth makes the default unacceptable, any move to a
  reduced runtime-data build such as `all_processors=false` must be an explicit
  product/compliance decision recorded in the roadmap/specs, not silent default
  ISA pruning.

## Refresh Procedure

1. Install flatline into an environment that reflects the release artifact
   shape.
2. Run `python tools/footprint.py`.
3. Update this document when the measured values change because of packaging,
   native-binary, or runtime-data changes.
