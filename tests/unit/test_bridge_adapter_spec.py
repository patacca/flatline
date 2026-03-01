"""Unit tests for bridge adapter behavior (specs.md section 3.2, section 6)."""

from __future__ import annotations

from typing import Any

import pytest

from flatline import DecompileRequest, DecompileResult, FunctionInfo, LanguageCompilerPair
from flatline import _bridge as bridge_module


class _NativeSessionSuccessDouble:
    """Native-session test double with tuple/list return shapes."""

    def __init__(self) -> None:
        self.closed = False
        self.last_request_payload: dict[str, Any] | None = None

    def close(self) -> None:
        self.closed = True

    def list_language_compilers(self) -> list[tuple[str, str]]:
        return [("x86:LE:64:default", "gcc")]

    def decompile_function(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        self.last_request_payload = request_payload
        return {
            "c_code": "int add(int a, int b) { return a + b; }",
            "function_info": {
                "name": "add",
                "entry_address": 0x1000,
                "size": 16,
                "is_complete": True,
                "prototype": {
                    "calling_convention": "__cdecl",
                    "parameters": [
                        {
                            "name": "a",
                            "type": {"name": "int", "size": 4, "metatype": "int"},
                            "index": 0,
                            "storage": None,
                        },
                        {
                            "name": "b",
                            "type": {"name": "int", "size": 4, "metatype": "int"},
                            "index": 1,
                            "storage": None,
                        },
                    ],
                    "return_type": {"name": "int", "size": 4, "metatype": "int"},
                    "is_noreturn": False,
                    "has_this_pointer": False,
                    "has_input_errors": False,
                    "has_output_errors": False,
                },
                "local_variables": [],
                "call_sites": [],
                "jump_tables": [],
                "diagnostics": {
                    "is_complete": True,
                    "has_unreachable_blocks": False,
                    "has_unimplemented": False,
                    "has_bad_data": False,
                    "has_no_code": False,
                },
                "varnode_count": 24,
            },
            "warnings": [
                {
                    "code": "analyze.W001",
                    "message": "synthetic warning",
                    "phase": "analyze",
                }
            ],
            "error": None,
            "metadata": {
                "decompiler_version": "0.1.0-dev",
                "language_id": request_payload["language_id"],
                "compiler_spec": request_payload["compiler_spec"],
                "diagnostics": {},
            },
        }


class _NativeSessionFailureDouble:
    """Native-session test double that raises in decompile."""

    def list_language_compilers(self) -> list[tuple[str, str]]:
        return [("x86:LE:64:default", "gcc")]

    def decompile_function(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("native bridge failure")

    def close(self) -> None:
        return None


class _NativeModuleDouble:
    """Module-level test double exposing create_session."""

    def __init__(self, native_session: Any) -> None:
        self.native_session = native_session
        self.runtime_data_dir: str | None = None

    def create_session(self, runtime_data_dir: str | None = None) -> Any:
        self.runtime_data_dir = runtime_data_dir
        return self.native_session


def test_u010_bridge_session_fallback_when_native_module_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U-010: Missing native extension falls back to deterministic Python bridge."""

    def _raise_import_error(_: str) -> Any:
        raise ImportError("module not found")

    monkeypatch.setattr(bridge_module.importlib, "import_module", _raise_import_error)

    bridge_session = bridge_module.create_bridge_session(runtime_data_dir="/tmp/runtime")
    assert isinstance(bridge_session, bridge_module._FallbackBridgeSession)


def test_u011_bridge_session_adapts_native_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    """U-011: Native tuple/dict payloads are adapted to public model types."""
    native_session = _NativeSessionSuccessDouble()
    native_module = _NativeModuleDouble(native_session=native_session)

    monkeypatch.setattr(
        bridge_module.importlib,
        "import_module",
        lambda _: native_module,
    )

    bridge_session = bridge_module.create_bridge_session(runtime_data_dir="/tmp/runtime")
    assert native_module.runtime_data_dir == "/tmp/runtime"

    pairs = bridge_session.list_language_compilers()
    assert pairs == [LanguageCompilerPair(language_id="x86:LE:64:default", compiler_spec="gcc")]

    request = DecompileRequest(
        memory_image=b"\x90\xc3",
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
        compiler_spec="gcc",
    )
    result = bridge_session.decompile_function(request)

    assert isinstance(result, DecompileResult)
    assert result.error is None
    assert isinstance(result.function_info, FunctionInfo)
    assert result.metadata["language_id"] == "x86:LE:64:default"
    assert native_session.last_request_payload is not None
    assert native_session.last_request_payload["memory_image"] == b"\x90\xc3"
    assert native_session.last_request_payload["base_address"] == 0x1000
    assert native_session.last_request_payload["function_address"] == 0x1000

    bridge_session.close()
    assert native_session.closed is True


def test_u012_bridge_session_normalizes_native_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """U-012: Native bridge exceptions become structured internal_error results."""
    native_module = _NativeModuleDouble(native_session=_NativeSessionFailureDouble())
    monkeypatch.setattr(
        bridge_module.importlib,
        "import_module",
        lambda _: native_module,
    )

    bridge_session = bridge_module.create_bridge_session()
    request = DecompileRequest(
        memory_image=b"\x90\xc3",
        base_address=0x400000,
        function_address=0x400000,
        language_id="x86:LE:64:default",
    )
    result = bridge_session.decompile_function(request)

    assert isinstance(result, DecompileResult)
    assert result.error is not None
    assert result.error.category == "internal_error"
    assert "native bridge failure" in result.error.message
    assert result.function_info is None
    assert result.c_code is None
    assert result.metadata["language_id"] == request.language_id
