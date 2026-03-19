"""Unit tests for bridge adapter behavior (specs.md section 3.2, section 6)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from flatline import (
    AnalysisBudget,
    ConfigurationError,
    DecompileRequest,
    DecompileResult,
    FunctionInfo,
    LanguageCompilerPair,
)
from flatline import _bridge as bridge_module
from flatline._version import DECOMPILER_VERSION


class _NativeSessionSuccessDouble:
    """Native-session test double with tuple/list return shapes."""

    def __init__(self) -> None:
        self.closed = False
        self.last_request_payload: dict[str, Any] | None = None
        self.decompile_calls = 0

    def close(self) -> None:
        self.closed = True

    def list_language_compilers(self) -> list[tuple[str, str]]:
        return [("x86:LE:64:default", "gcc")]

    def decompile_function(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        self.decompile_calls += 1
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
                "decompiler_version": DECOMPILER_VERSION,
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
        raise RuntimeError("native bridge failure at /tmp/native/session.log")

    def close(self) -> None:
        return None


class _NativeSessionInvalidSuccessShapeDouble:
    """Native-session test double returning a malformed success payload."""

    def list_language_compilers(self) -> list[tuple[str, str]]:
        return [("x86:LE:64:default", "gcc")]

    def decompile_function(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "c_code": "int add(int a, int b) { return a + b; }",
            "function_info": None,
            "warnings": [],
            "error": None,
            "metadata": {
                "decompiler_version": DECOMPILER_VERSION,
                "language_id": request_payload["language_id"],
                "compiler_spec": request_payload["compiler_spec"] or "",
                "diagnostics": {},
            },
        }

    def close(self) -> None:
        return None


class _NativeSessionEmptyEnumerationDouble:
    """Native-session double with empty enumeration output.

    Used to verify runtime-data-backed fallback enumeration in bridge adapters.
    """

    def __init__(self) -> None:
        self.decompile_calls = 0

    def list_language_compilers(self) -> list[tuple[str, str]]:
        return []

    def decompile_function(self, request_payload: dict[str, Any]) -> dict[str, Any]:
        self.decompile_calls += 1
        return {
            "c_code": None,
            "function_info": None,
            "warnings": [],
            "error": {
                "category": "internal_error",
                "message": "native bridge skeleton: decompile pipeline not implemented",
                "retryable": False,
            },
            "metadata": {
                "decompiler_version": DECOMPILER_VERSION,
                "language_id": request_payload["language_id"],
                "compiler_spec": request_payload["compiler_spec"] or "",
                "diagnostics": {},
            },
        }

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


def _make_runtime_data_fixture(tmp_path: Path) -> Path:
    """Create a synthetic runtime-data directory with one valid pair.

    Includes one compiler entry whose backing spec file exists and one whose
    spec file is missing, allowing existence filtering assertions.
    """
    runtime_dir = tmp_path / "runtime_data"
    language_dir = runtime_dir / "languages"
    language_dir.mkdir(parents=True)

    (language_dir / "x86-gcc.cspec").write_text("<compiler_spec/>", encoding="ascii")
    (language_dir / "x86.ldefs").write_text(
        (
            "<language_definitions>\n"
            '  <language id="x86:LE:64:default">\n'
            '    <compiler name="gcc" spec="x86-gcc.cspec"/>\n'
            '    <compiler name="broken" spec="missing.cspec"/>\n'
            "  </language>\n"
            "</language_definitions>\n"
        ),
        encoding="ascii",
    )
    return runtime_dir


def test_u010_bridge_session_fallback_when_native_module_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """U-010: Missing native extension falls back to deterministic Python bridge."""

    def _raise_import_error(_: str) -> Any:
        raise ImportError("module not found")

    monkeypatch.setattr(bridge_module.importlib, "import_module", _raise_import_error)

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))
    assert isinstance(bridge_session, bridge_module._FallbackBridgeSession)


def test_u011_bridge_session_adapts_native_payloads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """U-011: Native tuple/dict payloads are adapted to public model types."""
    native_session = _NativeSessionSuccessDouble()
    native_module = _NativeModuleDouble(native_session=native_session)

    monkeypatch.setattr(
        bridge_module.importlib,
        "import_module",
        lambda _: native_module,
    )

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))
    assert native_module.runtime_data_dir == str(runtime_dir)

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
    assert native_session.last_request_payload["analysis_budget"] == {
        "max_instructions": 100000,
    }

    bridge_session.close()
    assert native_session.closed is True


def test_u011_bridge_serializes_explicit_analysis_budget(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """U-011: Explicit analysis budgets use the stable native payload shape."""
    native_session = _NativeSessionSuccessDouble()
    native_module = _NativeModuleDouble(native_session=native_session)
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))

    request = DecompileRequest(
        memory_image=b"\x90\xc3",
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
        compiler_spec="gcc",
        analysis_budget=AnalysisBudget(max_instructions=4096),
    )
    bridge_session.decompile_function(request)

    assert native_session.last_request_payload is not None
    assert native_session.last_request_payload["analysis_budget"] == {
        "max_instructions": 4096,
    }


def test_u002_bridge_rejects_unsupported_target_without_native_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U-002: Bridge validates language/compiler and rejects unsupported targets."""
    native_session = _NativeSessionSuccessDouble()
    native_module = _NativeModuleDouble(native_session=native_session)
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    bridge_session = bridge_module.create_bridge_session()

    unknown_language_request = DecompileRequest(
        memory_image=b"\x90\xc3",
        base_address=0x1000,
        function_address=0x1000,
        language_id="arm:LE:64:v8A",
        compiler_spec="gcc",
    )
    unknown_language_result = bridge_session.decompile_function(unknown_language_request)

    assert unknown_language_result.error is not None
    assert unknown_language_result.error.category == "unsupported_target"
    assert unknown_language_result.function_info is None
    assert unknown_language_result.c_code is None
    assert native_session.decompile_calls == 0

    unknown_compiler_request = DecompileRequest(
        memory_image=b"\x90\xc3",
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
        compiler_spec="windows",
    )
    unknown_compiler_result = bridge_session.decompile_function(unknown_compiler_request)

    assert unknown_compiler_result.error is not None
    assert unknown_compiler_result.error.category == "unsupported_target"
    assert unknown_compiler_result.function_info is None
    assert unknown_compiler_result.c_code is None
    assert native_session.decompile_calls == 0


def test_u011_bridge_rejects_malformed_native_success_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U-011: Malformed native success payloads are normalized to internal_error."""
    native_module = _NativeModuleDouble(native_session=_NativeSessionInvalidSuccessShapeDouble())
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    bridge_session = bridge_module.create_bridge_session()
    request = DecompileRequest(
        memory_image=b"\x90\xc3",
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
        compiler_spec="gcc",
    )

    result = bridge_session.decompile_function(request)

    assert isinstance(result, DecompileResult)
    assert result.error is not None
    assert result.error.category == "internal_error"
    assert result.function_info is None
    assert result.c_code is None


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
    assert "/tmp/native/session.log" in result.error.message
    assert result.function_info is None
    assert result.c_code is None
    assert result.metadata["language_id"] == request.language_id


def test_u013_bridge_enumerates_runtime_data_when_native_module_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """U-013: Fallback bridge enumerates runtime-data language/compiler pairs."""

    def _raise_import_error(_: str) -> Any:
        raise ImportError("module not found")

    monkeypatch.setattr(bridge_module.importlib, "import_module", _raise_import_error)

    runtime_dir = _make_runtime_data_fixture(tmp_path)
    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))

    pairs = bridge_session.list_language_compilers()

    assert pairs == [LanguageCompilerPair(language_id="x86:LE:64:default", compiler_spec="gcc")]


def test_u013_bridge_uses_runtime_data_when_native_enumeration_is_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """U-013: Native adapter falls back to runtime-data enumeration when needed."""
    runtime_dir = _make_runtime_data_fixture(tmp_path)
    native_session = _NativeSessionEmptyEnumerationDouble()
    native_module = _NativeModuleDouble(native_session=native_session)
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))

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

    assert result.error is not None
    assert result.error.category == "internal_error"
    assert native_session.decompile_calls == 1


def test_u014_bridge_rejects_missing_runtime_data_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """U-014: Session startup fails deterministically for missing runtime_data_dir."""

    def _raise_import_error(_: str) -> Any:
        raise ImportError("module not found")

    monkeypatch.setattr(bridge_module.importlib, "import_module", _raise_import_error)

    missing_dir = tmp_path / "does-not-exist"
    with pytest.raises(ConfigurationError) as exc_info:
        bridge_module.create_bridge_session(runtime_data_dir=str(missing_dir))

    error_message = exc_info.value.message
    assert "runtime_data_dir does not exist" in error_message
    assert str(missing_dir) in error_message
