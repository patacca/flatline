# Code Style Guide

Authoritative style rules for the flatline codebase.
Tooling config lives in `pyproject.toml`; this document captures conventions
that tools cannot enforce.

## Character set

- **ASCII only:** all source files (`.py`, `.cpp`, `.h`, `meson.build`) must
  contain only ASCII characters (U+0000–U+007F). No Unicode symbols, smart
  quotes, em-dashes, or non-ASCII identifiers. String literals that genuinely
  need non-ASCII content (e.g., test vectors) are the sole exception.

## Formatting and linting

- **Runner:** tox — use `tox` (or `tox -e lint`, `tox -e py313`, etc.) instead of
  invoking ruff, pytest, or other tools directly. This ensures consistent
  environments and matches CI.
- **Linter:** ruff (configured in `pyproject.toml`; invoked via tox).
- **Line length:** 99 characters.
- **Target version:** Python 3.13+.
- **Enabled rule sets:** `E`, `W`, `F`, `I`, `UP`, `B`, `SIM`, `RUF`, plus
  `PLC2401` (non-ascii-name) and `PLC2403` (non-ascii-import-name) for ASCII enforcement.
- **Import order:** isort via ruff; `flatline` is `known-first-party`.

## Python conventions

### Imports

- Every module starts with `from __future__ import annotations`.
- Standard library imports first, then third-party, then first-party — enforced
  by `isort`.
- Public API symbols are re-exported from `src/flatline/__init__.py` and listed
  in `__all__`. Internal modules use a `_` prefix (`_models.py`, `_errors.py`).

### Naming

- **Modules:** lowercase with underscores, leading `_` for internal modules.
- **Classes:** `PascalCase`. Dataclass names end with a domain noun
  (`Info`, `Item`, `Flags`, `Error`).
- **Functions/methods:** `snake_case`. Internal helpers use a `_` prefix.
- **Constants:** `UPPER_SNAKE_CASE`. Use `frozenset` for stable enumeration sets.
- **Test functions:** `test_<id>_<description>` where `<id>` is the test catalog
  ID (e.g., `test_u001_request_schema_required_fields`).

### Type annotations

- All public function signatures must be fully annotated.
- Use modern union syntax (`X | None`) instead of `Optional[X]`.
- Use `list[T]`, `dict[K, V]`, `frozenset[T]` (lowercase builtins) — not
  `typing.List` etc.
- `Any` is acceptable only for opaque pass-through fields
  (e.g., `analysis_budget`).
- **TYPE_CHECKING guard (mandatory):** every import that is used *only* for
  type annotations **must** live inside an `if TYPE_CHECKING:` block — no
  exceptions. An import that appears solely in parameter types, return types,
  or variable annotations and is never referenced at runtime **must not** sit
  at module level. This rule applies to standard-library imports (e.g.,
  `collections.abc.Sequence`), third-party imports, and first-party imports
  alike. Violating this rule introduces unnecessary runtime dependencies and
  risks circular-import failures:
  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from flatline._models import DecompileRequest
  ```
  **How to decide:** if removing the import causes a `NameError` at runtime
  (not just a type-checker complaint), it belongs at module level. Otherwise
  it belongs under `TYPE_CHECKING`.

### Data models

- All structured result types are **frozen dataclasses** (`@dataclass(frozen=True)`).
- No native pointers or references cross the ABI boundary — all results are pure
  Python value copies.
- Validation logic lives in `__post_init__` and raises the appropriate
  `FlatlineError` subclass.
- Helper constructors for tests use `_stub_*` naming (e.g., `_stub_type`,
  `_stub_prototype`).

### Error handling

- Hard errors on invalid input; warnings on degraded success. No silent
  fallbacks.
- All exceptions inherit from `FlatlineError`. Each has a stable `category`
  class attribute.
- Never catch-and-silence exceptions from upstream code without re-raising a
  `FlatlineError`.

## Test conventions

- **Framework:** pytest.
- **Scope gate:** add tests only for contract, runtime, release, or other
  user-visible functional behavior. Routine CI/workflow toggles, security
  automation changes, housekeeping, and doc-only edits do not get dedicated
  tests unless they change a maintained support or release invariant.
- **Layout:** tests are organised by category under `tests/{unit,contract,integration,regression,negative}/`.
- **Markers:** auto-applied from directory name via `conftest.py`
  (`unit`, `contract`, `integration`, `regression`, `negative`).
- **Naming:** `test_<catalog_id>_<short_description>` with a docstring that
  starts with the catalog ID (e.g., `"""U-001: ..."`).
- **Spec references:** docstrings and inline comments cite `specs.md` sections.
- **Native-dependent tests:** tests that require the compiled bridge use
  `@pytest.mark.requires_native`. Collection-time skip logic in `tests/conftest.py`
  adds a clear actionable skip reason when `flatline._flatline_native` is unavailable.
- **Helpers:** test-local stub builders are module-level `_stub_*` functions, not
  fixtures, unless shared across files (then go in `conftest.py`).

## File and section structure

- Module docstring at top: one-line summary, then a paragraph linking to the
  relevant spec section.
- Logical sections separated by comment banners:
  ```python
  # --- Section name ---
  ```
  or (in tests):
  ```python
  # ---------------------------------------------------------------------------
  # Section name
  # ---------------------------------------------------------------------------
  ```
- `__all__` in `__init__.py` is kept sorted alphabetically.

## C++ (bridge code, future)

Style TBD — will follow nanobind and upstream Ghidra conventions where
applicable. Rules will be added here when the bridge module is implemented.
