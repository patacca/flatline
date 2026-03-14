"""flatline -- Python wrapper around the Ghidra decompiler."""

from __future__ import annotations

from flatline._errors import (
    CATEGORY_TO_EXCEPTION,
    ERROR_CATEGORIES,
    ConfigurationError,
    DecompileFailedError,
    FlatlineError,
    InternalError,
    InvalidAddressError,
    InvalidArgumentError,
    UnsupportedTargetError,
)
from flatline._models import (
    VALID_METATYPES,
    VALID_WARNING_PHASES,
    AnalysisBudget,
    CallSiteInfo,
    DecompileRequest,
    DecompileResult,
    DiagnosticFlags,
    ErrorItem,
    FunctionInfo,
    FunctionPrototype,
    JumpTableInfo,
    LanguageCompilerPair,
    ParameterInfo,
    StorageInfo,
    TypeInfo,
    VariableInfo,
    VersionInfo,
    WarningItem,
)
from flatline._session import DecompilerSession, decompile_function, list_language_compilers
from flatline._version import (
    UPSTREAM_COMMIT,
    UPSTREAM_TAG,
    __version__,
)


def get_version_info() -> VersionInfo:
    """Report runtime version information."""
    return VersionInfo(
        flatline_version=__version__,
        upstream_tag=UPSTREAM_TAG,
        upstream_commit=UPSTREAM_COMMIT,
    )


__all__ = [
    "CATEGORY_TO_EXCEPTION",
    "ERROR_CATEGORIES",
    "VALID_METATYPES",
    "VALID_WARNING_PHASES",
    "AnalysisBudget",
    "CallSiteInfo",
    "ConfigurationError",
    "DecompileFailedError",
    "DecompileRequest",
    "DecompileResult",
    "DecompilerSession",
    "DiagnosticFlags",
    "ErrorItem",
    "FlatlineError",
    "FunctionInfo",
    "FunctionPrototype",
    "InternalError",
    "InvalidAddressError",
    "InvalidArgumentError",
    "JumpTableInfo",
    "LanguageCompilerPair",
    "ParameterInfo",
    "StorageInfo",
    "TypeInfo",
    "UnsupportedTargetError",
    "VariableInfo",
    "VersionInfo",
    "WarningItem",
    "__version__",
    "decompile_function",
    "get_version_info",
    "list_language_compilers",
]
