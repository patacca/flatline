"""Unit tests for public Python contract (specs.md section 3).

Tests validate data model construction, field enforcement, error taxonomy,
and advisory-field passthrough -- all pure Python, no native bridge required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from flatline import (
    VALID_METATYPES,
    CallSiteInfo,
    DecompileRequest,
    DecompileResult,
    DiagnosticFlags,
    ErrorItem,
    FlatlineError,
    FunctionInfo,
    FunctionPrototype,
    InvalidArgumentError,
    JumpTableInfo,
    ParameterInfo,
    StorageInfo,
    TypeInfo,
    UnsupportedTargetError,
    VariableInfo,
)
from flatline._models import _validate_compiler_spec

# ---------------------------------------------------------------------------
# Helpers for building synthetic objects
# ---------------------------------------------------------------------------

def _stub_type(name: str = "int", size: int = 4, metatype: str = "int") -> TypeInfo:
    return TypeInfo(name=name, size=size, metatype=metatype)


def _stub_diagnostics(**overrides: bool) -> DiagnosticFlags:
    defaults: dict[str, bool] = {
        "is_complete": True,
        "has_unreachable_blocks": False,
        "has_unimplemented": False,
        "has_bad_data": False,
        "has_no_code": False,
    }
    defaults.update(overrides)
    return DiagnosticFlags(**defaults)


def _stub_prototype(**overrides: object) -> FunctionPrototype:
    defaults: dict[str, object] = {
        "calling_convention": "__cdecl",
        "parameters": [
            ParameterInfo(name="a", type=_stub_type(), index=0),
            ParameterInfo(name="b", type=_stub_type(), index=1),
        ],
        "return_type": _stub_type(),
        "is_noreturn": False,
        "has_this_pointer": False,
        "has_input_errors": False,
        "has_output_errors": False,
    }
    defaults.update(overrides)
    return FunctionPrototype(**defaults)


def _stub_function_info(**overrides: object) -> FunctionInfo:
    defaults: dict[str, object] = {
        "name": "add",
        "entry_address": 0x1000,
        "size": 32,
        "is_complete": True,
        "prototype": _stub_prototype(),
        "local_variables": [],
        "call_sites": [],
        "jump_tables": [],
        "diagnostics": _stub_diagnostics(),
        "varnode_count": 42,
    }
    defaults.update(overrides)
    return FunctionInfo(**defaults)


# ---------------------------------------------------------------------------
# U-001: Request schema rejects missing required fields
# ---------------------------------------------------------------------------

def test_u001_request_schema_required_fields():
    """U-001: Missing required request fields map to structured invalid_argument errors."""
    base_kwargs: dict[str, object] = {
        "memory_image": b"\xcc",
        "base_address": 0x1000,
        "function_address": 0x1000,
        "language_id": "x86:LE:64:default",
    }

    # Each required field omitted -> TypeError (Python enforcement)
    for field in ("memory_image", "base_address", "function_address", "language_id"):
        kwargs = {k: v for k, v in base_kwargs.items() if k != field}
        with pytest.raises(TypeError):
            DecompileRequest(**kwargs)

    # Empty memory image -> InvalidArgumentError (semantic validation, specs.md section 3.4)
    with pytest.raises(InvalidArgumentError) as exc_info:
        DecompileRequest(**{**base_kwargs, "memory_image": b""})
    assert exc_info.value.category == "invalid_argument"

    # Empty language_id -> InvalidArgumentError
    with pytest.raises(InvalidArgumentError) as exc_info:
        DecompileRequest(**{**base_kwargs, "language_id": ""})
    assert exc_info.value.category == "invalid_argument"

    # Valid construction succeeds
    req = DecompileRequest(**base_kwargs)
    assert req.memory_image == b"\xcc"
    assert req.base_address == 0x1000
    assert req.function_address == 0x1000
    assert req.language_id == "x86:LE:64:default"

    # Optional fields default to None
    assert req.compiler_spec is None
    assert req.runtime_data_dir is None
    assert req.function_size_hint is None
    assert req.analysis_budget is None


# ---------------------------------------------------------------------------
# U-002: Unknown compiler id handling
# ---------------------------------------------------------------------------

def test_u002_unknown_compiler_rejected_without_fallback():
    """U-002: Unknown compiler identifiers are hard failures, never implicit fallback."""
    known_specs = frozenset({"gcc", "default", "windows"})

    # Unknown compiler -> UnsupportedTargetError
    with pytest.raises(UnsupportedTargetError) as exc_info:
        _validate_compiler_spec("unknown_compiler", known_specs)
    assert exc_info.value.category == "unsupported_target"

    # Empty string -> UnsupportedTargetError (no empty-string fallback)
    with pytest.raises(UnsupportedTargetError):
        _validate_compiler_spec("", known_specs)

    # Known compiler passes without error
    _validate_compiler_spec("gcc", known_specs)
    _validate_compiler_spec("default", known_specs)

    # Error inherits from FlatlineError
    assert issubclass(UnsupportedTargetError, FlatlineError)


# ---------------------------------------------------------------------------
# U-003: Result metadata envelope shape
# ---------------------------------------------------------------------------

def test_u003_result_metadata_required_keys():
    """U-003: Result metadata always includes required top-level keys."""
    required_keys = {"decompiler_version", "language_id", "compiler_spec", "diagnostics"}

    metadata = {
        "decompiler_version": "0.1.0-dev",
        "language_id": "x86:LE:64:default",
        "compiler_spec": "gcc",
        "diagnostics": {},
    }
    result = DecompileResult(
        c_code="int add(int a, int b) { return a + b; }",
        function_info=_stub_function_info(),
        warnings=[],
        error=None,
        metadata=metadata,
    )

    # All required keys present
    assert required_keys.issubset(result.metadata.keys())

    # Each required key has expected type
    assert isinstance(result.metadata["decompiler_version"], str)
    assert isinstance(result.metadata["language_id"], str)
    assert isinstance(result.metadata["compiler_spec"], str)

    # Error-path result also carries metadata
    error_metadata = {
        "decompiler_version": "0.1.0-dev",
        "language_id": "x86:LE:64:default",
        "compiler_spec": "gcc",
        "diagnostics": {},
    }
    error_result = DecompileResult(
        c_code=None,
        function_info=None,
        warnings=[],
        error=ErrorItem(category="invalid_address", message="bad addr", retryable=False),
        metadata=error_metadata,
    )
    assert required_keys.issubset(error_result.metadata.keys())


# ---------------------------------------------------------------------------
# U-004: function_size_hint passthrough
# ---------------------------------------------------------------------------

def test_u004_function_size_hint_passthrough():
    """U-004: function_size_hint is accepted and passed through; omission does not error."""
    base_kwargs: dict[str, object] = {
        "memory_image": b"\xcc\xc3",
        "base_address": 0x1000,
        "function_address": 0x1000,
        "language_id": "x86:LE:64:default",
    }

    # Without hint -- defaults to None, no error
    req_no_hint = DecompileRequest(**base_kwargs)
    assert req_no_hint.function_size_hint is None

    # With hint -- value preserved
    req_with_hint = DecompileRequest(**base_kwargs, function_size_hint=64)
    assert req_with_hint.function_size_hint == 64

    # Zero hint -- advisory, no error
    req_zero_hint = DecompileRequest(**base_kwargs, function_size_hint=0)
    assert req_zero_hint.function_size_hint == 0


def test_request_accepts_pathlike_runtime_data_dir() -> None:
    """Runtime-data overrides accept `Path` inputs from `ghidra_sleigh`."""
    runtime_dir = Path("/tmp/flatline-runtime")
    request = DecompileRequest(
        memory_image=b"\xcc\xc3",
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
        runtime_data_dir=runtime_dir,
    )

    assert request.runtime_data_dir == str(runtime_dir)


# ---------------------------------------------------------------------------
# U-005: FunctionInfo fields from stub
# ---------------------------------------------------------------------------

def test_u005_function_info_fields_from_stub():
    """U-005: FunctionInfo fields are populated from adapter stub with correct types.

    Validates: FunctionInfo required fields present; DiagnosticFlags aggregation
    matches individual flag values; TypeInfo metatype is a valid stable string.
    """
    diag = _stub_diagnostics(is_complete=True, has_unimplemented=True)
    param = ParameterInfo(
        name="x",
        type=_stub_type("uint32_t", 4, "uint"),
        index=0,
        storage=StorageInfo(space="register", offset=0, size=4),
    )
    proto = _stub_prototype(
        parameters=[param],
        return_type=_stub_type("void", 0, "void"),
    )
    call_site = CallSiteInfo(instruction_address=0x1010, target_address=0x2000)
    jump = JumpTableInfo(
        switch_address=0x1020,
        target_count=3,
        target_addresses=[0x1030, 0x1040, 0x1050],
    )
    local_var = VariableInfo(
        name="tmp",
        type=_stub_type("int", 4, "int"),
        storage=StorageInfo(space="stack", offset=-8, size=4),
    )
    info = FunctionInfo(
        name="test_func",
        entry_address=0x1000,
        size=64,
        is_complete=True,
        prototype=proto,
        local_variables=[local_var],
        call_sites=[call_site],
        jump_tables=[jump],
        diagnostics=diag,
        varnode_count=150,
    )

    # Required fields present with correct types
    assert isinstance(info.name, str) and info.name == "test_func"
    assert isinstance(info.entry_address, int) and info.entry_address == 0x1000
    assert isinstance(info.size, int) and info.size == 64
    assert isinstance(info.is_complete, bool) and info.is_complete is True
    assert isinstance(info.prototype, FunctionPrototype)
    assert isinstance(info.local_variables, list)
    assert isinstance(info.call_sites, list)
    assert isinstance(info.jump_tables, list)
    assert isinstance(info.diagnostics, DiagnosticFlags)
    assert isinstance(info.varnode_count, int) and info.varnode_count == 150

    # DiagnosticFlags individual values
    assert diag.is_complete is True
    assert diag.has_unreachable_blocks is False
    assert diag.has_unimplemented is True
    assert diag.has_bad_data is False
    assert diag.has_no_code is False

    # Prototype fields
    assert proto.calling_convention == "__cdecl"
    assert len(proto.parameters) == 1
    assert proto.parameters[0].name == "x"
    assert proto.return_type.metatype == "void"
    assert proto.is_noreturn is False
    assert proto.has_this_pointer is False
    assert proto.has_input_errors is False
    assert proto.has_output_errors is False

    # TypeInfo metatype is a valid stable string
    assert param.type.metatype in VALID_METATYPES
    assert proto.return_type.metatype in VALID_METATYPES

    # StorageInfo
    assert param.storage is not None
    assert param.storage.space == "register"
    assert param.storage.offset == 0
    assert param.storage.size == 4

    # CallSiteInfo
    assert call_site.instruction_address == 0x1010
    assert call_site.target_address == 0x2000

    # JumpTableInfo
    assert jump.target_count == 3
    assert len(jump.target_addresses) == 3

    # VariableInfo with storage
    assert local_var.name == "tmp"
    assert local_var.storage is not None
    assert local_var.storage.space == "stack"

    # Frozen: attribute reassignment blocked
    with pytest.raises(AttributeError):
        info.name = "modified"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# U-006: analysis_budget passthrough
# ---------------------------------------------------------------------------

def test_u006_analysis_budget_passthrough():
    """U-006: analysis_budget is accepted and passed through; omission does not error."""
    base_kwargs: dict[str, object] = {
        "memory_image": b"\xcc\xc3",
        "base_address": 0x1000,
        "function_address": 0x1000,
        "language_id": "x86:LE:64:default",
    }

    # Without budget -- defaults to None, no error
    req_no_budget = DecompileRequest(**base_kwargs)
    assert req_no_budget.analysis_budget is None

    # With budget dict -- value preserved
    budget = {"max_instructions": 50000, "timeout_ms": 5000}
    req_with_budget = DecompileRequest(**base_kwargs, analysis_budget=budget)
    assert req_with_budget.analysis_budget == budget
