You are continuing an in-progress software project using the existing repo + prior chat context. **Repo docs/tests are authoritative** (override chat).

**Primary objective:** advance the **next roadmap item** and reflect progress via **concrete repo changes** (specs/docs, tests, code, tooling/deploy, roadmap). Keep repo internally consistent.

**If anything required to proceed is unclear, STOP and ask precise blocking questions before coding** (e.g., current failing tests, next roadmap step, target env, constraints, public APIs/contracts, code layout).

## Read first (authoritative)
- `docs/planning.md`
- `docs/specs.md`
- `docs/roadmap.md`
- `tests/**`
- `notes/api/decompiler_inventory.md` (decompiler/Python API contract)

## Deep reference (ONLY if repo docs/tests can’t resolve ambiguity/conflict)
- `third_party/ghidra/Ghidra/Features/Decompiler/src/decompile/cpp/**`
  - Use only to verify specific contract details.
  - If used: cite exact file paths + identifiers and update `notes/api/decompiler_inventory.md`.

## Rules
- Preserve scope, naming, structure; change only for correctness/consistency/testability.
- Revisit strategy/architecture **only** when the next roadmap step exposes a concrete blocker/inconsistency; propose the smallest fix.
- Prefer incremental diffs.
- If Rust: keep everything in **one source file** unless truly necessary.

## Workflow
1) **Extract baseline:** from `planning.md`, list deliverables/artifacts + acceptance criteria (tight bullets).
2) **Audit repo:** for each deliverable → `OK / Missing / Partial / Unclear` with file+section evidence and minimal fix.
3) **Consistency scan:** find drift/contradictions across planning/specs/roadmap/tests/inventory.
   - Classify: `Hard conflict / Soft inconsistency / Omission`
   - Provide evidence + one minimal resolution (or blocking question if needed).
4) **Next roadmap step (SDD + TDD):**
   - Update/append SDD only as needed: scope, assumptions, interfaces, data model, invariants, error model, ownership/lifetimes (if Rust), risks.
   - Write/adjust tests first (fail for the right reason).
   - Implement minimal code to pass; refactor with tests green.
   - Update specs/roadmap/inventory only when required by changes.

## Response format (concise, in order)
1) **Blocking questions** — each: why it matters + what decision it gates.
2) **Current status** — roadmap/spec/test alignment; key pass/fail signals (name tests/files).
3) **Issues / grey areas** — conflicts/drift + minimal proposed resolution.
4) **Next-step plan** — smallest effective steps (checklist).
5) **Changes** — unified diffs per file (tests + code + docs/SDD deltas), minimal and repo-conformant.
6) **Validation** — exact commands + expected “done” outcome.
7) **Non-blocking questions** — grouped by topic + potential impact (only if it could change conclusions).

End with a short proposed **git commit message**.