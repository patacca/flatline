"""Core stable value types used by the public flatline API."""

from __future__ import annotations

from dataclasses import dataclass

from flatline._errors import UnsupportedTargetError
from flatline.models.enums import PcodeOpcode, VarnodeSpace

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
        metatype: Stable metatype classification string. One of
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


@dataclass(frozen=True)
class WarningItem:
    """One decompiler warning.

    Attributes:
        code: Warning identifier string.
        message: Human-readable warning message.
        phase: Decompiler phase that produced the warning. One of
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


@dataclass(frozen=True)
class VarnodeFlags:
    """Stable boolean flags exported for one varnode."""

    is_constant: bool
    is_input: bool
    is_free: bool
    is_implied: bool
    is_explicit: bool
    is_read_only: bool
    is_persist: bool
    is_addr_tied: bool


@dataclass(frozen=True)
class PcodeOpInfo:
    """One post-simplification pcode operation.

    Attributes:
        true_target_address: Start address of the basic block entered when a
            CBRANCH condition evaluates true, or ``None`` for non-CBRANCH ops.
        false_target_address: Start address of the basic block entered when a
            CBRANCH condition evaluates false, or ``None`` for non-CBRANCH ops.
    """

    id: int
    opcode: PcodeOpcode
    instruction_address: int
    sequence_time: int
    sequence_order: int
    input_varnode_ids: list[int]
    output_varnode_id: int | None = None
    true_target_address: int | None = None
    false_target_address: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.opcode, str):
            object.__setattr__(self, "opcode", PcodeOpcode(self.opcode))


@dataclass(frozen=True)
class InstructionInfo:
    """One disassembled instruction from the native disassembly pass."""

    address: int
    length: int
    mnemonic: str
    operands: str


@dataclass(frozen=True)
class VarnodeInfo:
    """One varnode in the enriched use-def graph.

    Attributes:
        id: Unique identifier for this varnode within the pcode graph.
        space: Address space name from :class:`VarnodeSpace`. Determines the
            interpretation of ``offset``:

            - :attr:`VarnodeSpace.CONST`: ``offset`` is the literal constant value.
            - :attr:`VarnodeSpace.REGISTER`: ``offset`` is the register number in
              the processor specification.
            - :attr:`VarnodeSpace.UNIQUE`: ``offset`` is an internal temporary
              allocation ID (opaque).
            - :attr:`VarnodeSpace.RAM`: ``offset`` is the virtual memory address.
            - :attr:`VarnodeSpace.FSPEC`: Call-spec reference. ``offset`` is set
              to ``0``; use ``call_site_index`` instead.
            - :attr:`VarnodeSpace.IOP`: Internal op pointer. ``offset`` is set
              to ``0``; use ``target_op_id`` instead.
            - :attr:`VarnodeSpace.JOIN`: Split/merged variable storage (opaque).
            - :attr:`VarnodeSpace.STACK`: ``offset`` is the stack-frame offset.

        offset: Location within the address space. For :attr:`VarnodeSpace.FSPEC`
            and :attr:`VarnodeSpace.IOP` spaces, this is set to ``0`` and the
            dedicated fields ``call_site_index`` / ``target_op_id`` carry the
            meaningful value.
        size: Size in bytes.
        flags: Boolean flags describing varnode properties. See
            :class:`VarnodeFlags`.
        defining_op_id: ID of the pcode op that produces this varnode, or
            ``None`` for inputs/constants.
        use_op_ids: IDs of pcode ops that consume this varnode.
        call_site_index: Index into the function's call sites for
            :attr:`VarnodeSpace.FSPEC` varnodes. ``None`` for other spaces.
        target_op_id: ID of the target pcode op for :attr:`VarnodeSpace.IOP`
            varnodes. ``None`` for other spaces.
    """

    id: int
    space: VarnodeSpace
    offset: int
    size: int
    flags: VarnodeFlags
    defining_op_id: int | None
    use_op_ids: list[int]
    call_site_index: int | None = None
    target_op_id: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.space, str):
            object.__setattr__(self, "space", VarnodeSpace(self.space))


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

    Populated on successful decompilation. Access via
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


def _validate_compiler_spec(compiler_spec: str, known_specs: frozenset[str]) -> None:  # pyright: ignore[reportUnusedFunction]
    """Validate compiler_spec against a known set.

    Raises UnsupportedTargetError if not found. Never silently falls back
    to a default compiler.
    """

    if compiler_spec not in known_specs:
        raise UnsupportedTargetError(f"Unknown compiler specification: {compiler_spec!r}")


__all__ = [
    "VALID_METATYPES",
    "VALID_WARNING_PHASES",
    "CallSiteInfo",
    "DiagnosticFlags",
    "ErrorItem",
    "FunctionInfo",
    "FunctionPrototype",
    "InstructionInfo",
    "JumpTableInfo",
    "LanguageCompilerPair",
    "ParameterInfo",
    "PcodeOpInfo",
    "StorageInfo",
    "TypeInfo",
    "VariableInfo",
    "VarnodeFlags",
    "VarnodeInfo",
    "VersionInfo",
    "WarningItem",
]
