# r2ghidra Integration Map (Pinned Analysis)

Source root:
- `third_party/r2ghidra`

Pinned Ghidra baseline for this mapping:
- `Ghidra_12.0.3_build` (`09f14c92d3da6e5d5f6b7dea115409719db3cce1`, 2026-02-10)

## 1. Decompiler State Initialization

Relevant files/functions:
- `src/core_ghidra.cpp:159` `Decompile(...)`
- `src/core_ghidra.cpp:164` `R2Architecture arch(core, sleigh_id)`
- `src/core_ghidra.cpp:169` `arch.init(store)`
- `src/R2Architecture.cpp:39` `R2Architecture::R2Architecture`
- `src/R2Architecture.cpp:120` `R2Architecture::buildAction`

Notes:
- `r2ghidra` creates a fresh architecture per request, initializes it with `DocumentStorage`, then executes the current root action.
- Startup and per-request locking are mediated by radare2 (`DecompilerLock`, `RCoreMutex`).
- `collectSpecFiles` is called via `R2Architecture` to populate language definitions.

Classification:
- `Reusable as-is`: action reset/perform ordering (`action->reset(*func)` then `perform(*func)`) and high-level lifecycle shape.
- `Reimplement in ghidralib`: context object creation, initialization API, lock model, and startup path handling.
- `Not needed for MVP`: radare2 command-dispatch wrappers (`pd:g*` modes and command help plumbing).

## 2. Binary Bytes and Memory Model

Relevant files/functions:
- `src/R2LoadImage.cpp:14` `R2LoadImage::loadFill`
- `src/R2LoadImage.cpp:85` `R2LoadImage::getReadonly`
- `src/R2LoadImage.cpp:23` `R2LoadImage::adjustVma`

Notes:
- Byte reads are delegated to `r_io_read_at` through `RCore`.
- Readonly-range behavior is tied to `r2ghidra.roprop` and radare2 IO map semantics.
- This loader is fully adapter-specific.

Classification:
- `Reusable as-is`: none.
- `Reimplement in ghidralib`: load-image backend (file-backed ELF/raw reader), readonly policy, and any VMA policy.
- `Not needed for MVP`: radare2-specific `roprop` heuristics and IO map pointer scans.

## 3. Architecture and Context Metadata

Relevant files/functions:
- `src/R2Architecture.cpp:131` `buildLoader`
- `src/R2Architecture.cpp:137` `buildDatabase`
- `src/R2Architecture.cpp:183` `buildTypegrp`
- `src/R2Architecture.cpp:143` `buildCoreTypes`
- `src/R2Architecture.cpp:188` `buildCommentDB`
- `src/R2Architecture.cpp:106` `postSpecFile`
- `src/R2Scope.cpp:280` `R2Scope::registerFunction`

Notes:
- `R2Architecture` subclasses `SleighArchitecture` and replaces loader/scope/type/comment services with radare2-driven implementations.
- Function symbols/prototypes/comments are imported from radare2 analysis state.
- `postSpecFile` mutates function prototype metadata (e.g., noreturn) from radare2 catalogs.

Classification:
- `Reusable as-is`: small generic pieces in `R2Architecture` (e.g., `buildAction` tweak pattern) are conceptually reusable, code is not.
- `Reimplement in ghidralib`: symbol ingestion, function registration, type/comment bridges, and metadata import pipeline.
- `Not needed for MVP`: deep radare2 type-db synchronization and flag-name reconciliation complexity in `R2Scope`.

## 4. Decompilation Invocation Path

Relevant files/functions:
- `src/core_ghidra.cpp:159` `Decompile`
- `src/core_ghidra.cpp:171` `Address(..., function->addr)` and scope lookup
- `src/core_ghidra.cpp:193` `action->reset(*func)`
- `src/core_ghidra.cpp:194` `action->perform(*func)`
- `src/core_ghidra.cpp:240` `arch.print->docFunction(func)`

Notes:
- Call path is: lookup function in analyzer -> initialize arch -> execute decompile action graph -> print output.
- This validates that `reset`+`perform`+`docFunction` is the required minimal decompile path.

Classification:
- `Reusable as-is`: ordering and core Ghidra API calls.
- `Reimplement in ghidralib`: function lookup strategy and invocation surface independent of radare2 `RAnalFunction`.
- `Not needed for MVP`: alternate output modes (`JSON`, side-by-side disasm views, debug XML command modes).

## 5. Output and Error Handling

Relevant files/functions:
- `src/R2PrintC.cpp` custom `PrintC` implementation (`r2-c-language`)
- `src/core_ghidra.cpp:205` warning loop (`arch.getWarnings()`)
- `src/core_ghidra.cpp:264` exception handling in API entrypoints
- `src/R2CommentDatabase.cpp` radare2 comment bridge

Notes:
- Exceptions are caught at the command/API boundary and converted to radare2-friendly error output.
- Warnings are accumulated and optionally emitted as comments.
- XML is parsed back into radare2 metadata (`ParseCodeXML`) for annotated output.

Classification:
- `Reusable as-is`: `R2PrintC` is mostly Ghidra-side C printer customization and can be copied/adapted if desired.
- `Reimplement in ghidralib`: structured error/status mapping, warning extraction API, result serialization shape.
- `Not needed for MVP`: XML->radare2 code-metadata parsing and annotation machinery.

## 6. Radare2 Adapter Boundaries

Adapter-only code:
- `core_ghidra.cpp` command modes and interaction with `RCore`, `RAnalFunction`, `RConfig`, `RCodeMeta`.
- `R2LoadImage.*`, `R2Scope.*`, `R2CommentDatabase.*`, large parts of `R2TypeFactory.*`.
- Plugin entrypoints: `core_ghidra_plugin.c`, `anal_ghidra_plugin.c`.

Generic decompiler glue:
- `SleighArchitecture` init + `DocumentStorage` workflow.
- `Action` execution sequence (`reset`/`perform`) and print emission (`docFunction`).
- Language-description enumeration via `SleighArchitecture` facilities.

Notes:
- `ghidralib` should keep the generic glue, but introduce new neutral adapters (file loader, neutral symbol/comment model).
- Direct dependency on radare2 runtime objects is incompatible with pip-installable standalone MVP and must be removed.
