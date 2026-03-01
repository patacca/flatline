import pytest


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_c001_result_schema_stability():
    """C-001: Required result keys/types remain stable across compatible releases."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_c002_error_taxonomy_stability():
    """C-002: Error categories are contract-stable identifiers."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_c003_version_reporting_contains_upstream_pin():
    """C-003: Version endpoint includes ghidralib and upstream pin information."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_c004_structured_result_schema_stability():
    """C-004: Structured result objects (FunctionInfo, FunctionPrototype, TypeInfo)
    have stable required fields and types. Metatype strings are stable enum values."""
