"""Contract tests for API schema and taxonomy stability (specs.md section 3, 3.4, 3.5).

These tests verify that public types, field names, error categories, and version
metadata remain stable across releases -- the contract-level guarantees that
downstream code depends on. No native bridge required.
"""

from __future__ import annotations

import dataclasses

from flatline import (
    CATEGORY_TO_EXCEPTION,
    ERROR_CATEGORIES,
    VALID_METATYPES,
    VALID_WARNING_PHASES,
    AnalysisBudget,
    CallSiteInfo,
    DecompileFailedError,
    DecompileResult,
    DiagnosticFlags,
    ErrorItem,
    FlatlineError,
    FunctionInfo,
    FunctionPrototype,
    InternalError,
    InvalidAddressError,
    InvalidArgumentError,
    JumpTableInfo,
    LanguageCompilerPair,
    ParameterInfo,
    StorageInfo,
    TypeInfo,
    UnsupportedTargetError,
    VariableInfo,
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
    assert result_fields == {"c_code", "function_info", "warnings", "error", "metadata"}

    # FunctionInfo required fields
    info_fields = {f.name for f in dataclasses.fields(FunctionInfo)}
    expected_info = {
        "name", "entry_address", "size", "is_complete", "prototype",
        "local_variables", "call_sites", "jump_tables", "diagnostics",
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
    # Exactly 5 categories defined (specs.md section 3.4)
    expected_categories = {
        "invalid_argument",
        "unsupported_target",
        "invalid_address",
        "decompile_failed",
        "internal_error",
    }
    assert expected_categories == ERROR_CATEGORIES

    # Each category maps to a unique exception class
    assert set(CATEGORY_TO_EXCEPTION.keys()) == expected_categories
    assert len(set(CATEGORY_TO_EXCEPTION.values())) == 5

    # All exception classes inherit from FlatlineError
    for category, exc_cls in CATEGORY_TO_EXCEPTION.items():
        assert issubclass(exc_cls, FlatlineError)
        assert exc_cls.category == category

    # Direct class-level category verification
    assert InvalidArgumentError.category == "invalid_argument"
    assert UnsupportedTargetError.category == "unsupported_target"
    assert InvalidAddressError.category == "invalid_address"
    assert DecompileFailedError.category == "decompile_failed"
    assert InternalError.category == "internal_error"

    # Instance .message property works
    exc = InvalidArgumentError("test message")
    assert exc.message == "test message"
    assert str(exc) == "test message"


# ---------------------------------------------------------------------------
# C-003: Version reporting contract
# ---------------------------------------------------------------------------

def test_c003_version_reporting_contains_upstream_pin():
    """C-003: Version endpoint includes flatline and upstream pin information."""
    info = get_version_info()

    assert isinstance(info, VersionInfo)

    # All required fields populated (specs.md section 3.3 VersionInfo)
    assert isinstance(info.flatline_version, str) and info.flatline_version
    assert isinstance(info.upstream_tag, str) and info.upstream_tag
    assert isinstance(info.upstream_commit, str) and info.upstream_commit
    assert isinstance(info.runtime_data_revision, str)

    # Pin matches known baseline (docs/roadmap.md section 0)
    assert info.upstream_tag == "Ghidra_12.0.4_build"
    assert info.upstream_commit == "e40ed13014025f82488b1f8f7bca566894ac376b"

    # VersionInfo fields match spec
    version_fields = {f.name for f in dataclasses.fields(VersionInfo)}
    assert version_fields == {
        "flatline_version", "upstream_tag", "upstream_commit", "runtime_data_revision",
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
        "calling_convention", "parameters", "return_type",
        "is_noreturn", "has_this_pointer", "has_input_errors", "has_output_errors",
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
        "is_complete", "has_unreachable_blocks", "has_unimplemented",
        "has_bad_data", "has_no_code",
    }

    budget_fields = {f.name for f in dataclasses.fields(AnalysisBudget)}
    assert budget_fields == {"max_instructions"}

    # LanguageCompilerPair fields
    pair_fields = {f.name for f in dataclasses.fields(LanguageCompilerPair)}
    assert pair_fields == {"language_id", "compiler_spec"}

    # Metatype strings are the stable enum values (specs.md section 3.3)
    expected_metatypes = {
        "void", "bool", "int", "uint", "float", "pointer",
        "array", "struct", "union", "code", "enum", "unknown",
    }
    assert expected_metatypes == VALID_METATYPES

    # Warning phases are the stable set
    assert {"init", "analyze", "emit"} == VALID_WARNING_PHASES

    # All structured result types are frozen dataclasses
    frozen_types = [
        AnalysisBudget,
        StorageInfo, TypeInfo, ParameterInfo, VariableInfo, CallSiteInfo,
        JumpTableInfo, DiagnosticFlags, FunctionPrototype, FunctionInfo,
        WarningItem, ErrorItem, VersionInfo, LanguageCompilerPair,
    ]
    for cls in frozen_types:
        assert dataclasses.is_dataclass(cls), f"{cls.__name__} must be a dataclass"
        # Verify frozen by checking __dataclass_params__
        assert cls.__dataclass_params__.frozen, f"{cls.__name__} must be frozen"
