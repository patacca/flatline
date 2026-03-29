"""Integration tests for end-to-end decompiler pipeline (specs.md section 4)."""

from __future__ import annotations

import networkx as nx
import pytest

from flatline import VALID_WARNING_PHASES, DecompileRequest, DiagnosticFlags
from tests._native_fixtures import (
    FIXTURE_IDS,
    MULTI_ISA_FIXTURE_IDS,
    assert_successful_result,
    get_native_fixture,
    normalize_c_code,
    open_native_session,
)

pytestmark = pytest.mark.requires_native

TRIMMED_SLICE_FIXTURE_IDS = ("fx_add_elf64", *MULTI_ISA_FIXTURE_IDS)

EXTERNAL_CALL_ARM64_BASE_ADDRESS = 0x1000
EXTERNAL_CALL_ARM64_HEX = (
    "fd7bbda9fd030091f35301a9f40300aaf51300f929ffff97c002003540008052b59cff97"
    "f50300aac29cff97806000f013b045f9130100b5e00315aac39cff97e00313aaf35341a9"
    "f51340f9fd7bc3a8c0035fd634ffffb4e00314aa610e40f9fce7d997a0feff34730a40f9"
    "f2ffff17130080d2f3ffff17"
)


def test_i001_known_function_success_path(native_runtime_data_dir: str) -> None:
    """I-001: Known function decompilation succeeds and yields non-empty C output."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(fixture.build_request(native_runtime_data_dir))

    assert_successful_result(result)
    assert result.c_code.strip() != ""
    assert result.enriched is None
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


def test_i008_opt_in_enriched_supports_graph_analysis(
    native_runtime_data_dir: str,
) -> None:
    """I-008: Opt-in enriched output exposes a traversable pcode graph."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert result.enriched is not None
    assert result.enriched.pcode is not None

    pcode = result.enriched.pcode
    assert pcode.pcode_ops
    assert pcode.varnodes

    graph = pcode.to_graph()
    assert isinstance(graph, nx.MultiDiGraph)

    add_ops = [op for op in pcode.pcode_ops if op.opcode == "INT_ADD"]
    return_ops = [op for op in pcode.pcode_ops if op.opcode == "RETURN"]
    assert len(add_ops) == 1
    assert return_ops

    add_output_id = add_ops[0].output_varnode_id
    assert add_output_id is not None

    descendants = nx.descendants(graph, ("varnode", add_output_id))
    assert any(("op", return_op.id) in descendants for return_op in return_ops)


@pytest.mark.parametrize("fixture_id", TRIMMED_SLICE_FIXTURE_IDS)
def test_i009_exact_function_slices_use_default_tail_padding(
    native_runtime_data_dir: str,
    fixture_id: str,
) -> None:
    """I-009: Exact function slices decompile without manual caller padding."""
    fixture = get_native_fixture(fixture_id)
    trimmed_image = fixture.memory_image()[: fixture.expected_function_size]
    request = DecompileRequest(
        memory_image=trimmed_image,
        base_address=fixture.base_address,
        function_address=fixture.function_address,
        language_id=fixture.language_id,
        compiler_spec=fixture.compiler_spec,
        runtime_data_dir=native_runtime_data_dir,
    )

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(request)

    assert_successful_result(result)
    assert normalize_c_code(result.c_code) == fixture.normalized_c


def test_i010_external_call_slice_respects_tail_padding_toggle(
    native_runtime_data_dir: str,
) -> None:
    """I-010: Default/custom tail padding fixes exact slices while disabling preserves failure."""
    memory_image = bytes.fromhex(EXTERNAL_CALL_ARM64_HEX)
    image_end = EXTERNAL_CALL_ARM64_BASE_ADDRESS + len(memory_image)
    default_request = DecompileRequest(
        memory_image=memory_image,
        base_address=EXTERNAL_CALL_ARM64_BASE_ADDRESS,
        function_address=EXTERNAL_CALL_ARM64_BASE_ADDRESS,
        language_id="AARCH64:LE:64:v8A",
        compiler_spec="default",
        runtime_data_dir=native_runtime_data_dir,
    )
    custom_padding_request = DecompileRequest(
        memory_image=memory_image,
        base_address=EXTERNAL_CALL_ARM64_BASE_ADDRESS,
        function_address=EXTERNAL_CALL_ARM64_BASE_ADDRESS,
        language_id="AARCH64:LE:64:v8A",
        compiler_spec="default",
        runtime_data_dir=native_runtime_data_dir,
        tail_padding=b"\x1f\x20\x03\xd5",
    )
    strict_request = DecompileRequest(
        memory_image=memory_image,
        base_address=EXTERNAL_CALL_ARM64_BASE_ADDRESS,
        function_address=EXTERNAL_CALL_ARM64_BASE_ADDRESS,
        language_id="AARCH64:LE:64:v8A",
        compiler_spec="default",
        runtime_data_dir=native_runtime_data_dir,
        tail_padding=b"",
    )

    with open_native_session(native_runtime_data_dir) as session:
        default_result = session.decompile_function(default_request)
        custom_padding_result = session.decompile_function(custom_padding_request)
        strict_result = session.decompile_function(strict_request)

    assert_successful_result(default_result)
    assert_successful_result(custom_padding_result)
    assert default_result.c_code.strip() != ""
    assert custom_padding_result.c_code.strip() != ""
    assert any(
        call_site.target_address is not None
        and (
            call_site.target_address < EXTERNAL_CALL_ARM64_BASE_ADDRESS
            or call_site.target_address >= image_end
        )
        for call_site in default_result.function_info.call_sites
    )
    assert normalize_c_code(custom_padding_result.c_code) == normalize_c_code(
        default_result.c_code
    )

    assert strict_result.error is not None
    assert strict_result.error.category == "invalid_address"
    assert strict_result.function_info is None
    assert strict_result.c_code is None
