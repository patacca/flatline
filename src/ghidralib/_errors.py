"""ghidralib error taxonomy.

Stable exception hierarchy mapped from error categories (specs.md §3.4).
Category names are contract-stable across minor/patch releases.
"""

from __future__ import annotations

# Stable error categories (specs.md §3.4)
ERROR_CATEGORIES: frozenset[str] = frozenset({
    "invalid_argument",
    "unsupported_target",
    "invalid_address",
    "decompile_failed",
    "internal_error",
})


class GhidralibError(Exception):
    """Base exception for all ghidralib errors."""

    category: str = ""

    @property
    def message(self) -> str:
        return self.args[0] if self.args else ""


class InvalidArgumentError(GhidralibError):
    """Invalid or missing request arguments."""

    category = "invalid_argument"


class UnsupportedTargetError(GhidralibError):
    """Unsupported language or compiler specification."""

    category = "unsupported_target"


class InvalidAddressError(GhidralibError):
    """Invalid or unmapped address."""

    category = "invalid_address"


class DecompileFailedError(GhidralibError):
    """Decompilation failed."""

    category = "decompile_failed"


class InternalError(GhidralibError):
    """Unexpected internal error."""

    category = "internal_error"


# Category string → exception class mapping
CATEGORY_TO_EXCEPTION: dict[str, type[GhidralibError]] = {
    cls.category: cls
    for cls in (
        InvalidArgumentError,
        UnsupportedTargetError,
        InvalidAddressError,
        DecompileFailedError,
        InternalError,
    )
}
