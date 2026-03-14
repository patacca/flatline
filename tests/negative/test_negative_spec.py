"""Negative tests for error-path and rejection behaviour (specs.md section 3.4)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from flatline import (
    ConfigurationError,
    DecompileRequest,
    DecompilerSession,
    InvalidArgumentError,
)
from tests._native_fixtures import get_native_fixture, open_native_session


@pytest.mark.requires_native
def test_n001_invalid_address_is_hard_failure(native_runtime_data_dir: str) -> None:
    """N-001: Invalid address returns structured `invalid_address` failure."""
    fixture = get_native_fixture("fx_add_elf64")
    request = replace(
        fixture.build_request(native_runtime_data_dir),
        function_address=fixture.base_address + len(fixture.memory_image()),
    )

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(request)

    assert result.error is not None
    assert result.error.category == "invalid_address"
    assert result.function_info is None
    assert result.c_code is None


@pytest.mark.requires_native
def test_n002_unsupported_language_id_is_rejected(native_runtime_data_dir: str) -> None:
    """N-002: Unknown language id returns structured `unsupported_target` failure."""
    fixture = get_native_fixture("fx_add_elf64")
    request = replace(
        fixture.build_request(native_runtime_data_dir),
        language_id="x86:LE:64:not-a-real-variant",
    )

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(request)

    assert result.error is not None
    assert result.error.category == "unsupported_target"
    assert result.function_info is None
    assert result.c_code is None


@pytest.mark.requires_native
def test_n003_unsupported_compiler_id_is_rejected(native_runtime_data_dir: str) -> None:
    """N-003: Unsupported compiler id for a known language is a hard failure."""
    fixture = get_native_fixture("fx_add_elf64")
    request = replace(
        fixture.build_request(native_runtime_data_dir),
        compiler_spec="not-a-real-compiler",
    )

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(request)

    assert result.error is not None
    assert result.error.category == "unsupported_target"
    assert result.function_info is None
    assert result.c_code is None


def test_n004_broken_runtime_data_dir_fails_startup(tmp_path) -> None:
    """N-004: Missing runtime data directory fails deterministically on startup."""
    missing_runtime_dir = tmp_path / "missing-runtime-data"

    with pytest.raises(ConfigurationError) as exc_info:
        DecompilerSession(runtime_data_dir=str(missing_runtime_dir))

    assert "runtime_data_dir does not exist" in exc_info.value.message


def test_n005_invalid_memory_image_is_rejected_at_request_construction() -> None:
    """N-005: Empty memory images raise `InvalidArgumentError` before decompile."""
    fixture = get_native_fixture("fx_add_elf64")

    with pytest.raises(InvalidArgumentError) as exc_info:
        DecompileRequest(
            memory_image=b"",
            base_address=fixture.base_address,
            function_address=fixture.function_address,
            language_id=fixture.language_id,
            compiler_spec=fixture.compiler_spec,
        )

    assert exc_info.value.category == "invalid_argument"
