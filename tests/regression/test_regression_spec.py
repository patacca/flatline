"""Regression tests for output and latency stability (specs.md section 4)."""

from __future__ import annotations

from math import ceil
from time import perf_counter

import pytest

from tests._native_fixtures import (
    MULTI_ISA_FIXTURE_IDS,
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
    assert jump_table.target_count == len(fixture.expected_jump_table_targets)
    assert tuple(jump_table.target_addresses) == fixture.expected_jump_table_targets


def test_r003_latency_budget_regression_guard(native_runtime_data_dir: str) -> None:
    """R-003: Decompile latency stays within the gross regression budget."""
    add_fixture = get_native_fixture("fx_add_elf64")
    switch_fixture = get_native_fixture("fx_switch_elf64")
    thresholds = {
        add_fixture.fixture_id: 0.25,
        switch_fixture.fixture_id: 0.25,
    }

    with open_native_session(native_runtime_data_dir) as session:
        for fixture in (add_fixture, switch_fixture):
            request = fixture.build_request(native_runtime_data_dir)
            session.decompile_function(request)
            samples: list[float] = []
            for _ in range(20):
                started = perf_counter()
                result = session.decompile_function(request)
                samples.append(perf_counter() - started)
                assert_successful_result(result)
            assert _p95(samples) < thresholds[fixture.fixture_id]


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
