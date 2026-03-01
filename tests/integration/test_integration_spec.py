"""Integration tests for end-to-end decompiler pipeline (specs.md §4).

Each test exercises the full request-bridge-decompile-result path against
real Ghidra runtime data. Skipped until the native bridge is available.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_i001_known_function_success_path():
    """I-001: Known function decompilation succeeds and yields non-empty C output."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_i002_language_compiler_enumeration_validity():
    """I-002: Enumerated language/compiler pairs are valid for available runtime data."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_i003_sequential_session_isolation():
    """I-003: Sequential sessions do not leak warnings, config, or metadata state."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_i004_startup_and_minimal_load_smoke_path():
    """I-004: Startup/runtime-data initialization and minimal load path remain deterministic."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_i005_known_function_produces_function_info():
    """I-005: Known function decompile produces populated FunctionInfo with expected
    prototype shape (parameter count, return type), diagnostics flags, and non-zero
    varnode_count."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_i006_multi_isa_known_function():
    """I-006: Known function decompilation succeeds for each additional priority ISA variant
    (x86_32, ARM64, RISC-V 64, MIPS32) with non-empty C output and populated function_info.
    Parameterized over fx_add_elf32, fx_add_arm64, fx_add_riscv64, fx_add_mips32 fixtures."""


@pytest.mark.skip(reason="Spec-only skeleton; no runtime integration in this phase")
def test_i007_warning_only_success_with_warning_structure():
    """I-007: Decompilation that produces warnings still reports success.

    Uses fx_warning_elf64 fixture (function with unreachable blocks or unimplemented
    instructions). Validates: c_code is non-empty; error is None; function_info is
    populated; warnings list is non-empty; each WarningItem has code (str), message
    (str), phase (str from {init, analyze, emit}). Covers specs.md §3.4 warning-only
    success invariant and §3.3 WarningItem structure."""
