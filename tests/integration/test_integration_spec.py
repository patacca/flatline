"""Integration tests for end-to-end decompiler pipeline (specs.md section 4)."""

from __future__ import annotations

import pytest

from flatline import VALID_WARNING_PHASES, DiagnosticFlags
from tests._native_fixtures import (
    FIXTURE_IDS,
    MULTI_ISA_FIXTURE_IDS,
    assert_successful_result,
    get_native_fixture,
    normalize_c_code,
    open_native_session,
)

pytestmark = pytest.mark.requires_native


def test_i001_known_function_success_path(native_runtime_data_dir: str) -> None:
    """I-001: Known function decompilation succeeds and yields non-empty C output."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(fixture.build_request(native_runtime_data_dir))

    assert_successful_result(result)
    assert result.c_code.strip() != ""
    assert normalize_c_code(result.c_code) == fixture.normalized_c


def test_i002_language_compiler_enumeration_validity(native_runtime_data_dir: str) -> None:
    """I-002: Enumerated language/compiler pairs are valid for available runtime data."""
    with open_native_session(native_runtime_data_dir) as session:
        pairs = session.list_language_compilers()

    assert pairs
    pair_set = {(pair.language_id, pair.compiler_spec) for pair in pairs}
    for fixture_id in FIXTURE_IDS:
        fixture = get_native_fixture(fixture_id)
        assert (fixture.language_id, fixture.compiler_spec) in pair_set


def test_i003_sequential_session_isolation(native_runtime_data_dir: str) -> None:
    """I-003: Sequential sessions do not leak warnings, config, or metadata state."""
    warning_fixture = get_native_fixture("fx_warning_elf64")
    add_fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        warning_result = session.decompile_function(
            warning_fixture.build_request(native_runtime_data_dir)
        )
    with open_native_session(native_runtime_data_dir) as session:
        add_result = session.decompile_function(add_fixture.build_request(native_runtime_data_dir))

    assert_successful_result(warning_result)
    assert len(warning_result.warnings) == warning_fixture.expected_warning_count
    assert_successful_result(add_result)
    assert add_result.warnings == []
    assert add_result.metadata["language_id"] == add_fixture.language_id
    assert add_result.metadata["compiler_spec"] == add_fixture.compiler_spec
    assert normalize_c_code(add_result.c_code) == add_fixture.normalized_c


def test_i004_startup_and_minimal_load_smoke_path(native_runtime_data_dir: str) -> None:
    """I-004: Startup/runtime-data initialization and minimal load path remain deterministic."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        pairs_first = session.list_language_compilers()
    with open_native_session(native_runtime_data_dir) as session:
        pairs_second = session.list_language_compilers()
        result = session.decompile_function(fixture.build_request(native_runtime_data_dir))

    assert pairs_first == pairs_second
    assert pairs_first
    assert_successful_result(result)
    assert result.metadata["decompiler_version"]
    assert result.metadata["language_id"] == fixture.language_id
    assert result.metadata["compiler_spec"] == fixture.compiler_spec


def test_i005_known_function_produces_function_info(native_runtime_data_dir: str) -> None:
    """I-005: Known function decompile produces populated `FunctionInfo`."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(fixture.build_request(native_runtime_data_dir))

    assert_successful_result(result)
    info = result.function_info
    assert info.size == fixture.expected_function_size
    assert info.is_complete is True
    assert len(info.prototype.parameters) == fixture.expected_param_count
    assert info.prototype.return_type.name == fixture.expected_return_type_name
    assert info.prototype.return_type.size == fixture.expected_return_type_size
    assert info.prototype.return_type.metatype == fixture.expected_return_type_metatype
    assert info.diagnostics == DiagnosticFlags(
        is_complete=True,
        has_unreachable_blocks=False,
        has_unimplemented=False,
        has_bad_data=False,
        has_no_code=False,
    )
    assert info.varnode_count == fixture.expected_varnode_count


@pytest.mark.parametrize("fixture_id", MULTI_ISA_FIXTURE_IDS)
def test_i006_multi_isa_known_function(
    native_runtime_data_dir: str,
    fixture_id: str,
) -> None:
    """I-006: Priority-ISA fixtures decompile independently with expected output."""
    fixture = get_native_fixture(fixture_id)

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(fixture.build_request(native_runtime_data_dir))

    assert_successful_result(result)
    assert result.function_info.size == fixture.expected_function_size
    assert result.function_info.varnode_count == fixture.expected_varnode_count
    assert normalize_c_code(result.c_code) == fixture.normalized_c


def test_i007_warning_only_success_with_warning_structure(
    native_runtime_data_dir: str,
) -> None:
    """I-007: Decompilation with warnings still reports success."""
    fixture = get_native_fixture("fx_warning_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(fixture.build_request(native_runtime_data_dir))

    assert_successful_result(result)
    assert result.c_code.strip() != ""
    assert result.function_info.size == fixture.expected_function_size
    assert len(result.warnings) == fixture.expected_warning_count
    for warning in result.warnings:
        assert isinstance(warning.code, str) and warning.code
        assert isinstance(warning.message, str) and warning.message
        assert isinstance(warning.phase, str)
        assert warning.phase in VALID_WARNING_PHASES
