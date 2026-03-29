# flatline Design Guide

This file captures the durable design guidance that still matters for day-to-day
work. It is intentionally brief.

- Keep unfinished work in `docs/TODO.md`.
- Keep accepted architecture and release-policy decisions in `docs/adr/`.
- Keep implementation detail in code, reference docs, and comments.
- Keep historical full-detail planning and specification material in
  `docs/archived/`; those archived docs are not maintained and may drift from
  the current repo state.
- Keep historical delivery sequencing out of this file unless it changes future
  design posture.

## Personas and Core Workflows

flatline is primarily for:

- reverse engineers automating decompilation pipelines from Python
- security engineers building repeatable triage workflows
- tooling engineers embedding deterministic decompilation checks into CI or release validation
- researchers building similarity, diffing, or data-flow analysis on structured decompiler output
- security researchers performing data-flow or taint analysis on decompiled functions

The main workflows to preserve in future design are:

- decompile one function from caller-provided memory plus explicit target selection
- enumerate valid target/compiler pairs
- fail predictably on invalid addresses, unsupported targets, or bad configuration
- support repeated decompilation in one process without leaking request state
- keep advanced structured output useful for downstream analysis, but opt-in

## Product Posture

- Design from the caller's perspective first.
- Keep the public surface Python-first and stable even when upstream internals change.
- Keep installation self-contained; users should not need to provide or build Ghidra separately for the normal path.
- Keep the runtime compatibility floor explicit: CPython `>=3.13`.
- Prefer explicit inputs, explicit validation, and explicit failure over hidden inference or silent fallback.
- Keep defaults deterministic when callers omit optional configuration.
- Preserve a lightweight baseline contract; richer analysis surfaces should be additive.
- Do not treat full upstream feature parity as a goal by default; additions should justify caller value.
- Support broad ISA availability, but state confidence boundaries clearly.
- Treat supported hosts, published wheels, fixture-backed ISAs, and best-effort ISAs as distinct concepts in both design and release messaging.
- Host-support promotion should follow continuous contract evidence, not successful builds or wheel publication alone.
- The current supported runtime-host boundary is Linux x86_64, macOS arm64, and Windows x86_64; Linux aarch64 and macOS x86_64 remain wheel-install targets pending promotion evidence.

## Durable Boundaries

- The foundational contract is single-function decompilation from memory, not file loading.
- Keep function-level decompilation as the baseline scope; broader program modeling should not be assumed by default.
- Convenience layers may be added, but they should stay additive over the memory-image core rather than redefining it.
- File-loading convenience is a separate concern with its own parsing, security, and maintenance cost; keep that cost isolated from the core contract.
- This core model fits the target users, who often already have loaded memory and architecture information from surrounding tooling.
- The default experience should remain self-contained and broad enough to work out of the box; lighter or custom runtime-data setups are explicit overrides.
- Auto-discovered runtime-data compatibility drift should be surfaced as an explicit warning; custom runtime-data roots remain caller-managed compatibility choices.
- Broad bundled ISA coverage does not imply equal support confidence. The fixture-backed confidence promise remains the narrower set: x86 32/64, ARM64, RISC-V 64, and MIPS32.
- Non-fixture-backed bundled ISAs and variants should promise enumeration and structured error-contract coverage only, not decompilation-quality confidence.
- Future input-model expansion should preserve ways to express information that materially affects quality, such as memory completeness, readonly boundaries, and symbol context.

## API and Evolution Rules

- The stable boundary is the public Python API. Bridge/native internals are replaceable implementation detail.
- Prefer additive evolution through optional request fields, optional metadata, and new structured diagnostics.
- Avoid breaking required fields or core semantics without a major-version event.
- Support one upstream decompiler version at a time. Upstream bumps are deliberate compatibility events, not background maintenance.
- Alternative backends or advanced execution modes must preserve the baseline public contract semantics.
- Each upstream bump should trigger contract and fixture reevaluation before release classification.
- Give public API deprecations at least one minor-release notice window unless security or compliance requires faster action.
- Keep user-fixable setup and configuration failures distinct from internal bugs.

## Quality and Operability Principles

- Define behavior in testable contract terms before implementation detail.
- Test durable contract behavior rather than incidental implementation structure or workflow formatting.
- Measure determinism with normalized structural/textual oracles, not exact pretty-printed C.
- Keep warning and error codes stable even if message text changes.
- Invalid input and unsupported targets should produce structured, actionable failures.
- When output is still usable, degradation should remain a successful result with warnings rather than being escalated to a hard error.
- If a caller explicitly requests an enriched surface, either provide it or fail; do not silently downgrade.
- Diagnostics may include useful identifiers and filesystem paths when they help users debug their own environment, but never raw memory-image bytes.
- Treat memory images as untrusted input and keep explicit resource limits as part of the operational contract.
- Do not execute external tools implicitly as part of the request path.
- Do not assume implicit thread safety. Parallel or concurrent features require an explicit session-isolation policy.
- Do not hide support degradations behind silent fallback.

## Future Design Heuristics

- New convenience should reduce caller friction without obscuring core target selection, memory assumptions, or support boundaries.
- New analysis surfaces should justify themselves through real downstream workflows such as similarity, diffing, or data-flow use cases.
- When capability expands, keep the base workflow simple and make extra complexity explicit.
- Support claims should follow evidence, not availability alone.
- Footprint pressure should trigger an explicit product decision, not silent pruning of the default experience.

## Persistent Risks Worth Remembering

- upstream callable-surface drift
- deterministic-output drift across environments
- runtime-footprint growth from the default full multi-ISA experience
- ISA-specific or ISA-variant quality gaps
- bridge or ABI assumptions breaking under runtime or interpreter changes
- validation cost growing faster than the supported matrix
