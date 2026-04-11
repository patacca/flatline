You are refining an EXISTING plan (previous iteration). Treat the repo's current state as the latest output of that plan. Do **not** create a new plan; regenerate the **same deliverables** as a consistent vNext with the smallest necessary changes.

## Inputs (read first)
- `planning.md`, `specs.md`, `roadmap.md`, `tests/**`
- `notes/api/decompiler_inventory.md` (decompiler/Python API contract)

## Extra reference (read ONLY if needed to resolve uncertainty/conflict)
- `third_party/ghidra/Ghidra/Features/Decompiler/src/decompile/cpp/**`
  - Use only to verify specific decompiler-contract details that are ambiguous/contradictory in repo docs/tests.
  - When used, cite exact file paths + identifiers (class/function/symbol) and update the contract details in `notes/api/decompiler_inventory.md`.

## Core rule
Prior deliverables + intent are the baseline and the only required outputs. Preserve scope, naming, and structure unless a minimal change is required for consistency/testability.

## Tasks
1) **Baseline extraction**
   - From `planning.md`: enumerate deliverables/artifacts + explicit success/acceptance criteria.

2) **Deliverables audit (repo vs baseline)**
   - For each deliverable: Present / Missing / Partial / Unclear.
   - Cite file + heading/section; for gaps, propose the minimal fix.

3) **Cross-file consistency**
   - Detect contradictions/drift across `planning.md` ↔ `specs.md` ↔ `roadmap.md` ↔ `tests/**` ↔ `notes/api/decompiler_inventory.md`.
   - Classify: Hard conflict / Soft inconsistency / Omission.
   - For each: evidence (file+section) + ONE minimal fix.

4) **Architecture/strategy validation (within prior intent)**
   - Extract key prior decisions (boundaries, data flow, APIs, invariants, testing strategy, security/perf assumptions) with evidence.
   - Flag grey areas/unstated assumptions that could break implementation/testing.
   - Recommend minimal clarifications/adjustments (preserve intent).

5) **Expand the stable Python interface (structured results)**
   - Using `notes/api/decompiler_inventory.md` as the contract baseline, propose an incremental vNext that returns *structured objects* (not only C text), while keeping compatibility.
   - Define the objects (fields/types), error model, and ownership/lifetime rules (as relevant).
   - Map each new object/field to: (a) a concrete consumer need in plan/specs/tests, and (b) a decompiler capability per the inventory; verify in Ghidra sources ONLY if the inventory/docs/tests are unclear.
   - **The definition of the structured objects exposed by the contract baseline is a P0 requirement.** The roadmap must include it as an exit criterion for P0 (Spec lock), not deferred to later phases.
   - Update/extend tests and docs minimally to lock behavior.

6) **Produce vNext deliverables (same set)**
   - Provide patch-style edits mapped to specific files/sections to update the EXISTING deliverables set.
   - Keep acceptance criteria testable and roadmap sequencing coherent.
   - Ensure the roadmap P0 exit criteria include the structured-object definitions from Task 5 (fields, types, error model, ownership/lifetime).

7) **Questions / clarifications**
   - If anything is ambiguous (even if not fully blocking) and could change conclusions, ask targeted questions.
   - Group by topic; include why it matters and what decision it affects. Otherwise proceed.

## Output (strict order)
- **Summary** (≤8 bullets)
- **Deliverables Gap Audit** (table)
- **Inconsistencies & Grey Areas** (ranked; evidence + minimal fix)
- **Architecture/Strategy Review** (evidence-based)
- **Python Interface Expansion** (proposed objects + compatibility + tests/docs impact; cite sources if checked)
- **Proposed Updates** (patch-style by file/section; minimal changes)
- **Questions** (only if applicable)
