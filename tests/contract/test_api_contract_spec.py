"""Contract tests for API schema and taxonomy stability (specs.md section 3, 3.4, 3.5).

These tests verify that public types, field names, error categories, and version
metadata remain stable across releases -- the contract-level guarantees that
downstream code depends on. No native bridge required.
"""

from __future__ import annotations

import dataclasses
import inspect
from dataclasses import FrozenInstanceError

import pytest

from flatline import (
    CATEGORY_TO_EXCEPTION,
    ERROR_CATEGORIES,
    VALID_METATYPES,
    VALID_WARNING_PHASES,
    AnalysisBudget,
    CallSiteInfo,
    ConfigurationError,
    DecompileFailedError,
    DecompileRequest,
    DecompileResult,
    DiagnosticFlags,
    Enriched,
    ErrorItem,
    FlatlineError,
    FunctionInfo,
    FunctionPrototype,
    InstructionInfo,
    InternalError,
    InvalidAddressError,
    InvalidArgumentError,
    JumpTableInfo,
    LanguageCompilerPair,
    ParameterInfo,
    Pcode,
    PcodeOpInfo,
    StorageInfo,
    TypeInfo,
    UnsupportedTargetError,
    VariableInfo,
    VarnodeFlags,
    VarnodeInfo,
    VersionInfo,
    WarningItem,
    get_version_info,
)

# ---------------------------------------------------------------------------
# C-001: Public result schema stability
# ---------------------------------------------------------------------------


def test_c001_result_schema_stability():
    """C-001: Required result keys/types remain stable across compatible releases."""
    # DecompileResult required fields (specs.md section 3.3)
    result_fields = {f.name for f in dataclasses.fields(DecompileResult)}
    assert result_fields == {
        "c_code",
        "function_info",
        "warnings",
        "error",
        "metadata",
        "enriched",
    }

    # FunctionInfo required fields
    info_fields = {f.name for f in dataclasses.fields(FunctionInfo)}
    expected_info = {
        "name",
        "entry_address",
        "size",
        "is_complete",
        "prototype",
        "local_variables",
        "call_sites",
        "jump_tables",
        "diagnostics",
        "varnode_count",
    }
    assert info_fields == expected_info

    # WarningItem required fields
    warning_fields = {f.name for f in dataclasses.fields(WarningItem)}
    assert warning_fields == {"code", "message", "phase"}

    # ErrorItem required fields
    error_fields = {f.name for f in dataclasses.fields(ErrorItem)}
    assert error_fields == {"category", "message", "retryable"}


# ---------------------------------------------------------------------------
# C-002: Error taxonomy stability
# ---------------------------------------------------------------------------


def test_c002_error_taxonomy_stability():
    """C-002: Error categories are contract-stable identifiers."""
    # Exactly 6 categories defined (specs.md section 3.4)
    expected_categories = {
        "invalid_argument",
        "unsupported_target",
        "invalid_address",
        "decompile_failed",
        "configuration_error",
        "internal_error",
    }
    assert expected_categories == ERROR_CATEGORIES

    # Each category maps to a unique exception class
    assert set(CATEGORY_TO_EXCEPTION.keys()) == expected_categories
    assert len(set(CATEGORY_TO_EXCEPTION.values())) == 6

    # All exception classes inherit from FlatlineError
    for category, exc_cls in CATEGORY_TO_EXCEPTION.items():
        assert issubclass(exc_cls, FlatlineError)
        assert exc_cls.category == category

    # Direct class-level category verification
    assert InvalidArgumentError.category == "invalid_argument"
    assert UnsupportedTargetError.category == "unsupported_target"
    assert InvalidAddressError.category == "invalid_address"
    assert DecompileFailedError.category == "decompile_failed"
    assert ConfigurationError.category == "configuration_error"
    assert InternalError.category == "internal_error"

    # Instance .message property works
    exc = InvalidArgumentError("test message")
    assert exc.message == "test message"
    assert str(exc) == "test message"


# ---------------------------------------------------------------------------
# C-003: Version reporting contract
# ---------------------------------------------------------------------------


def test_c003_version_reporting_contains_decompiler_version():
    """C-003: Version endpoint includes flatline and decompiler version information."""
    info = get_version_info()

    assert isinstance(info, VersionInfo)

    # All required fields populated (specs.md section 3.3 VersionInfo)
    assert isinstance(info.flatline_version, str) and info.flatline_version
    assert isinstance(info.decompiler_version, str) and info.decompiler_version
    # Decompiler version reflects the Ghidra engine, not flatline
    assert info.decompiler_version.startswith("ghidra-")

    # VersionInfo fields match spec
    version_fields = {f.name for f in dataclasses.fields(VersionInfo)}
    assert version_fields == {
        "flatline_version",
        "decompiler_version",
    }


# ---------------------------------------------------------------------------
# C-004: Structured result object schema stability
# ---------------------------------------------------------------------------


def test_c004_structured_result_schema_stability():
    """C-004: Structured result objects (FunctionInfo, FunctionPrototype, TypeInfo)
    have stable required fields and types. Metatype strings are stable enum values.
    """
    # FunctionPrototype fields (specs.md section 3.3)
    proto_fields = {f.name for f in dataclasses.fields(FunctionPrototype)}
    assert proto_fields == {
        "calling_convention",
        "parameters",
        "return_type",
        "is_noreturn",
        "has_this_pointer",
        "has_input_errors",
        "has_output_errors",
    }

    # TypeInfo fields
    type_fields = {f.name for f in dataclasses.fields(TypeInfo)}
    assert type_fields == {"name", "size", "metatype"}

    # ParameterInfo fields
    param_fields = {f.name for f in dataclasses.fields(ParameterInfo)}
    assert param_fields == {"name", "type", "index", "storage"}

    # VariableInfo fields
    var_fields = {f.name for f in dataclasses.fields(VariableInfo)}
    assert var_fields == {"name", "type", "storage"}

    # StorageInfo fields
    storage_fields = {f.name for f in dataclasses.fields(StorageInfo)}
    assert storage_fields == {"space", "offset", "size"}

    # CallSiteInfo fields
    call_fields = {f.name for f in dataclasses.fields(CallSiteInfo)}
    assert call_fields == {"instruction_address", "target_address"}

    # JumpTableInfo fields
    jump_fields = {f.name for f in dataclasses.fields(JumpTableInfo)}
    assert jump_fields == {"switch_address", "target_count", "target_addresses"}

    # DiagnosticFlags fields
    diag_fields = {f.name for f in dataclasses.fields(DiagnosticFlags)}
    assert diag_fields == {
        "is_complete",
        "has_unreachable_blocks",
        "has_unimplemented",
        "has_bad_data",
        "has_no_code",
    }

    budget_fields = {f.name for f in dataclasses.fields(AnalysisBudget)}
    assert budget_fields == {"max_instructions"}

    # LanguageCompilerPair fields
    pair_fields = {f.name for f in dataclasses.fields(LanguageCompilerPair)}
    assert pair_fields == {"language_id", "compiler_spec"}

    # Metatype strings are the stable enum values (specs.md section 3.3)
    expected_metatypes = {
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
    assert expected_metatypes == VALID_METATYPES

    # Warning phases are the stable set
    assert {"init", "analyze", "emit"} == VALID_WARNING_PHASES

    # All structured result types are frozen dataclasses
    frozen_types = [
        AnalysisBudget,
        StorageInfo,
        TypeInfo,
        ParameterInfo,
        VariableInfo,
        CallSiteInfo,
        JumpTableInfo,
        DiagnosticFlags,
        FunctionPrototype,
        FunctionInfo,
        Enriched,
        Pcode,
        WarningItem,
        ErrorItem,
        VersionInfo,
        LanguageCompilerPair,
    ]
    for cls in frozen_types:
        assert dataclasses.is_dataclass(cls), f"{cls.__name__} must be a dataclass"


def test_c007_enriched_schema_stability() -> None:
    """C-007: Enriched-output companion types keep stable field names."""
    request_fields = {f.name for f in dataclasses.fields(DecompileRequest)}
    assert "enriched" in request_fields
    assert "tail_padding" in request_fields

    enriched_fields = {f.name for f in dataclasses.fields(Enriched)}
    assert enriched_fields == {"pcode", "instructions"}

    pcode_container_fields = {f.name for f in dataclasses.fields(Pcode)}
    assert pcode_container_fields == {"pcode_ops", "varnodes"}

    pcode_fields = {f.name for f in dataclasses.fields(PcodeOpInfo)}
    assert pcode_fields == {
        "id",
        "opcode",
        "instruction_address",
        "sequence_time",
        "sequence_order",
        "input_varnode_ids",
        "output_varnode_id",
    }

    varnode_fields = {f.name for f in dataclasses.fields(VarnodeInfo)}
    assert varnode_fields == {
        "id",
        "space",
        "offset",
        "size",
        "flags",
        "defining_op_id",
        "use_op_ids",
    }

    flag_fields = {f.name for f in dataclasses.fields(VarnodeFlags)}
    assert flag_fields == {
        "is_constant",
        "is_input",
        "is_free",
        "is_implied",
        "is_explicit",
        "is_read_only",
        "is_persist",
        "is_addr_tied",
    }


def test_c008_pcode_graph_surface_stability() -> None:
    """C-008: Pcode graph helpers keep stable names and parameters."""
    assert callable(Pcode.get_pcode_op)
    assert callable(Pcode.get_varnode)
    assert callable(Pcode.to_graph)

    get_op_sig = inspect.signature(Pcode.get_pcode_op)
    assert tuple(get_op_sig.parameters) == ("self", "op_id")

    get_varnode_sig = inspect.signature(Pcode.get_varnode)
    assert tuple(get_varnode_sig.parameters) == ("self", "varnode_id")

    graph_sig = inspect.signature(Pcode.to_graph)
    assert tuple(graph_sig.parameters) == ("self",)


def test_c009_instructioninfo_schema_stability() -> None:
    """C-009: InstructionInfo remains a frozen public schema."""
    instruction_fields = {f.name for f in dataclasses.fields(InstructionInfo)}
    assert instruction_fields == {"address", "length", "mnemonic", "operands"}

    assert dataclasses.is_dataclass(InstructionInfo)

    item = InstructionInfo(
        address=0x1000,
        length=4,
        mnemonic="MOV",
        operands="EAX, [RBP - 0x8]",
    )
    assert item.address == 0x1000
    assert item.length == 4
    assert item.mnemonic == "MOV"
    assert item.operands == "EAX, [RBP - 0x8]"

    with pytest.raises(FrozenInstanceError):
        item.mnemonic = "ADD"


def test_c010_enriched_instructions_schema_stability() -> None:
    """C-010: Enriched accepts instruction payloads alongside pcode."""
    empty = Enriched(pcode=None, instructions=None)
    assert empty.pcode is None
    assert empty.instructions is None

    instruction = InstructionInfo(
        address=0x2000,
        length=5,
        mnemonic="LEA",
        operands="RAX, [RBP - 0x10]",
    )
    enriched = Enriched(pcode=None, instructions=[instruction])
    assert enriched.instructions == [instruction]
