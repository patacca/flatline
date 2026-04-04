"""Unit tests for bridge adapter behavior (specs.md section 3.2, section 6)."""

from __future__ import annotations

import pytest

from flatline import (
    AnalysisBudget,
    ConfigurationError,
    DecompileRequest,
    DecompileResult,
    Enriched,
    FunctionInfo,
    LanguageCompilerPair,
    Pcode,
    PcodeOpInfo,
    VarnodeFlags,
    VarnodeInfo,
)
from flatline.bridge import core as bridge_module

from ._bridge_doubles import (
    _make_runtime_data_fixture,
    _NativeModuleDouble,
    _NativeSessionEmptyEnumerationDouble,
    _NativeSessionFailureDouble,
    _NativeSessionInvalidSuccessShapeDouble,
    _NativeSessionMissingEnrichedDouble,
    _NativeSessionMissingPcodeDouble,
    _NativeSessionSuccessDouble,
)


def test_u010_bridge_session_fallback_when_native_module_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """U-010: Missing native extension falls back to deterministic Python bridge."""

    def _raise_import_error(_: str) -> object:
        raise ImportError("module not found")

    monkeypatch.setattr(bridge_module.importlib, "import_module", _raise_import_error)

    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    bridge_session = bridge_module.create_bridge_session(runtime_data_dir=str(runtime_dir))
    assert isinstance(bridge_session, bridge_module._FallbackBridgeSession)


def test_u011_bridge_session_adapts_native_payloads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
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
    assert native_session.last_request_payload["tail_padding"] == b"\x00"

    bridge_session.close()
    assert native_session.closed is True


def test_u011_bridge_serializes_explicit_analysis_budget(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
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


def test_u011_bridge_serializes_explicit_tail_padding_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """U-011: Tail padding uses the stable native payload shape."""
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
        tail_padding=b"\x1f\x20\x03\xd5",
    )
    bridge_session.decompile_function(request)

    assert native_session.last_request_payload is not None
    assert native_session.last_request_payload["tail_padding"] == b"\x1f\x20\x03\xd5"

    disabled_request = DecompileRequest(
        memory_image=b"\x90\xc3",
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
        compiler_spec="gcc",
        tail_padding=b"",
    )
    bridge_session.decompile_function(disabled_request)

    assert native_session.last_request_payload["tail_padding"] is None


def test_u028_bridge_session_adapts_enriched_payload_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """U-028: Native enriched-output payloads adapt to public frozen model types."""
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
        enriched=True,
    )
    result = bridge_session.decompile_function(request)

    assert native_session.last_request_payload is not None
    assert native_session.last_request_payload["enriched"] is True
    assert isinstance(result.enriched, Enriched)
    assert isinstance(result.enriched.pcode, Pcode)
    assert isinstance(result.enriched.pcode.pcode_ops[0], PcodeOpInfo)
    assert isinstance(result.enriched.pcode.varnodes[0], VarnodeInfo)
    assert isinstance(result.enriched.pcode.varnodes[0].flags, VarnodeFlags)
    assert result.enriched.pcode.pcode_ops[0].opcode == "INT_ADD"
    assert result.enriched.pcode.get_varnode(2).use_op_ids == [1]


def test_u028_bridge_rejects_missing_enriched_payload_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U-028: Opt-in enriched output must not silently disappear on success."""
    native_module = _NativeModuleDouble(native_session=_NativeSessionMissingEnrichedDouble())
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    bridge_session = bridge_module.create_bridge_session()
    request = DecompileRequest(
        memory_image=b"\x90\xc3",
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
        compiler_spec="gcc",
        enriched=True,
    )

    result = bridge_session.decompile_function(request)

    assert result.error is not None
    assert result.error.category == "internal_error"
    assert result.enriched is None


def test_u028_bridge_rejects_missing_pcode_when_enriched_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U-028: Enriched present but pcode missing must not silently pass."""
    native_module = _NativeModuleDouble(native_session=_NativeSessionMissingPcodeDouble())
    monkeypatch.setattr(bridge_module.importlib, "import_module", lambda _: native_module)

    bridge_session = bridge_module.create_bridge_session()
    request = DecompileRequest(
        memory_image=b"\x90\xc3",
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
        compiler_spec="gcc",
        enriched=True,
    )

    result = bridge_session.decompile_function(request)

    assert result.error is not None
    assert result.error.category == "internal_error"
    assert result.enriched is None


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
