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
    fixture = get_native_fixture("fx_external_call_arm64")
    memory_image = fixture.memory_image()[: fixture.expected_function_size]
    image_end = fixture.base_address + len(memory_image)
    default_request = DecompileRequest(
        memory_image=memory_image,
        base_address=fixture.base_address,
        function_address=fixture.function_address,
        language_id=fixture.language_id,
        compiler_spec=fixture.compiler_spec,
        runtime_data_dir=native_runtime_data_dir,
    )
    custom_padding_request = DecompileRequest(
        memory_image=memory_image,
        base_address=fixture.base_address,
        function_address=fixture.function_address,
        language_id=fixture.language_id,
        compiler_spec=fixture.compiler_spec,
        runtime_data_dir=native_runtime_data_dir,
        tail_padding=b"\x1f\x20\x03\xd5",  # Aarch64 NOP
    )
    strict_request = DecompileRequest(
        memory_image=memory_image,
        base_address=fixture.base_address,
        function_address=fixture.function_address,
        language_id=fixture.language_id,
        compiler_spec=fixture.compiler_spec,
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
            call_site.target_address < fixture.base_address
            or call_site.target_address >= image_end
        )
        for call_site in default_result.function_info.call_sites
    )
    assert normalize_c_code(default_result.c_code) == fixture.normalized_c
    assert normalize_c_code(custom_padding_result.c_code) == normalize_c_code(
        default_result.c_code
    )

    assert strict_result.error is not None
    assert strict_result.error.category == "invalid_address"
    assert strict_result.function_info is None
    assert strict_result.c_code is None


def test_i011_cbranch_target_addresses_on_warning_fixture(
    native_runtime_data_dir: str,
) -> None:
    """I-011: CBRANCH ops expose true/false target addresses on warning fixture."""
    fixture = get_native_fixture("fx_warning_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert result.enriched is not None
    assert result.enriched.pcode is not None

    pcode = result.enriched.pcode
    cbranch_ops = [op for op in pcode.pcode_ops if op.opcode == "CBRANCH"]

    assert len(cbranch_ops) >= 1, "Expected at least one CBRANCH op in warning fixture"

    for op in cbranch_ops:
        assert op.true_target_address is not None, (
            f"CBRANCH op {op.id} missing true_target_address"
        )
        assert op.false_target_address is not None, (
            f"CBRANCH op {op.id} missing false_target_address"
        )
        assert op.true_target_address != op.false_target_address, (
            f"CBRANCH op {op.id} has identical true/false targets"
        )

    non_cbranch_ops = [op for op in pcode.pcode_ops if op.opcode != "CBRANCH"]
    for op in non_cbranch_ops:
        assert op.true_target_address is None, (
            f"Non-CBRANCH op {op.id} ({op.opcode}) has non-None true_target_address"
        )
        assert op.false_target_address is None, (
            f"Non-CBRANCH op {op.id} ({op.opcode}) has non-None false_target_address"
        )


def test_i012_fspec_iop_fields_on_external_call_fixture(
    native_runtime_data_dir: str,
) -> None:
    """I-012: FSPEC varnodes expose call_site_index; IOP varnodes expose target_op_id."""
    fixture = get_native_fixture("fx_external_call_arm64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert result.enriched is not None
    assert result.enriched.pcode is not None

    pcode = result.enriched.pcode

    # Find fspec varnodes (call-site references)
    fspec_varnodes = [vn for vn in pcode.varnodes if vn.space == "fspec"]
    if fspec_varnodes:
        for vn in fspec_varnodes:
            assert vn.call_site_index is not None, f"fspec varnode {vn.id} missing call_site_index"
            assert vn.offset == 0, f"fspec varnode {vn.id} should have offset=0"
            # Cross-validate: call_site_index must be valid
            assert vn.call_site_index < len(result.function_info.call_sites), (
                f"call_site_index {vn.call_site_index} out of range "
                f"(only {len(result.function_info.call_sites)} call sites)"
            )

    # Find iop varnodes (internal op pointers)
    iop_varnodes = [vn for vn in pcode.varnodes if vn.space == "iop"]
    if iop_varnodes:
        for vn in iop_varnodes:
            assert vn.target_op_id is not None, f"iop varnode {vn.id} missing target_op_id"
            assert vn.offset == 0, f"iop varnode {vn.id} should have offset=0"
            # Cross-validate: target_op_id must resolve
            target_op = pcode.get_pcode_op(vn.target_op_id)
            assert target_op is not None, (
                f"target_op_id {vn.target_op_id} does not resolve to valid pcode op"
            )


def test_i013_backward_compatibility_new_fields_default_none(
    native_runtime_data_dir: str,
) -> None:
    """I-013: New enrichment fields default to None on simple fixture without calls/branches."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert result.enriched is not None
    assert result.enriched.pcode is not None

    pcode = result.enriched.pcode

    # Simple add function has no calls, no indirect ops, no conditional branches
    fspec_varnodes = [vn for vn in pcode.varnodes if vn.space == "fspec"]
    iop_varnodes = [vn for vn in pcode.varnodes if vn.space == "iop"]
    cbranch_ops = [op for op in pcode.pcode_ops if op.opcode == "CBRANCH"]

    assert len(fspec_varnodes) == 0, "Simple add function should have no fspec varnodes"
    assert len(iop_varnodes) == 0, "Simple add function should have no iop varnodes"
    assert len(cbranch_ops) == 0, "Simple add function should have no CBRANCH ops"

    # All varnodes must have new fields as None
    for vn in pcode.varnodes:
        assert vn.call_site_index is None, (
            f"varnode {vn.id} in space '{vn.space}' has non-None call_site_index"
        )
        assert vn.target_op_id is None, (
            f"varnode {vn.id} in space '{vn.space}' has non-None target_op_id"
        )

    # All ops must have target addresses as None
    for op in pcode.pcode_ops:
        assert op.true_target_address is None, (
            f"op {op.id} ({op.opcode}) has non-None true_target_address"
        )
        assert op.false_target_address is None, (
            f"op {op.id} ({op.opcode}) has non-None false_target_address"
        )
