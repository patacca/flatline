import pytest


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_n001_invalid_address_is_hard_failure():
    """N-001: Invalid address returns structured invalid_address failure."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_n002_unsupported_language_id_is_rejected():
    """N-002: Unknown language id returns structured unsupported-target failure."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_n003_unsupported_compiler_id_is_rejected():
    """N-003: Unsupported compiler id for known language is hard failure."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_n004_broken_runtime_data_dir_fails_startup():
    """N-004: Corrupt or missing runtime data directory fails deterministically."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_n005_binary_load_failure_is_structured_error():
    """N-005: Corrupt or unreadable binary target returns structured invalid_argument failure."""
