# ghidralib — Project Memory

## What it is
Pip-installable Python wrapper around the Ghidra C++ decompiler, bundling runtime assets. Multi-ISA.

## Non-goals
- Not a general Ghidra automation framework; only exposes the decompiler surface.
- No UI, no project database management.

## Architecture (3-layer adapter)
1. **Public Contract** — Python request/result models, error taxonomy
2. **Bridge Contract** — translates public models ↔ native decompiler calls
3. **Upstream Adapter** — wraps Ghidra C++ callable surface

## Key files
- `docs/specs.md` — **SDD / source of truth**: API contract, data models, error taxonomy
- `docs/roadmap.md` — phases, milestones, risk register, ADR backlog
- `notes/api/decompiler_inventory.md` — required callable C++ symbols + post-decompilation contract
- `AGENTS.md` — live project status snapshot (update on every repo operation)

## Conventions
- **Spec-first / TDD:** test definitions precede code.
- **Error model:** Hard errors on invalid input; warnings on degraded success. No silent fallbacks.
- **All structured results are frozen value copies** — no native pointers cross the ABI boundary.
- **AGENTS.md must be updated** on every repo operation to reflect current state.
