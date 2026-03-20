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

VALID_METATYPES: frozenset[str] = frozenset(
    {
        "void",
        "bool",
        "int",
        "uint",
        "float",
        "pointer",
        "array",
        "struct",
        "union",
        "code",
        "enum",
        "unknown",
    }
)

VALID_WARNING_PHASES: frozenset[str] = frozenset({"init", "analyze", "emit"})

DEFAULT_MAX_INSTRUCTIONS = 100000


# --- Leaf value types ---


@dataclass(frozen=True)
class StorageInfo:
    """Variable or parameter storage location.

    Attributes:
        space: Address space name (e.g. ``"register"``, ``"ram"``,
            ``"stack"``).
        offset: Byte offset within the address space.
        size: Size in bytes.
    """

    space: str
    offset: int
    size: int


@dataclass(frozen=True)
class TypeInfo:
    """Recovered type descriptor.

    Attributes:
        name: Type name (e.g. ``"int"``, ``"undefined8"``).
        size: Type size in bytes.
        metatype: Stable metatype classification string.  One of
            [`VALID_METATYPES`][flatline.VALID_METATYPES] (``"void"``, ``"int"``,
            ``"uint"``, ``"float"``, ``"pointer"``, ``"array"``,
            ``"struct"``, ``"union"``, ``"code"``, ``"enum"``,
            ``"bool"``, ``"unknown"``).
    """

    name: str
    size: int
    metatype: str


@dataclass(frozen=True)
class ParameterInfo:
    """One function parameter.

    Attributes:
        name: Parameter name recovered by the decompiler.
        type: Recovered type descriptor.
        index: Zero-based position in the function signature.
        storage: Storage location, or ``None`` if not mapped.
    """

    name: str
    type: TypeInfo
    index: int
    storage: StorageInfo | None = None


@dataclass(frozen=True)
class VariableInfo:
    """One local variable.

    Attributes:
        name: Variable name recovered by the decompiler.
        type: Recovered type descriptor.
        storage: Storage location, or ``None`` if not mapped.
    """

    name: str
    type: TypeInfo
    storage: StorageInfo | None = None


@dataclass(frozen=True)
class CallSiteInfo:
    """One call instruction within the function.

    Attributes:
        instruction_address: Address of the ``CALL`` instruction.
        target_address: Resolved callee address, or ``None`` for indirect
            calls.
    """

    instruction_address: int
    target_address: int | None = None


@dataclass(frozen=True)
class JumpTableInfo:
    """One recovered jump table.

    Attributes:
        switch_address: Address of the switch or indirect-branch
            instruction.
        target_count: Number of resolved target addresses.
        target_addresses: Resolved target addresses.
    """

    switch_address: int
    target_count: int
    target_addresses: list[int]


@dataclass(frozen=True)
class DiagnosticFlags:
    """Aggregated boolean diagnostic flags from the decompiler.

    Attributes:
        is_complete: Whether decompilation completed fully.
        has_unreachable_blocks: Whether unreachable basic blocks were
            detected.
        has_unimplemented: Whether unimplemented instructions were
            encountered.
        has_bad_data: Whether the decompiler flagged bad data in the
            function body.
        has_no_code: Whether the function entry contained no executable
            code.
    """

    is_complete: bool
    has_unreachable_blocks: bool
    has_unimplemented: bool
    has_bad_data: bool
    has_no_code: bool


# --- Composite value types ---


@dataclass(frozen=True)
class FunctionPrototype:
    """Recovered function signature.

    Attributes:
        calling_convention: Calling convention model name (e.g.
            ``"__cdecl"``), or ``None`` if unknown.
        parameters: Recovered function parameters.
        return_type: Recovered return type.
        is_noreturn: ``True`` if the function does not return.
        has_this_pointer: ``True`` if the function has an implicit
            ``this`` parameter.
        has_input_errors: ``True`` if parameter recovery was incomplete.
        has_output_errors: ``True`` if return type recovery was
            incomplete.
    """

    calling_convention: str | None
    parameters: list[ParameterInfo]
    return_type: TypeInfo
    is_noreturn: bool
    has_this_pointer: bool
    has_input_errors: bool
    has_output_errors: bool


@dataclass(frozen=True)
class FunctionInfo:
    """Structured post-decompile data for one function.

    Populated on successful decompilation.  Access via
    [`DecompileResult.function_info`][flatline.DecompileResult].

    Attributes:
        name: Function name assigned by the decompiler.
        entry_address: Function entry point virtual address.
        size: Function body size in bytes.
        is_complete: Whether decompilation completed fully.
        prototype: Recovered function signature.
        local_variables: Local scope variables.
        call_sites: Call instructions within the function.
        jump_tables: Recovered jump tables.
        diagnostics: Aggregated diagnostic status flags.
        varnode_count: Total Varnode count (complexity metric).
    """

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
    """One decompiler warning.

    Attributes:
        code: Warning identifier string.
        message: Human-readable warning message.
        phase: Decompiler phase that produced the warning.  One of
            [`VALID_WARNING_PHASES`][flatline.VALID_WARNING_PHASES] (``"init"``,
            ``"analyze"``, ``"emit"``).
    """

    code: str
    message: str
    phase: str


@dataclass(frozen=True)
class ErrorItem:
    """Structured error descriptor returned in [`DecompileResult.error`][flatline.DecompileResult].

    Attributes:
        category: Error category string from
            [`ERROR_CATEGORIES`][flatline.ERROR_CATEGORIES].
        message: Human-readable error message.
        retryable: ``True`` if the operation might succeed on retry.
    """

    category: str
    message: str
    retryable: bool


# --- Enumeration and version types ---


@dataclass(frozen=True)
class LanguageCompilerPair:
    """One valid language/compiler pair known to the runtime data directory.

    Attributes:
        language_id: Language identifier (e.g. ``"x86:LE:64:default"``).
        compiler_spec: Compiler specification (e.g. ``"gcc"``).
    """

    language_id: str
    compiler_spec: str


@dataclass(frozen=True)
class VersionInfo:
    """Runtime version information.

    Attributes:
        flatline_version: The installed flatline package version.
        decompiler_version: The underlying Ghidra decompiler engine
            version (e.g. ``"ghidra-6.1"``).
    """

    flatline_version: str
    decompiler_version: str


@dataclass(frozen=True)
class AnalysisBudget:
    """Deterministic per-request resource limits.

    Attributes:
        max_instructions: Maximum number of p-code instructions the
            decompiler will process before stopping.  Defaults to
            ``100000``.  Must be a positive integer.

    Raises:
        InvalidArgumentError: If ``max_instructions`` is not a positive
            integer.

    Example:
        ```python
        budget = AnalysisBudget(max_instructions=500_000)
        request = DecompileRequest(..., analysis_budget=budget)
        ```
    """

    max_instructions: int = DEFAULT_MAX_INSTRUCTIONS

    def __post_init__(self) -> None:
        if not isinstance(self.max_instructions, int) or isinstance(self.max_instructions, bool):
            raise InvalidArgumentError("analysis_budget.max_instructions must be an integer")
        if self.max_instructions <= 0:
            raise InvalidArgumentError("analysis_budget.max_instructions must be positive")


# --- Request/Result ---


@dataclass(frozen=True)
class DecompileRequest:
    """Input payload for one function decompilation.

    The caller provides a flat memory image covering the relevant address
    space.  The library does not perform binary format parsing; callers
    working with binary files must extract memory content first.

    Attributes:
        memory_image: Byte content of the target memory region.  Must be
            non-empty ``bytes`` or ``bytearray``.
        base_address: Virtual address of the start of ``memory_image``.
        function_address: Entry point virtual address of the function to
            decompile, within the memory image.
        language_id: Target architecture identifier (e.g.
            ``"x86:LE:64:default"``).  Use
            [`list_language_compilers()`][flatline.list_language_compilers] to discover valid
            values.
        compiler_spec: Compiler specification (e.g. ``"gcc"``).  When
            ``None``, the default compiler for the language is used.
        runtime_data_dir: Explicit path to the Ghidra runtime data
            directory.  When ``None``, auto-discovered from
            ``ghidra-sleigh``.
        function_size_hint: Optional advisory size hint in bytes for the
            function body.
        analysis_budget: Resource limits for this decompilation.  Accepts
            an [`AnalysisBudget`][flatline.AnalysisBudget] or a ``dict`` with a
            ``"max_instructions"`` key.  Defaults to
            ``AnalysisBudget(max_instructions=100000)``.

    Raises:
        InvalidArgumentError: If ``memory_image`` is empty or not bytes,
            ``language_id`` is empty, or ``analysis_budget`` is invalid.
    """

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
    """Output payload from one function decompilation.

    On success, ``c_code`` and ``function_info`` are populated.  On
    failure, ``error`` describes the problem and the other fields may be
    ``None``.

    Attributes:
        c_code: Decompiled C source code, or ``None`` on error.
        function_info: Structured function data, or ``None`` on error.
        warnings: Decompiler warnings emitted during processing.
        error: Structured error descriptor if decompilation failed,
            otherwise ``None``.
        metadata: Additional metadata with stable keys:
            ``"decompiler_version"``, ``"language_id"``,
            ``"compiler_spec"``, and ``"diagnostics"``.
    """

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
        raise UnsupportedTargetError(f"Unknown compiler specification: {compiler_spec!r}")


def _coerce_analysis_budget(raw_budget: Any) -> AnalysisBudget:
    if raw_budget is None:
        return AnalysisBudget()
    if isinstance(raw_budget, AnalysisBudget):
        return raw_budget
    if not isinstance(raw_budget, Mapping):
        raise InvalidArgumentError("analysis_budget must be an AnalysisBudget or mapping")

    unknown_fields = sorted(set(raw_budget) - {"max_instructions"})
    if unknown_fields:
        raise InvalidArgumentError(
            "analysis_budget contains unsupported fields: "
            + ", ".join(repr(field) for field in unknown_fields)
        )

    if "max_instructions" not in raw_budget:
        return AnalysisBudget()

    return AnalysisBudget(max_instructions=raw_budget["max_instructions"])
