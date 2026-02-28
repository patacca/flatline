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
