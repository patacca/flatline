"""Unit tests for session lifecycle and bridge delegation (specs.md section 3.1, 7)."""

from __future__ import annotations

import pytest

from flatline import (
    DecompileRequest,
    DecompileResult,
    DecompilerSession,
    ErrorItem,
    InvalidArgumentError,
    LanguageCompilerPair,
    _session as session_module,
)
from flatline._version import DECOMPILER_VERSION


class _FakeBridgeSession:
    """Test double for bridge-session delegation checks."""

    def __init__(self) -> None:
        self.closed = False
        self.last_request: DecompileRequest | None = None

    def close(self) -> None:
        self.closed = True

    def list_language_compilers(self) -> list[LanguageCompilerPair]:
        return [LanguageCompilerPair(language_id="x86:LE:64:default", compiler_spec="gcc")]

    def decompile_function(self, request: DecompileRequest) -> DecompileResult:
        self.last_request = request
        return DecompileResult(
            c_code=None,
            function_info=None,
            warnings=[],
            error=ErrorItem(
                category="internal_error",
                message="bridge double",
                retryable=False,
            ),
            metadata={
                "decompiler_version": DECOMPILER_VERSION,
                "language_id": request.language_id,
                "compiler_spec": request.compiler_spec or "",
                "diagnostics": {},
            },
        )


def test_u007_session_context_manager_lifecycle() -> None:
    """U-007: Session lifecycle is deterministic and close() is idempotent."""
    bridge = _FakeBridgeSession()

    with DecompilerSession(_bridge_session=bridge) as session:
        assert session.is_closed is False

    assert session.is_closed is True
    assert bridge.closed is True

    # close() idempotency
    session.close()
    assert session.is_closed is True


def test_u008_session_rejects_calls_after_close() -> None:
    """U-008: Closed session rejects API operations with invalid_argument."""
    session = DecompilerSession(_bridge_session=_FakeBridgeSession())
    session.close()

    req = DecompileRequest(
        memory_image=b"\xcc",
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
    )

    with pytest.raises(InvalidArgumentError) as list_exc:
        session.list_language_compilers()
    assert list_exc.value.category == "invalid_argument"

    with pytest.raises(InvalidArgumentError) as decomp_exc:
        session.decompile_function(req)
    assert decomp_exc.value.category == "invalid_argument"


def test_u009_session_delegates_to_bridge() -> None:
    """U-009: Session delegates enumerate/decompile operations to bridge layer."""
    bridge = _FakeBridgeSession()
    session = DecompilerSession(_bridge_session=bridge)

    pairs = session.list_language_compilers()
    assert pairs == [LanguageCompilerPair(language_id="x86:LE:64:default", compiler_spec="gcc")]

    req = DecompileRequest(
        memory_image=b"\xcc\xc3",
        base_address=0x1000,
        function_address=0x1000,
        language_id="x86:LE:64:default",
        compiler_spec="gcc",
    )
    result = session.decompile_function(req)
    assert isinstance(result, DecompileResult)
    assert result.error is not None
    assert result.error.category == "internal_error"
    assert bridge.last_request == req


def test_u016_session_resolves_default_runtime_data_before_bridge_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U-016: Public sessions resolve the packaged default runtime-data root."""
    bridge = _FakeBridgeSession()
    resolve_calls: list[str | None] = []
    bridge_calls: list[str | None] = []

    def _resolve_runtime_data_dir(runtime_data_dir: str | None) -> str:
        resolve_calls.append(runtime_data_dir)
        return "/tmp/flatline-runtime"

    def _create_bridge_session(runtime_data_dir: str | None) -> _FakeBridgeSession:
        bridge_calls.append(runtime_data_dir)
        return bridge

    monkeypatch.setattr(
        session_module,
        "resolve_session_runtime_data_dir",
        _resolve_runtime_data_dir,
    )
    monkeypatch.setattr(session_module, "create_bridge_session", _create_bridge_session)

    session = session_module.DecompilerSession()

    assert resolve_calls == [None]
    assert bridge_calls == ["/tmp/flatline-runtime"]
    assert session._runtime_data_dir == "/tmp/flatline-runtime"


def test_u016_injected_bridge_skips_default_runtime_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U-016: Injected bridge doubles do not trigger packaged-default discovery."""

    def _unexpected_runtime_resolution(runtime_data_dir: str | None) -> str:
        raise AssertionError(
            f"resolve_session_runtime_data_dir should not be called: {runtime_data_dir!r}"
        )

    monkeypatch.setattr(
        session_module,
        "resolve_session_runtime_data_dir",
        _unexpected_runtime_resolution,
    )

    session = session_module.DecompilerSession(_bridge_session=_FakeBridgeSession())

    assert session.is_closed is False
