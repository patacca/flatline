"""ghidralib — Python wrapper around the Ghidra decompiler."""

from ghidralib._errors import (
    CATEGORY_TO_EXCEPTION,
    ERROR_CATEGORIES,
    DecompileFailedError,
    GhidralibError,
    InternalError,
    InvalidAddressError,
    InvalidArgumentError,
    UnsupportedTargetError,
)
from ghidralib._models import (
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

__version__ = "0.1.0-dev"

_UPSTREAM_TAG = "Ghidra_12.0.3_build"
_UPSTREAM_COMMIT = "09f14c92d3da6e5d5f6b7dea115409719db3cce1"
_RUNTIME_DATA_REVISION = ""  # populated when runtime data is bundled


def get_version_info() -> VersionInfo:
    """Report runtime version information."""
    return VersionInfo(
        ghidralib_version=__version__,
        upstream_tag=_UPSTREAM_TAG,
        upstream_commit=_UPSTREAM_COMMIT,
        runtime_data_revision=_RUNTIME_DATA_REVISION,
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
    "DiagnosticFlags",
    "ErrorItem",
    "FunctionInfo",
    "FunctionPrototype",
    "GhidralibError",
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
    "get_version_info",
]
