---
name: compact-agent
description: Compress or rewrite `AGENTS.md` and similar repo-memory instruction files into a minimum-token form without losing operational facts. Use when Codex needs to shrink prompt memory, refresh repo instructions after changes, or convert verbose maintenance docs into compact bullet-only guidance while preserving section order, exact commands, file paths, version pins, enums, error categories, ADR outcomes, and immediate next steps.
---

# Compact Agent

Rewrite repo memory files so another agent can recover project state quickly with fewer tokens. Keep the result terse, factual, and lossless on anything that affects execution.

## Contract

- Rewrite `AGENTS.md` for minimum tokens while preserving all operationally relevant repo knowledge.
- Keep (lossless): architecture, conventions, commands, paths, ADR outcomes, data models, current state, caveats, immediate next steps.
- Drop: history/changelog language, repetition, filler, obvious inference, explanatory prose.
- Normalize style: short declarative bullets; merge related points; prefer compact noun phrases.
- Hard constraints: preserve section order/headings, exact command strings, exact file paths, exact version pins, exact enums/error categories.
- Do not invent, reinterpret, or broaden scope.
- Output only markdown bullet points (no preamble, no summary, no tables).
- Shrink the overview section aggressively; it usually contains the most recoverable prose.
- If information is critical for prompt quality or repeated execution, keep it.

## Workflow

1. Read the target file plus any repo sources needed to confirm current facts before compressing.
2. Keep the existing section order and headings unless the user explicitly asks to change them.
3. Separate hard facts from re-derivable prose; preserve the facts and compress or remove the prose.
4. Preserve exact strings for commands, file paths, version pins, commits, tags, enums, and error-category names.
5. Compress section by section, merging related facts where no meaning is lost.
6. Keep release state, support matrices, caveats, and immediate next steps explicit.
7. Verify any fact that may have drifted before keeping it.
8. Avoid turning the file into a changelog; keep only current operational state.

## Checks

- Commands remain copy-pastable and unchanged.
- Section headings and ordering still match the original file.
- Exact identifiers such as `0.1.0`, `ghidra-sleigh == 12.0.4`, commit hashes, and public error categories remain intact.
- Only facts that save future re-derivation time remain.
