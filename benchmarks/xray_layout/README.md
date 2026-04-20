# xray Layout Library Benchmark

> **WARNING: DO NOT MERGE TO MAIN** — This is a throwaway research branch.
> All findings live in `out/REPORT.md` and inform future work, not this codebase.

## Purpose

Data-driven evaluation of orthogonal layout libraries as candidates to replace
xray's custom placement+routing algorithm. Candidates: libavoid, HOLA, OGDF,
DOMUS, OGDF+libavoid combo.

## Installation

### Prerequisites

- Python 3.13+
- gcc
- Cairo system library (required by cairosvg):
  - Ubuntu/Debian: `sudo apt-get install libcairo2-dev`
  - Fedora/RHEL: `sudo dnf install cairo-devel`
  - macOS: `brew install cairo`

### Setup

Run the idempotent setup script from the repo root:

```bash
./benchmarks/xray_layout/setup.sh
```

This creates `.venv-bench/` in the benchmark directory (separate from the main flatline `.venv/`).

Activate the environment:

```bash
source benchmarks/xray_layout/.venv-bench/bin/activate
```

Verify the installation:

```bash
python -c "import flatline, networkx, jsonschema, cairosvg, PIL; print('OK')"
```

Run the benchmark check:

```bash
python -m benchmarks.xray_layout.bench check
```

**Note:** This virtual environment is intentionally separate from the main flatline `.venv/`.

## Branch Policy

This branch (`bench/xray-layout-comparison`) is a throwaway research artifact.
It MUST NOT be merged to main. The benchmark harness lives entirely under
`benchmarks/xray_layout/` with zero diff against main outside this directory.
