from __future__ import annotations

import pytest

from flatline import ConfigurationError, DecompileRequest, DecompileResult, LanguageCompilerPair
from flatline.bridge import core as bridge_module

from ._bridge_doubles import (
    _make_runtime_data_fixture,
    _NativeModuleDouble,
    _NativeSessionEmptyEnumerationDouble,
    _NativeSessionFailureDouble,
    _NativeSessionInvalidSuccessShapeDouble,
    _NativeSessionSuccessDouble,
)


def test_u002_bridge_rejects_unsupported_target_without_native_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    native_module = _NativeModuleDouble(native_session=_NativeSessionFailureDouble())
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

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
    tmp_path,
) -> None:
    def _raise_import_error(_: str) -> object:
        raise ImportError("module not found")

    monkeypatch.setattr(bridge_module.importlib, "import_module", _raise_import_error)

    runtime_dir = _make_runtime_data_fixture(tmp_path)
    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))

    pairs = bridge_session.list_language_compilers()
    assert pairs == [LanguageCompilerPair(language_id="x86:LE:64:default", compiler_spec="gcc")]


def test_u013_bridge_uses_runtime_data_when_native_enumeration_is_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
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
    tmp_path,
) -> None:
    def _raise_import_error(_: str) -> object:
        raise ImportError("module not found")

    monkeypatch.setattr(bridge_module.importlib, "import_module", _raise_import_error)

    missing_dir = tmp_path / "does-not-exist"
    with pytest.raises(ConfigurationError) as exc_info:
        bridge_module.create_bridge_session(runtime_data_dir=str(missing_dir))

    error_message = exc_info.value.message
    assert "runtime_data_dir does not exist" in error_message
    assert str(missing_dir) in error_message
