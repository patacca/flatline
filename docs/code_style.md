# Code Style Guide

Authoritative style rules for the ghidralib codebase.
Tooling config lives in `pyproject.toml`; this document captures conventions
that tools cannot enforce.

## Formatting and linting

- **Runner:** tox — use `tox` (or `tox -e lint`, `tox -e py313`, etc.) instead of
  invoking ruff, pytest, or other tools directly. This ensures consistent
  environments and matches CI.
- **Linter:** ruff (configured in `pyproject.toml`; invoked via tox).
- **Line length:** 99 characters.
- **Target version:** Python 3.13+.
- **Enabled rule sets:** `E`, `W`, `F`, `I`, `UP`, `B`, `SIM`, `RUF`.
- **Import order:** isort via ruff; `ghidralib` is `known-first-party`.

## Python conventions

### Imports

- Every module starts with `from __future__ import annotations`.
- Standard library imports first, then third-party, then first-party — enforced
  by `isort`.
- Public API symbols are re-exported from `src/ghidralib/__init__.py` and listed
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
- **TYPE_CHECKING guard:** imports used *only* for type annotations must be
  placed inside an `if TYPE_CHECKING:` block. This avoids circular imports
  and unnecessary runtime dependencies:
  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from ghidralib._models import DecompileRequest
  ```

### Data models

- All structured result types are **frozen dataclasses** (`@dataclass(frozen=True)`).
- No native pointers or references cross the ABI boundary — all results are pure
  Python value copies.
- Validation logic lives in `__post_init__` and raises the appropriate
  `GhidralibError` subclass.
- Helper constructors for tests use `_stub_*` naming (e.g., `_stub_type`,
  `_stub_prototype`).

### Error handling

- Hard errors on invalid input; warnings on degraded success. No silent
  fallbacks.
- All exceptions inherit from `GhidralibError`. Each has a stable `category`
  class attribute.
- Never catch-and-silence exceptions from upstream code without re-raising a
  `GhidralibError`.

## Test conventions

- **Framework:** pytest.
- **Layout:** tests are organised by category under `tests/{unit,contract,integration,regression,negative}/`.
- **Markers:** auto-applied from directory name via `conftest.py`
  (`unit`, `contract`, `integration`, `regression`, `negative`).
- **Naming:** `test_<catalog_id>_<short_description>` with a docstring that
  starts with the catalog ID (e.g., `"""U-001: ..."`).
- **Spec references:** docstrings and inline comments cite `specs.md` sections.
- **Skip-decorating:** tests that need the native bridge use
  `@pytest.mark.skip(reason="requires native bridge")`.
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
