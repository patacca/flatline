Rewrite `AGENTS.md` for minimum tokens while preserving all operationally relevant repo knowledge.

Rules:
- Keep (lossless): architecture, conventions, commands, paths, ADR outcomes, data models, current state, caveats, immediate next steps.
- Drop: history/changelog language, repetition, filler, obvious inference, explanatory prose.
- Normalize style: short declarative bullets; merge related points; prefer compact noun phrases.
- Hard constraints: preserve section order/headings, exact command strings, exact file paths, exact version pins, exact enums/error categories.
- Do not invent, reinterpret, or broaden scope.
- Output only markdown bullet points (no preamble, no summary, no tables).
- Try to shrink the overview section if you can because it's the one that contains the most tokens.
- If you think that those information are critical for any prompt and in general it's better to have them always there, then keep them