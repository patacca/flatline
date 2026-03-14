"""flatline data models.

Frozen value types for the public API contract (specs.md section 3.3).
All structured result objects are pure Python frozen dataclasses.
No native pointers or references survive past the bridge boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from os import fspath
from typing import Any

from flatline._errors import InvalidArgumentError, UnsupportedTargetError

# --- Stable enumerations (specs.md section 3.3) ---

VALID_METATYPES: frozenset[str] = frozenset({
    "void", "bool", "int", "uint", "float", "pointer",
    "array", "struct", "union", "code", "enum", "unknown",
})

VALID_WARNING_PHASES: frozenset[str] = frozenset({"init", "analyze", "emit"})

DEFAULT_MAX_INSTRUCTIONS = 100000


# --- Leaf value types ---

@dataclass(frozen=True)
class StorageInfo:
    """Variable/parameter storage location."""

    space: str
    offset: int
    size: int


@dataclass(frozen=True)
class TypeInfo:
    """Recovered type descriptor."""

    name: str
    size: int
    metatype: str


@dataclass(frozen=True)
class ParameterInfo:
    """One function parameter."""

    name: str
    type: TypeInfo
    index: int
    storage: StorageInfo | None = None


@dataclass(frozen=True)
class VariableInfo:
    """One local variable."""

    name: str
    type: TypeInfo
    storage: StorageInfo | None = None


@dataclass(frozen=True)
class CallSiteInfo:
    """One call instruction within the function."""

    instruction_address: int
    target_address: int | None = None


@dataclass(frozen=True)
class JumpTableInfo:
    """One recovered jump table."""

    switch_address: int
    target_count: int
    target_addresses: list[int]


@dataclass(frozen=True)
class DiagnosticFlags:
    """Aggregated boolean diagnostic flags from the decompiler."""

    is_complete: bool
    has_unreachable_blocks: bool
    has_unimplemented: bool
    has_bad_data: bool
    has_no_code: bool


# --- Composite value types ---

@dataclass(frozen=True)
class FunctionPrototype:
    """Recovered function signature."""

    calling_convention: str | None
    parameters: list[ParameterInfo]
    return_type: TypeInfo
    is_noreturn: bool
    has_this_pointer: bool
    has_input_errors: bool
    has_output_errors: bool


@dataclass(frozen=True)
class FunctionInfo:
    """Structured post-decompile data for one function."""

    name: str
    entry_address: int
    size: int
    is_complete: bool
    prototype: FunctionPrototype
    local_variables: list[VariableInfo]
    call_sites: list[CallSiteInfo]
    jump_tables: list[JumpTableInfo]
    diagnostics: DiagnosticFlags
    varnode_count: int


# --- Warning/Error items ---

@dataclass(frozen=True)
class WarningItem:
    """One decompiler warning."""

    code: str
    message: str
    phase: str


@dataclass(frozen=True)
class ErrorItem:
    """Structured error descriptor."""

    category: str
    message: str
    retryable: bool


# --- Enumeration and version types ---

@dataclass(frozen=True)
class LanguageCompilerPair:
    """One valid language_id + compiler_spec entry."""

    language_id: str
    compiler_spec: str


@dataclass(frozen=True)
class VersionInfo:
    """Runtime version information."""

    flatline_version: str
    upstream_tag: str
    upstream_commit: str


@dataclass(frozen=True)
class AnalysisBudget:
    """Deterministic per-request resource limits."""

    max_instructions: int = DEFAULT_MAX_INSTRUCTIONS

    def __post_init__(self) -> None:
        if not isinstance(self.max_instructions, int) or isinstance(self.max_instructions, bool):
            raise InvalidArgumentError("analysis_budget.max_instructions must be an integer")
        if self.max_instructions <= 0:
            raise InvalidArgumentError("analysis_budget.max_instructions must be positive")


# --- Request/Result ---

@dataclass(frozen=True)
class DecompileRequest:
    """Input payload for one function decompilation."""

    memory_image: bytes
    base_address: int
    function_address: int
    language_id: str
    compiler_spec: str | None = None
    runtime_data_dir: str | None = None
    function_size_hint: int | None = None
    analysis_budget: AnalysisBudget | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.memory_image, (bytes, bytearray)):
            raise InvalidArgumentError("memory_image must be bytes or bytearray")
        if len(self.memory_image) == 0:
            raise InvalidArgumentError("memory_image must not be empty")
        if not isinstance(self.language_id, str) or not self.language_id:
            raise InvalidArgumentError("language_id must be a non-empty string")
        if self.runtime_data_dir is not None:
            object.__setattr__(self, "runtime_data_dir", fspath(self.runtime_data_dir))
        object.__setattr__(self, "analysis_budget", _coerce_analysis_budget(self.analysis_budget))


@dataclass(frozen=True)
class DecompileResult:
    """Output payload from one function decompilation."""

    c_code: str | None
    function_info: FunctionInfo | None
    warnings: list[WarningItem]
    error: ErrorItem | None
    metadata: dict[str, Any]


# --- Validation helpers (used by bridge, not user-facing) ---

def _validate_compiler_spec(compiler_spec: str, known_specs: frozenset[str]) -> None:
    """Validate compiler_spec against a known set.

    Raises UnsupportedTargetError if not found. Never silently falls back
    to a default compiler (specs.md section 3.4, section 4.4).
    """
    if compiler_spec not in known_specs:
        raise UnsupportedTargetError(
            f"Unknown compiler specification: {compiler_spec!r}"
        )


def _coerce_analysis_budget(raw_budget: Any) -> AnalysisBudget:
    if raw_budget is None:
        return AnalysisBudget()
    if isinstance(raw_budget, AnalysisBudget):
        return raw_budget
    if not isinstance(raw_budget, Mapping):
        raise InvalidArgumentError(
            "analysis_budget must be an AnalysisBudget or mapping"
        )

    unknown_fields = sorted(set(raw_budget) - {"max_instructions"})
    if unknown_fields:
        raise InvalidArgumentError(
            "analysis_budget contains unsupported fields: "
            + ", ".join(repr(field) for field in unknown_fields)
        )

    if "max_instructions" not in raw_budget:
        return AnalysisBudget()

    return AnalysisBudget(max_instructions=raw_budget["max_instructions"])
