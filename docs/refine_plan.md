You are reviewing and refining an EXISTING plan (previous iteration). Treat the current repo state as the plan’s latest output.

Inputs (only): `planning.md`, `specs.md`, `roadmap.md`, and `tests/**`.

Core rule: The previously elaborated plan + its deliverables are the baseline. Your job is to (a) verify those deliverables exist and match intent, and (b) regenerate the SAME deliverables as an updated, consistent vNext (not a new plan), applying minimal necessary changes.

Do:

1) Baseline extraction (`planning.md`)
- Extract the plan’s stated deliverables/artifacts and success criteria (explicitly listed).
- Use these as the ONLY required outputs to reproduce.

2) Deliverables audit (repo vs baseline)
- For each deliverable from (1): Present / Missing / Partial / Unclear with file+section refs.
- For Missing/Partial: specify minimal fixes/additions to bring it to spec.

3) Cross-file consistency check
- Identify contradictions/drift across `planning.md` ↔ `specs.md` ↔ `roadmap.md` ↔ `tests/**`.
- Classify: Hard conflict / Soft inconsistency / Omission.
- For each: cite evidence (file+section) and propose ONE best minimal fix.

4) Architecture/strategy validation (within existing plan)
- List key prior decisions (boundaries, data flow, APIs, storage, invariants, testing strategy, security/perf assumptions) as evidenced in files.
- Check alignment with requirements + tests; flag grey areas/unstated assumptions that block implementation or testing.
- Recommend minimal clarifications/adjustments (preserve prior intent).

5) Produce vNext deliverables (same set as baseline)
- Output patch-style edits mapped to specific files/sections to update the EXISTING deliverables set.
- Ensure acceptance criteria are testable and roadmap sequencing remains coherent.

6) Questions (only when blocking)
- Ask targeted questions ONLY when required to avoid guessing.
- Group by topic; explain why each is blocking. Do not invent requirements.

Output (strict):
- Summary (<=8 bullets)
- Deliverables Gap Audit (table)
- Inconsistencies & Grey Areas (ranked)
- Architecture/Strategy Review
- Proposed Updates (patch-style by file/section)
- Blocking Questions