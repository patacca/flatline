You are documenting the **post-decompilation API contract** of the **Ghidra native decompiler (C++)** for a standalone wrapper library.

## Upstream pin (mandatory)
Work **only** against:
- Tag: `Ghidra_12.0.3_build`
- Commit: `09f14c92d3da6e5d5f6b7dea115409719db3cce1` (tag date `2026-02-10`)
Every claim must reference this pin (file path + symbol; line numbers if practical). Any later upgrade requires a revalidation pass.

## Inputs (read first)
- `notes/api/decompiler_inventory.md`
- `notes/r2ghidra/integration_map.md`

## Goal
Update the notes to precisely describe **what objects exist after a successful decompile** and **what they expose**: C output, **IR/P-code** (important even if later exposure is optional), symbols/vars, types, address/range mapping, diagnostics.

C++ ABI exposure is acceptable; still document which classes are “safe-ish to expose” vs internal/fragile.

## Scope
Focus on objects **returned or reachable after decompilation completes** from the native entrypoint(s). Avoid unrelated program-loading architecture unless needed to explain **ownership/lifetime**.

## What to trace
From the pinned revision, trace the decompile call path and enumerate result objects:
- decompile entry API(s)
- result container type(s)
- IR/function representation (ops/nodes/blocks; iteration APIs; P-code/SSA forms if present)
- C/text output generation (printers, streams/buffers)
- diagnostics/warnings/errors (incl. timeouts/budgets if present)
- supporting reachable objects (varnodes/ops/types/symbols/comments/address maps/etc.)

## Required deliverable: “Post-decompilation contract”
Edit `notes/api/decompiler_inventory.md` to add/replace:

### Post-decompilation contract
For each category below, list **classes + key methods** with:
- semantic role
- extractable data (exact)
- extraction method(s): function name + key params/return types
- ownership/lifetime (alloc/free; validity window; reset/reuse; what invalidates iterators/refs)
- diagnostics surfaces (status/flags/exceptions/log buffers; how warnings appear)
- thread-safety caveats (document constraints; don’t over-speculate)
- MVP relevance: `required` / `optional` / `ignore`

Minimum categories:
1) Entrypoints & result container
2) C/text output generation
3) Function IR graph (P-code/ops/blocks/nodes; traversal/iteration)
4) Symbols & variables (naming, storage, scopes)
5) Types / datatype model (recovered types location/ownership)
6) Address/range mapping (IR ↔ original addresses)
7) Diagnostics (warnings/errors/timeouts/budgets)

Prefer short tables per category + brief bullets only for tricky semantics.

## r2ghidra cross-check
Update `notes/r2ghidra/integration_map.md` **only if needed** to:
- record exact extraction steps it uses (C text, warnings, etc.)
- map each step to the contract (“uses `X::Y()` to get Z”)
- mark reusable vs wrapper-specific logic

## Output requirements
- Write edits **directly** into:
  - `notes/api/decompiler_inventory.md`
  - `notes/r2ghidra/integration_map.md` (only if necessary)
- In your response include:
  - brief change summary
  - structured list of final contract items (classes/functions) exactly as written in the notes

If anything is blocking/ambiguous, ask **targeted** questions.