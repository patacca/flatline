"""Negative tests for error-path and rejection behaviour (specs.md section 3.4).

Verify that invalid inputs produce structured error responses, not crashes
or silent fallbacks. Auto-skipped when the native bridge is unavailable.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.requires_native

def _skip_spec_only() -> None:
    """Skip placeholder tests until runtime assertions are implemented."""
    pytest.skip("Spec-only skeleton; no runtime integration assertions in this phase")


def test_n001_invalid_address_is_hard_failure():
    """N-001: Invalid address returns structured invalid_address failure.

    Asserts: error.category == 'invalid_address'; function_info is None;
    c_code is None. Must not downgrade to warning-only success."""
    _skip_spec_only()


def test_n002_unsupported_language_id_is_rejected():
    """N-002: Unknown language id returns structured unsupported_target failure.

    Asserts: error.category == 'unsupported_target'; function_info is None;
    c_code is None. No fallback language substitution."""
    _skip_spec_only()


def test_n003_unsupported_compiler_id_is_rejected():
    """N-003: Unsupported compiler id for known language is hard failure.

    Asserts: error.category == 'unsupported_target'; function_info is None;
    c_code is None. No implicit compiler fallback."""
    _skip_spec_only()


def test_n004_broken_runtime_data_dir_fails_startup():
    """N-004: Corrupt or missing runtime data directory fails deterministically."""
    _skip_spec_only()


def test_n005_invalid_memory_image_is_structured_error():
    """N-005: Empty or zero-length memory image returns structured invalid_argument failure.

    Asserts: error.category == 'invalid_argument'; function_info is None;
    c_code is None."""
    _skip_spec_only()
