# Overview
- Spec-first repository for a planned Python wrapper around the Ghidra decompiler.
- Current state is planning/testing artifacts only; no production library implementation yet outside vendored upstream code.

# Current baseline and policy
- Pinned upstream baseline: `Ghidra_12.0.3_build` at commit `09f14c92d3da6e5d5f6b7dea115409719db3cce1` (2026-02-10).
- MVP policy in docs: Linux first, `Python 3.13+`, latest-upstream-only support model.
- Public contract intent: stable Python API over potentially unstable upstream internals.

# Source of truth files
- Spec: `docs/specs.md`
- Delivery phases/gates/risks: `docs/roadmap.md`
- Discovery constraints and early stage experiment plan (already passed that stage): `docs/preplanning.md`
- Original writing brief/requirements: `docs/planning.md`

# Repo structure (non-vendored)
- `docs/`: architecture/spec/roadmap docs.
- `notes/api/`: decompiler callable-surface inventory.
- `notes/r2ghidra/`: integration mapping notes (reference only).
- `tests/`: definitions-only test plan and pytest skeletons.

# Tests status
- `tests/README.md` defines this tree as spec artifacts only.
- Pytest files are skeletons and currently marked skipped; no live native integration yet.
- Canonical test definitions/oracle strategy: `tests/specs/test_catalog.md` and `tests/specs/fixtures.md`.

# Vendored upstream trees
- `third_party/ghidra`: large upstream Ghidra source snapshot.
- `third_party/r2ghidra`: reference integration code and patches.
- Treat `third_party/*` as external upstream/reference unless explicitly asked to modify.
