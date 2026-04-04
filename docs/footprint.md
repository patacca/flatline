# Default-Install Footprint

## Scope

This document records flatline's current default-install footprint baseline for
P3 packaging/compliance hardening.

Measurement policy:
- Measure shipped payload files only.
- Exclude interpreter-generated `__pycache__` / `.pyc` files so the baseline
  stays stable across Python micro-version differences.
- Measure the default install as `flatline` plus its runtime dependencies
  `networkx` and `ghidra-sleigh`.
- Treat lighter runtime-data profiles such as `all_processors=false` as
  explicit user-managed overrides, not as silent default ISA pruning.

Reference command:
- `python tools/footprint.py`

Reference environment for the committed baseline:
- Date: `2026-04-04`
- Host: Linux x86_64
- Python: `3.14.3`
- Install shape: installed wheel in `.tox/py314`

## Current Baseline

Captured from `.tox/py314/bin/python tools/footprint.py`:

| Component | Bytes | MiB | Files | Notes |
| --- | ---: | ---: | ---: | --- |
| `flatline` distribution | `6,260,321` | `5.97` | `31` | Installed wheel payload including the native extension and shipped `flatline.xray` modules in `.tox/py314` |
| `networkx` distribution | `7,081,035` | `6.75` | `603` | Graph-projection dependency payload required by `Pcode.to_graph()` |
| `ghidra-sleigh` distribution | `24,810,933` | `23.66` | `848` | Companion runtime-data package payload |
| `ghidra-sleigh` runtime data | `24,688,937` | `23.55` | `841` | Runtime-data subset inside the package |
| Combined default install | `38,152,289` | `36.38` | `1,482` | `flatline` + `networkx` + `ghidra-sleigh` payloads |

Runtime-data share of combined footprint: `64.7%`.

## Product Interpretation

- The current default-install baseline is about `36.38 MiB`, and the bundled
  runtime data still accounts for most of it.
- The non-runtime share is materially higher than the earlier baseline because
  the installed wheel now includes the native extension and the public graph
  projection depends on `networkx`.
- Shipping `flatline.xray` adds a small pure-Python increase to the default
  install without changing the dependency baseline.
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
