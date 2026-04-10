"""Regression tests for output and latency stability (specs.md section 4)."""

from __future__ import annotations

from math import ceil
from time import perf_counter

import pytest
from flatline.models.enums import PcodeOpcode

from tests._native_fixtures import (
    MULTI_ISA_FIXTURE_IDS,
    PERFORMANCE_FIXTURE_IDS,
    assert_successful_result,
    get_native_fixture,
    normalize_c_code,
    open_native_session,
)

pytestmark = pytest.mark.requires_native


def _p95(samples: list[float]) -> float:
    index = ceil(len(samples) * 0.95) - 1
    return sorted(samples)[index]


def test_r001_simple_function_output_regression_guard(native_runtime_data_dir: str) -> None:
    """R-001: Normalized output for baseline simple function remains stable."""
    fixture = get_native_fixture("fx_add_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(fixture.build_request(native_runtime_data_dir))

    assert_successful_result(result)
    assert normalize_c_code(result.c_code) == fixture.normalized_c
    assert result.function_info.varnode_count == fixture.expected_varnode_count


def test_r002_jump_table_output_regression_guard(native_runtime_data_dir: str) -> None:
    """R-002: Switch/jump-table structural output remains stable."""
    fixture = get_native_fixture("fx_switch_elf64")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(fixture.build_request(native_runtime_data_dir))

    assert_successful_result(result)
    assert normalize_c_code(result.c_code) == fixture.normalized_c
    assert result.function_info.jump_tables
    jump_table = result.function_info.jump_tables[0]
    assert jump_table.switch_address == fixture.expected_jump_table_switch_address
    assert jump_table.target_count == len(fixture.expected_jump_table_targets)
    assert tuple(jump_table.target_addresses) == fixture.expected_jump_table_targets


@pytest.mark.parametrize("fixture_id", PERFORMANCE_FIXTURE_IDS)
def test_r003_latency_budget_regression_guard(
    native_runtime_data_dir: str,
    fixture_id: str,
) -> None:
    """R-003: Warm-session decompile latency stays within fixture budgets."""
    fixture = get_native_fixture(fixture_id)
    budget = fixture.warm_p95_budget_seconds
    assert budget is not None

    with open_native_session(native_runtime_data_dir) as session:
        request = fixture.build_request(native_runtime_data_dir)
        session.decompile_function(request)
        samples: list[float] = []
        for _ in range(20):
            started = perf_counter()
            result = session.decompile_function(request)
            samples.append(perf_counter() - started)
            assert_successful_result(result)

    measured_p95 = _p95(samples)
    assert measured_p95 < budget, (
        f"{fixture.fixture_id} p95 {measured_p95:.6f}s exceeded budget {budget:.6f}s"
    )


@pytest.mark.parametrize("fixture_id", MULTI_ISA_FIXTURE_IDS)
def test_r004_multi_isa_regression_baselines(
    native_runtime_data_dir: str,
    fixture_id: str,
) -> None:
    """R-004: Per-ISA regression baselines remain stable."""
    fixture = get_native_fixture(fixture_id)

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(fixture.build_request(native_runtime_data_dir))

    assert_successful_result(result)
    assert normalize_c_code(result.c_code) == fixture.normalized_c
    assert result.function_info.varnode_count == fixture.expected_varnode_count


def test_r005_delay_slot_branch_alias_regression_guard(native_runtime_data_dir: str) -> None:
    fixture = get_native_fixture("fx_delay_slot_branch_mips32")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert normalize_c_code(result.c_code) == fixture.normalized_c
    assert result.function_info.varnode_count == fixture.expected_varnode_count
    assert result.enriched is not None
    assert result.enriched.pcode is not None

    multiequal_ops = [
        op for op in result.enriched.pcode.pcode_ops if op.opcode == PcodeOpcode.MULTIEQUAL
    ]
    opcode_sequence = [op.opcode for op in result.enriched.pcode.pcode_ops]

    assert multiequal_ops, "Expected a canonical MULTIEQUAL op from BUILD alias handling"
    assert len(multiequal_ops) == 1
    assert opcode_sequence == [
        PcodeOpcode.INT_NOTEQUAL,
        PcodeOpcode.COPY,
        PcodeOpcode.CBRANCH,
        PcodeOpcode.COPY,
        PcodeOpcode.RETURN,
        PcodeOpcode.MULTIEQUAL,
    ]


def test_r006_delay_slot_call_alias_regression_guard(native_runtime_data_dir: str) -> None:
    fixture = get_native_fixture("fx_delay_slot_call_mips32")

    with open_native_session(native_runtime_data_dir) as session:
        result = session.decompile_function(
            fixture.build_request(native_runtime_data_dir, enriched=True)
        )

    assert_successful_result(result)
    assert normalize_c_code(result.c_code) == fixture.normalized_c
    assert result.function_info.varnode_count == fixture.expected_varnode_count
    assert result.enriched is not None
    assert result.enriched.pcode is not None

    indirect_ops = [
        op for op in result.enriched.pcode.pcode_ops if op.opcode == PcodeOpcode.INDIRECT
    ]
    opcode_sequence = [op.opcode for op in result.enriched.pcode.pcode_ops]

    assert indirect_ops, "Expected a canonical INDIRECT op from DELAY_SLOT alias handling"
    assert len(indirect_ops) == 1
    assert opcode_sequence == [
        PcodeOpcode.COPY,
        PcodeOpcode.CALL,
        PcodeOpcode.INDIRECT,
        PcodeOpcode.COPY,
        PcodeOpcode.RETURN,
    ]
