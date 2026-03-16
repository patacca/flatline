# Default-Install Footprint

## Scope

This document records flatline's current default-install footprint baseline for
P3 packaging/compliance hardening.

Measurement policy:
- Measure shipped payload files only.
- Exclude interpreter-generated `__pycache__` / `.pyc` files so the baseline
  stays stable across Python micro-version differences.
- Measure the default install as `flatline` plus its pinned runtime dependency
  `ghidra-sleigh`.
- Treat lighter runtime-data profiles such as `all_processors=false` as
  explicit user-managed overrides, not as silent default ISA pruning.

Reference command:
- `python tools/footprint.py`

Reference environment for the committed baseline:
- Date: `2026-03-15`
- Host: Linux x86_64
- Python: `3.14.3`
- Install shape: installed wheel in `.tox/py314`

## Current Baseline

Captured from `.tox/py314/bin/python tools/footprint.py`:

| Component | Bytes | MiB | Files | Notes |
| --- | ---: | ---: | ---: | --- |
| `flatline` distribution | `5,931,943` | `5.66` | `16` | Python package + native extension + dist-info payload |
| `ghidra-sleigh` distribution | `24,810,933` | `23.66` | `848` | Companion runtime-data package payload |
| `ghidra-sleigh` runtime data | `24,688,937` | `23.55` | `841` | Runtime-data subset inside the package |
| Combined default install | `30,742,876` | `29.32` | `864` | `flatline` + `ghidra-sleigh` payloads |

Runtime-data share of combined footprint: `80.3%`.

## Product Interpretation

- The default one-package UX remains acceptable at the current pinned baseline:
  combined payload is about `29.32 MiB`, and the bundled runtime data accounts
  for most of it.
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
