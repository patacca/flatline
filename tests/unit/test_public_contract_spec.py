import pytest


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_u001_request_schema_required_fields():
    """U-001: Missing required request fields map to structured invalid_argument errors."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_u002_unknown_compiler_rejected_without_fallback():
    """U-002: Unknown compiler identifiers are hard failures, never implicit fallback."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_u003_result_metadata_required_keys():
    """U-003: Result metadata always includes required top-level keys."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_u004_function_size_hint_passthrough():
    """U-004: function_size_hint is accepted and passed through; omission does not error."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_u005_function_info_fields_from_stub():
    """U-005: FunctionInfo fields are populated from adapter stub with correct types.

    Validates: FunctionInfo required fields present; DiagnosticFlags aggregation
    matches individual flag values; TypeInfo metatype is a valid stable string."""
