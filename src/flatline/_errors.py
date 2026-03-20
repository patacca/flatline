"""flatline error taxonomy.

Stable exception hierarchy mapped from error categories (specs.md section 3.4).
Category names are contract-stable across minor/patch releases.
"""

from __future__ import annotations

# --- Stable error categories (specs.md section 3.4) ---
ERROR_CATEGORIES: frozenset[str] = frozenset(
    {
        "invalid_argument",
        "unsupported_target",
        "invalid_address",
        "decompile_failed",
        "configuration_error",
        "internal_error",
    }
)


class FlatlineError(Exception):
    """Base exception for all flatline errors.

    All flatline exceptions inherit from this class.  Each subclass
    corresponds to one entry in [`ERROR_CATEGORIES`][flatline.ERROR_CATEGORIES] and carries a
    `category` class attribute with the matching category string.
    """

    category: str = ""

    @property
    def message(self) -> str:
        return self.args[0] if self.args else ""


class InvalidArgumentError(FlatlineError):
    """Raised when a request contains invalid or missing arguments.

    Examples: empty ``memory_image``, non-string ``language_id``,
    invalid ``analysis_budget`` fields.
    """

    category = "invalid_argument"


class UnsupportedTargetError(FlatlineError):
    """Raised when the ``language_id`` or ``compiler_spec`` is not recognized.

    Check available targets with [`list_language_compilers()`][flatline.list_language_compilers].
    """

    category = "unsupported_target"


class InvalidAddressError(FlatlineError):
    """Raised when the function address falls outside the memory image."""

    category = "invalid_address"


class DecompileFailedError(FlatlineError):
    """Raised when the decompiler engine fails to produce output."""

    category = "decompile_failed"


class ConfigurationError(FlatlineError):
    """Raised for user-fixable configuration issues.

    Indicates problems with the installation, runtime data directory, or
    other startup configuration that the caller can resolve.
    """

    category = "configuration_error"


class InternalError(FlatlineError):
    """Raised for unexpected internal errors (bugs in flatline).

    If you encounter this error, please report it as a bug.
    """

    category = "internal_error"


# --- Category string -> exception class mapping ---
CATEGORY_TO_EXCEPTION: dict[str, type[FlatlineError]] = {
    cls.category: cls
    for cls in (
        InvalidArgumentError,
        UnsupportedTargetError,
        InvalidAddressError,
        DecompileFailedError,
        ConfigurationError,
        InternalError,
    )
}
