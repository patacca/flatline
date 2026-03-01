"""Unit tests for session lifecycle and bridge delegation (specs.md §3.1, §7)."""

from __future__ import annotations

import pytest

from flatline import (
    DecompileRequest,
    DecompileResult,
    DecompilerSession,
    ErrorItem,
    InvalidArgumentError,
    LanguageCompilerPair,
)


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
                "decompiler_version": "0.1.0-dev",
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
