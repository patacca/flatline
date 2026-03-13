You are continuing an in-progress software project using the existing repo + prior chat context. **Repo docs/tests are authoritative** (override chat).

**Primary objective:** advance the **next roadmap item** and reflect progress via **concrete repo changes** (specs/docs, tests, code, tooling/deploy, roadmap). Keep repo internally consistent.

**If anything required to proceed is unclear, STOP and ask precise blocking questions before coding** (e.g., current failing tests, next roadmap step, constraints, public APIs/contracts, code layout).

## Read first (authoritative, in priority order)
- `AGENTS.md` (current project state, conventions, build commands, ADR status)
- `docs/specs.md` (SDD: API contract, data models, error model, cross-cutting concerns)
- `docs/roadmap.md` (phases, milestones, risk register, ADR backlog)
- `tests/specs/test_catalog.md` (test definitions, contract traceability matrix)
- `tests/specs/fixtures.md` (fixture definitions, oracle strategy, determinism rules)
- `tests/**/*.py` (pytest skeletons and passing tests)
- `src/flatline/` (current implementation)

## Secondary reference
- `docs/planning.md` (original brief/requirements — consult for intent, not current state)
- `notes/api/decompiler_inventory.md` (decompiler callable surface, init order, thread-safety)

## Deep reference (ONLY if repo docs/tests can't resolve ambiguity/conflict)
- `third_party/ghidra/Ghidra/Features/Decompiler/src/decompile/cpp/**`
  - Use only to verify specific native contract details (function signatures, struct layouts, enums).
  - If used: cite exact file paths + identifiers and update `notes/api/decompiler_inventory.md`.
- `third_party/r2ghidra/` — reference integration only; do not replicate its patterns.

## Rules
- Preserve scope, naming, structure; change only for correctness/consistency/testability.
- Revisit strategy/architecture **only** when the next roadmap step exposes a concrete blocker/inconsistency; propose the smallest fix.
- Prefer incremental diffs over rewrites.
- All structured result objects are **frozen Python value types** — no native pointers cross the bridge boundary.
- Error model: hard errors on invalid input; warnings on degraded success. No silent fallbacks.
- When an ADR resolves only the mechanism, keep any deferred policy/versioning questions open in the backlog instead of marking them fully resolved.
- Runtime-data packaging uses the external package `ghidra-sleigh` (import `ghidra_sleigh`).
- Keep `AGENTS.md` updated after meaningful repo changes (state, test counts, new files).
- Always work inside the Python **venv** (`source .venv/bin/activate`).

## Architecture context (3-layer adapter)
1. **Public Contract** — Python request/result models, error taxonomy.
2. **Bridge Contract** — nanobind C++ extension module (ADR-002); translates public models ↔ native calls. Unstable internal.
3. **Upstream Adapter** — wraps Ghidra C++ callable surface; changes absorb upstream drift.

## Workflow
1) **Identify next step:** from `docs/roadmap.md` phases/milestones + `AGENTS.md` current state, determine the next concrete deliverable.
2) **Audit repo:** for each deliverable in the current step → `OK / Missing / Partial / Unclear` with file+section evidence and minimal fix.
3) **Consistency scan:** find drift/contradictions across specs/roadmap/tests/inventory/code.
   - Classify: `Hard conflict / Soft inconsistency / Omission`
   - Provide evidence + one minimal resolution (or blocking question if needed).
4) **Next roadmap step (SDD + TDD):**
   - Update/append specs only as needed: scope, assumptions, interfaces, data model, invariants, error model, risks.
   - Write/adjust tests first (fail for the right reason).
   - Implement minimal code to pass; refactor with tests green.
   - Update specs/roadmap/inventory/AGENTS.md only when required by changes.

## Validation commands
- `source .venv/bin/activate` (always first)
- `tox` (full: tests + lint across Python versions)
- `tox -e py313 -- -m unit` (single category: `unit`, `contract`, `integration`, `regression`, `negative`)
- `tox -e lint`

## Response format (concise, in order)
1) **Blocking questions** — each: why it matters + what decision it gates.
2) **Current status** — roadmap/spec/test alignment; key pass/fail signals (name tests/files).
3) **Issues / grey areas** — conflicts/drift + minimal proposed resolution.
4) **Next-step plan** — smallest effective steps (checklist).
5) **Changes** — unified diffs per file (tests + code + docs/SDD deltas), minimal and repo-conformant.
6) **Validation** — exact commands + expected "done" outcome.
7) **Non-blocking questions** — grouped by topic + potential impact (only if it could change conclusions).

End with a proposed **git commit message**. Try to fit the first line within 50 characters, you can add additional context in subsequent lines.
