"""Unit tests for bridge session error and fallback edges."""

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


def _make_request(**overrides: object) -> DecompileRequest:
    payload: dict[str, object] = {
        "memory_image": b"\x90\xc3",
        "base_address": 0x1000,
        "function_address": 0x1000,
        "language_id": "x86:LE:64:default",
        "compiler_spec": "gcc",
    }
    payload.update(overrides)
    return DecompileRequest(**payload)


def test_u002_bridge_rejects_unsupported_target_without_native_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U-002: Bridge validates language/compiler and rejects unsupported targets."""
    native_session = _NativeSessionSuccessDouble()
    native_module = _NativeModuleDouble(native_session=native_session)
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    bridge_session = bridge_module.create_bridge_session()

    unknown_language_result = bridge_session.decompile_function(
        _make_request(language_id="arm:LE:64:v8A")
    )

    assert unknown_language_result.error is not None
    assert unknown_language_result.error.category == "unsupported_target"
    assert unknown_language_result.function_info is None
    assert unknown_language_result.c_code is None
    assert native_session.decompile_calls == 0

    unknown_compiler_result = bridge_session.decompile_function(
        _make_request(compiler_spec="windows")
    )

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
    result = bridge_session.decompile_function(_make_request())

    assert isinstance(result, DecompileResult)
    assert result.error is not None
    assert result.error.category == "internal_error"
    assert result.function_info is None
    assert result.c_code is None


def test_u012_bridge_session_normalizes_native_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """U-012: Native bridge exceptions become structured internal_error results."""
    native_module = _NativeModuleDouble(native_session=_NativeSessionFailureDouble())
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    request = _make_request(base_address=0x400000, function_address=0x400000)
    bridge_session = bridge_module.create_bridge_session()
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
    """U-013: Fallback bridge enumerates runtime-data language/compiler pairs."""

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
    """U-013: Native adapter falls back to runtime-data enumeration when needed."""
    runtime_dir = _make_runtime_data_fixture(tmp_path)
    native_session = _NativeSessionEmptyEnumerationDouble()
    native_module = _NativeModuleDouble(native_session=native_session)
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))

    pairs = bridge_session.list_language_compilers()
    assert pairs == [LanguageCompilerPair(language_id="x86:LE:64:default", compiler_spec="gcc")]

    result = bridge_session.decompile_function(_make_request())

    assert result.error is not None
    assert result.error.category == "internal_error"
    assert native_session.decompile_calls == 1


def test_u014_bridge_rejects_missing_runtime_data_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """U-014: Session startup fails deterministically for missing runtime_data_dir."""

    def _raise_import_error(_: str) -> object:
        raise ImportError("module not found")

    monkeypatch.setattr(bridge_module.importlib, "import_module", _raise_import_error)

    missing_dir = tmp_path / "does-not-exist"
    with pytest.raises(ConfigurationError) as exc_info:
        bridge_module.create_bridge_session(runtime_data_dir=str(missing_dir))

    error_message = exc_info.value.message
    assert "runtime_data_dir does not exist" in error_message
    assert str(missing_dir) in error_message
