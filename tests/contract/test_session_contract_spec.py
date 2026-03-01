"""Contract tests for session and operation API shape (specs.md section 3.1, 3.2)."""

from __future__ import annotations

import inspect

from flatline import DecompilerSession, decompile_function, list_language_compilers


def test_c005_session_surface_contract() -> None:
    """C-005: DecompilerSession exposes stable lifecycle + operation methods."""
    required_methods = {"close", "decompile_function", "list_language_compilers"}
    for method_name in required_methods:
        assert hasattr(DecompilerSession, method_name)
        assert callable(getattr(DecompilerSession, method_name))


def test_c006_top_level_operation_functions_exist() -> None:
    """C-006: Public operation functions are exposed at package top level."""
    assert callable(decompile_function)
    assert callable(list_language_compilers)

    decompile_sig = inspect.signature(decompile_function)
    assert "request" in decompile_sig.parameters

    list_sig = inspect.signature(list_language_compilers)
    assert "runtime_data_dir" in list_sig.parameters
