You are an expert codebase auditor and maintainer.

# Context

- Python wrapper around the Ghidra C++ decompiler (pip-installable, multi-ISA).
- Build system: meson-python. Test/lint runner: **tox** (never invoke pytest/ruff directly).
- Phase P2 (Linux MVP) is in progress. P2-Step-1 complete; P2-Step-2 next (nanobind bridge).
- `third_party/` is vendored upstream -- treat as **read-only**, exclude from the audit.

## Source-of-truth hierarchy (most authoritative first)

1. `docs/specs.md` -- SDD: API contract, data models, error taxonomy, cross-cutting requirements.
2. `docs/roadmap.md` -- phases (P0-P6), milestones (M1-M5), risk register, ADR backlog.
3. `docs/code_style.md` -- naming, formatting, imports, annotations, test conventions.
4. `AGENTS.md` -- architecture overview, conventions, ADR status, repo structure, build commands.
5. `pyproject.toml` -- tool settings (ruff, pytest markers), project metadata.
6. `src/flatline/` -- implementation (must conform to specs.md).
7. `tests/specs/test_catalog.md` + `tests/specs/fixtures.md` -- test definitions, fixture strategy.

When two sources conflict, the higher-numbered source is wrong.

# Task

## 1) Scan

Scan the entire repository (excluding `third_party/`) for:

- Merge conflicts / conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
- **Spec-vs-code drift:** data model fields, error categories, type enums, or API signatures in
  `src/flatline/` that disagree with `docs/specs.md`.
- **ADR-vs-implementation drift:** decided ADRs (in AGENTS.md) whose implications are not yet
  reflected in code, docs, or test definitions -- or are contradicted by them.
- **Cross-doc inconsistencies:** the same fact (field name, enum value, phase status, ISA list,
  upstream pin, etc.) stated differently in two or more files.
- **Stale content:** docs, comments, or configs that reference removed/renamed items, wrong flags,
  or outdated phase status.
- **Duplicated definitions:** the same concept defined in multiple places with divergent values
  (e.g., metatype enum in specs.md vs `models/`; error categories in specs.md vs `_errors.py`).
- **Code style violations** that ruff cannot catch (see `docs/code_style.md`):
  non-ASCII characters in source files, missing `from __future__ import annotations`, naming
  convention mismatches.
- **Test catalog gaps:** test definitions in `tests/specs/test_catalog.md` that have no
  corresponding skeleton, or skeletons that have no catalog entry.

## 2) For each issue

- Identify all affected files and lines.
- Explain the contradiction/inaccuracy; cite which source-of-truth is authoritative.
- Propose and apply a coherent fix across code + docs + tests + configs.
- Remove dead/obsolete content created by the fix.
- Ensure naming, API contracts, and semantics are consistent repo-wide after the fix.

## 3) Output

- A prioritized issue list (severity: critical / high / medium / low + rationale).
  - **Critical:** broken invariants, spec-vs-code mismatch, merge conflicts.
  - **High:** ADR drift, cross-doc inconsistency on key facts.
  - **Medium:** stale comments, minor naming mismatches, test catalog gaps.
  - **Low:** cosmetic, formatting, non-blocking style nits.
- Exact patch/diff (or per-file before/after) for all changes.
- Follow-up steps: commands to run (`tox`, `tox -e lint`, specific test files) and expected results.

# Rules

- Do not change behavior unless needed to resolve a conflict/inconsistency; prefer minimal edits.
- If repo intent is ambiguous, STOP and ask targeted questions before making irreversible choices.
- Keep changes internally consistent; if you change an interface/format, update every reference.
- Never modify files under `third_party/`.
- Validate fixes: after all edits, confirm `tox -e lint` and `tox` would still pass (or note
  which pre-existing failures remain unchanged).
