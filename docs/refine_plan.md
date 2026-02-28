You are refining an EXISTING plan (previous iteration). Treat the repo’s current state as the latest output of that plan.

## Inputs (read first)
- `planning.md`, `specs.md`, `roadmap.md`, `tests/**`

## Extra reference (read ONLY if needed)
- `third_party/ghidra/Ghidra/Features/Decompiler/src/decompile/cpp/**`
  - Use only to confirm/resolve uncertainties or conflicts about *decompiler requirements* already claimed/assumed in the plan/specs/tests.
  - Cite exact file paths + identifiers (e.g., function/class) when used.

## Core rule
The prior deliverables + intent are the baseline. Do NOT invent a new plan. Regenerate the SAME deliverables as a consistent vNext with the smallest necessary changes.

## Tasks
1) **Baseline extraction**
   - From `planning.md`: list explicitly stated deliverables/artifacts + success/acceptance criteria.
   - These define the ONLY required outputs.

2) **Deliverables audit (repo vs baseline)**
   - For each baseline deliverable: Present / Missing / Partial / Unclear.
   - Include file + heading/section refs; for gaps, state minimal fix.

3) **Cross-file consistency**
   - Find contradictions/drift across `planning.md` ↔ `specs.md` ↔ `roadmap.md` ↔ `tests/**`.
   - Classify: Hard conflict / Soft inconsistency / Omission.
   - For each: evidence (file+section) + ONE best minimal fix.

4) **Architecture/strategy validation (within prior intent)**
   - Extract key prior decisions (boundaries, data flow, APIs, storage, invariants, testing strategy, security/perf assumptions) with evidence.
   - Flag grey areas/unstated assumptions that block implementation/testing.
   - Recommend minimal clarifications/adjustments (preserve intent).

5) **ADR-001 decision (must do)**
   - Locate ADR-001; extract context/options/constraints already present.
   - Decide ADR-001 (choose an option), add rationale, consequences, and follow-ups.
   - Ensure consistency with `planning.md`/`specs.md`/`roadmap.md`/`tests/**`.
   - If ADR-001 hinges on decompiler requirements and the repo docs are ambiguous/conflicting, verify ONLY the specific points in the Ghidra source folder above and cite paths/identifiers.

6) **Produce vNext deliverables (same set)**
   - Provide patch-style edits mapped to specific files/sections to update the EXISTING deliverables set.
   - Ensure acceptance criteria remain testable and roadmap sequencing stays coherent.

7) **Questions (only when blocking)**
   - If something is ambiguous/insufficient to proceed safely, ask targeted blocking questions.
   - Group by topic; say why each blocks. Otherwise proceed without questions.

## Output (strict order)
- **Summary** (≤8 bullets)
- **Deliverables Gap Audit** (table)
- **Inconsistencies & Grey Areas** (ranked, with evidence + minimal fix)
- **Architecture/Strategy Review** (evidence-based)
- **ADR-001 Decision** (decision + rationale + consequences + follow-ups; cite sources if checked)
- **Proposed Updates** (patch-style by file/section; minimal changes)
- **Blocking Questions** (only if truly blocking)