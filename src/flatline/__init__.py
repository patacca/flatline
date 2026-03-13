"""flatline -- Python wrapper around the Ghidra decompiler."""

from __future__ import annotations

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

from flatline._errors import (
    CATEGORY_TO_EXCEPTION,
    ERROR_CATEGORIES,
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
    RUNTIME_DATA_REVISION,
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
        runtime_data_revision=RUNTIME_DATA_REVISION,
    )


__all__ = [
    "CATEGORY_TO_EXCEPTION",
    "ERROR_CATEGORIES",
    "VALID_METATYPES",
    "VALID_WARNING_PHASES",
    "CallSiteInfo",
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
