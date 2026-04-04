"""Request and result models for one decompile operation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from os import fspath
from typing import Any

from flatline._errors import InvalidArgumentError
from flatline.models.enriched import Enriched
from flatline.models.types import (
    DEFAULT_MAX_INSTRUCTIONS,
    ErrorItem,
    FunctionInfo,
    WarningItem,
)


@dataclass(frozen=True)
class AnalysisBudget:
    """Deterministic per-request resource limits.

    Attributes:
        max_instructions: Maximum number of p-code instructions the
            decompiler will process before stopping. Defaults to
            ``100000``. Must be a positive integer.

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


@dataclass(frozen=True)
class DecompileRequest:
    """Input payload for one function decompilation.

    The caller provides a flat memory image covering the relevant address
    space. The library does not perform binary format parsing; callers
    working with binary files must extract memory content first.

    Attributes:
        memory_image: Byte content of the target memory region. Must be
            non-empty ``bytes`` or ``bytearray``.
        base_address: Virtual address of the start of ``memory_image``.
        function_address: Entry point virtual address of the function to
            decompile, within the memory image.
        language_id: Target architecture identifier (e.g.
            ``"x86:LE:64:default"``). Use
            [`list_language_compilers()`][flatline.list_language_compilers] to discover valid
            values.
        compiler_spec: Compiler specification (e.g. ``"gcc"``). When
            ``None``, the default compiler for the language is used.
        runtime_data_dir: Explicit path to the Ghidra runtime data
            directory. When ``None``, auto-discovered from
            ``ghidra-sleigh``.
        function_size_hint: Optional advisory size hint in bytes for the
            function body.
        analysis_budget: Resource limits for this decompilation. Accepts
            an [`AnalysisBudget`][flatline.AnalysisBudget] or a ``dict`` with a
            ``"max_instructions"`` key. Defaults to
            ``AnalysisBudget(max_instructions=100000)``.
        enriched: When ``True``, the result includes an
            [`Enriched`][flatline.Enriched] companion payload with
            post-simplification pcode and varnode graph data.
            Defaults to ``False``.
        tail_padding: Optional byte pattern used to satisfy decoder
            lookahead reads that start within ``memory_image`` but extend
            past its tail. Defaults to ``b"\\x00"`` so exact function
            slices decompile without manual caller padding. Non-empty
            padding is repeated as needed. Set to ``None`` or ``b""`` to
            preserve strict tail-boundary failures.

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
    enriched: bool = False
    tail_padding: bytes | None = b"\x00"

    def __post_init__(self) -> None:
        if not isinstance(self.memory_image, (bytes, bytearray)):
            raise InvalidArgumentError("memory_image must be bytes or bytearray")
        if len(self.memory_image) == 0:
            raise InvalidArgumentError("memory_image must not be empty")
        if not isinstance(self.language_id, str) or not self.language_id:
            raise InvalidArgumentError("language_id must be a non-empty string")
        if not isinstance(self.enriched, bool):
            raise InvalidArgumentError("enriched must be a bool")
        if self.tail_padding is not None and not isinstance(self.tail_padding, (bytes, bytearray)):
            raise InvalidArgumentError("tail_padding must be bytes, bytearray, or None")
        if self.runtime_data_dir is not None:
            object.__setattr__(self, "runtime_data_dir", fspath(self.runtime_data_dir))
        if isinstance(self.tail_padding, bytearray):
            object.__setattr__(self, "tail_padding", bytes(self.tail_padding))
        if self.tail_padding == b"":
            object.__setattr__(self, "tail_padding", None)
        object.__setattr__(self, "analysis_budget", _coerce_analysis_budget(self.analysis_budget))


@dataclass(frozen=True)
class DecompileResult:
    """Output payload from one function decompilation.

    On success, ``c_code`` and ``function_info`` are populated. On
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
        enriched: Optional [`Enriched`][flatline.Enriched] companion
            payload, populated only when ``DecompileRequest.enriched``
            is ``True`` and decompilation succeeds. ``None`` otherwise.
    """

    c_code: str | None
    function_info: FunctionInfo | None
    warnings: list[WarningItem]
    error: ErrorItem | None
    metadata: dict[str, Any]
    enriched: Enriched | None = None


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


__all__ = [
    "AnalysisBudget",
    "DecompileRequest",
    "DecompileResult",
]
