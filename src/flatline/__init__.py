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
from flatline._session import DecompilerSession, decompile_function, list_language_compilers
from flatline._version import (
    DECOMPILER_VERSION,
    __version__,
)
from flatline.models import (
    VALID_METATYPES,
    VALID_WARNING_PHASES,
    AnalysisBudget,
    CallSiteInfo,
    DecompileRequest,
    DecompileResult,
    DiagnosticFlags,
    Enriched,
    ErrorItem,
    FunctionInfo,
    FunctionPrototype,
    InstructionInfo,
    JumpTableInfo,
    LanguageCompilerPair,
    ParameterInfo,
    Pcode,
    PcodeOpInfo,
    StorageInfo,
    TypeInfo,
    VariableInfo,
    VarnodeFlags,
    VarnodeInfo,
    VersionInfo,
    WarningItem,
)


def get_version_info() -> VersionInfo:
    """Report runtime version information.

    Returns:
        The installed flatline package version and the underlying
            Ghidra decompiler engine version.
    """
    return VersionInfo(
        flatline_version=__version__,
        decompiler_version=DECOMPILER_VERSION,
    )


__all__ = [
    "CATEGORY_TO_EXCEPTION",
    "DECOMPILER_VERSION",
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
    "Enriched",
    "ErrorItem",
    "FlatlineError",
    "FunctionInfo",
    "FunctionPrototype",
    "InstructionInfo",
    "InternalError",
    "InvalidAddressError",
    "InvalidArgumentError",
    "JumpTableInfo",
    "LanguageCompilerPair",
    "ParameterInfo",
    "Pcode",
    "PcodeOpInfo",
    "StorageInfo",
    "TypeInfo",
    "UnsupportedTargetError",
    "VariableInfo",
    "VarnodeFlags",
    "VarnodeInfo",
    "VersionInfo",
    "WarningItem",
    "__version__",
    "decompile_function",
    "get_version_info",
    "list_language_compilers",
]
