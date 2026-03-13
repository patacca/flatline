---
name: step-roadmap
description: Advance the next roadmap item for the flatline project. Identify the next deliverable, audit repo consistency, write tests first, implement minimal code, and update docs. Use when the user says "advance the roadmap", "next step", "step", or wants to progress the project toward the next milestone.
---

# Step Roadmap

Advance the **next roadmap item** and reflect progress via **concrete repo changes** (specs/docs, tests, code, tooling/deploy, roadmap). Keep repo internally consistent.

**If anything required to proceed is unclear, STOP and ask precise blocking questions before coding.**

## Read first (authoritative, in priority order)

1. `CLAUDE.md` (current project state, conventions, build commands, ADR status)
2. `docs/specs.md` (SDD: API contract, data models, error model, cross-cutting concerns)
3. `docs/roadmap.md` (phases, milestones, risk register, ADR backlog)
4. `tests/specs/test_catalog.md` (test definitions, contract traceability matrix)
5. `tests/specs/fixtures.md` (fixture definitions, oracle strategy, determinism rules)
6. `tests/**/*.py` (pytest skeletons and passing tests)
7. `src/flatline/` (current implementation)

### Secondary reference
- `docs/planning.md` (original brief/requirements -- consult for intent, not current state)
- `notes/api/decompiler_inventory.md` (decompiler callable surface, init order, thread-safety)

### Deep reference (ONLY if repo docs/tests cannot resolve ambiguity)
- `third_party/ghidra/Ghidra/Features/Decompiler/src/decompile/cpp/**` -- verify specific native contract details only. If used: cite exact file paths + identifiers and update `notes/api/decompiler_inventory.md`.
- `third_party/r2ghidra/` -- reference integration only; do not replicate its patterns.

## Rules

- Preserve scope, naming, structure; change only for correctness/consistency/testability.
- Revisit strategy/architecture **only** when the next step exposes a concrete blocker; propose the smallest fix.
- Prefer incremental diffs over rewrites.
- All structured result objects are **frozen Python value types** -- no native pointers cross the bridge boundary.
- Error model: hard errors on invalid input; warnings on degraded success. No silent fallbacks.
- When an ADR resolves only the mechanism, keep deferred policy/versioning questions open in the backlog.
- Runtime-data packaging uses the external package `ghidra-sleigh` (import `ghidra_sleigh`).
- Keep `CLAUDE.md` updated after meaningful repo changes (state, test counts, new files).
- Always work inside the Python **venv** (`source .venv/bin/activate`).

## Workflow

1. **Identify next step:** from `docs/roadmap.md` phases/milestones + `CLAUDE.md` current state, determine the next concrete deliverable.
2. **Audit repo:** for each deliverable -> `OK / Missing / Partial / Unclear` with file+section evidence and minimal fix.
3. **Consistency scan:** find drift/contradictions across specs/roadmap/tests/inventory/code.
   - Classify: `Hard conflict / Soft inconsistency / Omission`
   - Provide evidence + one minimal resolution (or blocking question if needed).
4. **Next roadmap step (SDD + TDD):**
   - Update/append specs only as needed: scope, assumptions, interfaces, data model, invariants, error model, risks.
   - Write/adjust tests first (fail for the right reason).
   - Implement minimal code to pass; refactor with tests green.
   - Update specs/roadmap/inventory/CLAUDE.md only when required by changes.

## Validation

```bash
source .venv/bin/activate
tox                                    # full: tests + lint
tox -e py313 -- -m unit                # single category
tox -e lint                            # lint only
```

## Response format (concise, in order)

1. **Blocking questions** -- each: why it matters + what decision it gates.
2. **Current status** -- roadmap/spec/test alignment; key pass/fail signals (name tests/files).
3. **Issues / grey areas** -- conflicts/drift + minimal proposed resolution.
4. **Next-step plan** -- smallest effective steps (checklist).
5. **Changes** -- unified diffs per file (tests + code + docs/SDD deltas), minimal and repo-conformant.
6. **Validation** -- exact commands + expected "done" outcome.
7. **Non-blocking questions** -- grouped by topic + potential impact (only if it could change conclusions).

End with a proposed **git commit message** (first line within 50 characters, additional context in subsequent lines).
