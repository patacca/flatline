"""Regression tests for output and latency stability (specs.md section 4).

Guard against unintended changes in decompiler output or performance.
Auto-skipped when the native bridge is unavailable.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.requires_native

def _skip_spec_only() -> None:
    """Skip placeholder tests until runtime assertions are implemented."""
    pytest.skip("Spec-only skeleton; no runtime integration assertions in this phase")


def test_r001_simple_function_output_regression_guard():
    """R-001: Normalized output for baseline simple function remains stable."""
    _skip_spec_only()


def test_r002_jump_table_output_regression_guard():
    """R-002: Switch/jump-table structural output remains stable."""
    _skip_spec_only()


def test_r003_latency_budget_regression_guard():
    """R-003: Decompile latency stays within configured regression budget."""
    _skip_spec_only()


def test_r004_multi_isa_regression_baselines():
    """R-004: Per-ISA regression baselines (x86_32, ARM64, RISC-V 64, MIPS32) remain stable.
    Output matches normalized ISA-specific baseline. Parameterized over
    fx_add_elf32, fx_add_arm64, fx_add_riscv64, fx_add_mips32 fixtures."""
    _skip_spec_only()
