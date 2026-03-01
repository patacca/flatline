You are documenting the **native Ghidra decompiler (C++) decompilation API contract** for a **standalone wrapper library**.

## Mandatory upstream pin
Work **only** against:
- Tag: `Ghidra_12.0.3_build`
- Commit: `09f14c92d3da6e5d5f6b7dea115409719db3cce1` (tag date `2026-02-10`)

For every factual claim, cite **(file path + class/function/symbol)** and **line numbers when practical**. If something depends on build flags or runtime config, say so.

## Inputs (read first)
- `notes/api/decompiler_inventory.md`
- `notes/r2ghidra/integration_map.md`

## First task: audit & correct previous iteration
Before adding new material, **review what’s already written** in the above notes and:
- fix incorrect names/types/ownership statements
- add missing citations
- remove duplicates / speculative statements
- ensure consistency of terminology (class names, ownership language, “IR/P-code”, etc.)

## Goal
Update the notes to precisely describe **what objects exist after a successful decompile** (and what is reachable from them) and **what they expose**, including:
- C/text output
- **IR/P-code** (important even if wrapper may expose it later)
- symbols/vars, scopes
- types/datatype model
- address ↔ range mappings (original ↔ IR/text where available)
- diagnostics: warnings/errors/status, timeouts/budgets if present

This is not just “what the decompiler prints”: define the **contract with the decompiler library** (result objects, APIs, and lifetimes) as a wrapper author would rely on.

C++ ABI exposure is acceptable; still classify APIs as:
- **safe-ish to expose** (stable-ish surface)
- **internal/fragile** (likely to change; avoid binding unless needed)

## Scope & trace requirements
Focus on objects **returned or reachable after decompilation completes** from the **native entrypoint(s)**. Include minimal setup/teardown only when necessary to explain **ownership/lifetime** of the post-decompile objects. Avoid unrelated program-loading architecture unless it directly affects result validity.

From the pinned revision, trace the call path and enumerate:
- decompile entry API(s) / native boundary
- result container(s)
- IR/function representation (ops/nodes/blocks; traversal; P-code/SSA forms if present)
- printers/output buffers/streams for C/text
- diagnostics/warnings/errors/status surfaces
- reachable supporting objects (varnodes, ops, symbols, types, comments, address maps, etc.)

## Required deliverable: “Post-decompilation contract”
Edit `notes/api/decompiler_inventory.md` to add/replace a section:

### Post-decompilation contract
For each category below, list **classes + key methods** with:
- role (1 line)
- extractable data (explicit)
- extraction API: `Class::method(params) -> ret` (exact types where possible)
- ownership/lifetime: who allocates/frees; validity window; what invalidates refs/iterators; reset/reuse rules
- diagnostics surfaces: flags/status objects/return codes/exceptions/log buffers; how warnings appear
- thread-safety constraints (only what code/docs support; avoid guesswork)
- MVP relevance: `required` / `optional` / `ignore`

Minimum categories:
1) Entrypoints & result container
2) C/text output generation
3) Function IR graph (P-code/ops/blocks/nodes; traversal/iteration)
4) Symbols & variables (naming, storage, scopes)
5) Types / datatype model (ownership + where recovered types live)
6) Address/range mapping (IR/text ↔ original addresses)
7) Diagnostics (warnings/errors/timeouts/budgets)

Prefer **short tables** per category; use bullets only for tricky semantics.

## r2ghidra cross-check (only if needed)
Update `notes/r2ghidra/integration_map.md` only if necessary to:
- record exact extraction steps it uses (C text, warnings, etc.)
- map each step to the contract (“uses `X::Y()` to get Z”)
- mark reusable vs wrapper-specific logic

## Output requirements
Produce edits **directly** in:
- `notes/api/decompiler_inventory.md`
- `notes/r2ghidra/integration_map.md` (only if necessary)

In your response include:
1) brief change summary
2) the updated file content **or** a unified diff per file (choose the more concise that stays unambiguous)
3) a structured list of the final contract items (classes/functions) **exactly as written in the notes**

## Questions
If anything is blocking/ambiguous, ask **targeted** questions (max 5) before guessing.