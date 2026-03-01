"""Negative tests for error-path and rejection behaviour (specs.md §3.4).

Verify that invalid inputs produce structured error responses, not crashes
or silent fallbacks. Skipped until the native bridge is available.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_n001_invalid_address_is_hard_failure():
    """N-001: Invalid address returns structured invalid_address failure.

    Asserts: error.category == 'invalid_address'; function_info is None;
    c_code is None. Must not downgrade to warning-only success."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_n002_unsupported_language_id_is_rejected():
    """N-002: Unknown language id returns structured unsupported_target failure.

    Asserts: error.category == 'unsupported_target'; function_info is None;
    c_code is None. No fallback language substitution."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_n003_unsupported_compiler_id_is_rejected():
    """N-003: Unsupported compiler id for known language is hard failure.

    Asserts: error.category == 'unsupported_target'; function_info is None;
    c_code is None. No implicit compiler fallback."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_n004_broken_runtime_data_dir_fails_startup():
    """N-004: Corrupt or missing runtime data directory fails deterministically."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_n005_invalid_memory_image_is_structured_error():
    """N-005: Empty or zero-length memory image returns structured invalid_argument failure.

    Asserts: error.category == 'invalid_argument'; function_info is None;
    c_code is None."""
