"""Bridge session abstraction and fallback implementation.

Internal bridge-session boundary between the stable Python public API and the
replaceable native bridge implementation. The BridgeSession protocol and its
implementations are private; only the public Python API is stable.
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from os import fspath
from typing import TYPE_CHECKING, Any, Protocol

from flatline._errors import ConfigurationError, InternalError
from flatline.bridge.payloads import (
    _coerce_decompile_result,
    _coerce_language_compiler_pair,
    _error_result,
    _request_to_native_payload,
)
from flatline.runtime import (
    configure_windows_native_dll_dirs,
    enumerate_runtime_data_language_compilers,
)

if TYPE_CHECKING:
    from flatline.models import DecompileRequest, DecompileResult, LanguageCompilerPair


class BridgeSession(Protocol):
    """Internal bridge session protocol used by DecompilerSession."""

    def close(self) -> None:
        """Release bridge/native resources owned by this session."""

    def list_language_compilers(self) -> list[LanguageCompilerPair]:
        """List valid language/compiler pairs known to the runtime data."""

    def decompile_function(self, request: DecompileRequest) -> DecompileResult:
        """Run one decompile request through the bridge."""


class _FallbackBridgeSession:
    """Pure-Python fallback until the native bridge is available.

    Keeps the public API usable while returning deterministic structured
    error responses for unimplemented native operations.
    """

    def __init__(
        self,
        runtime_data_dir: str | None = None,
        *,
        runtime_data_pairs: Sequence[LanguageCompilerPair] = (),
    ) -> None:
        self._runtime_data_dir = runtime_data_dir
        self._runtime_data_pairs = tuple(runtime_data_pairs)
        self._closed = False

    def close(self) -> None:
        self._closed = True

    def list_language_compilers(self) -> list[LanguageCompilerPair]:
        if self._closed:
            return []
        return list(self._runtime_data_pairs)

    def decompile_function(self, request: DecompileRequest) -> DecompileResult:
        if self._closed:
            return _error_result(
                request,
                category="internal_error",
                message="bridge session is closed",
                retryable=False,
            )

        return _error_result(
            request,
            category="configuration_error",
            message="native bridge is not implemented in this build",
            retryable=False,
        )


class _NativeBridgeSession:
    """Adapter around native bridge sessions.

    Normalizes native payloads to stable Python dataclasses at the bridge
    boundary so the public API remains contract-shaped.
    """

    def __init__(
        self,
        native_session: Any,
        *,
        runtime_data_pairs: Sequence[LanguageCompilerPair] = (),
    ) -> None:
        self._native_session = native_session
        self._runtime_data_pairs = tuple(runtime_data_pairs)

    def close(self) -> None:
        self._native_session.close()

    def list_language_compilers(self) -> list[LanguageCompilerPair]:
        try:
            raw_pairs = self._native_session.list_language_compilers()
            native_pairs = [_coerce_language_compiler_pair(item) for item in raw_pairs]
            if native_pairs:
                return native_pairs
            return list(self._runtime_data_pairs)
        except Exception as exc:  # pragma: no cover - exercised with bridge doubles
            raise InternalError(f"native list_language_compilers failed: {exc}") from exc

    def decompile_function(self, request: DecompileRequest) -> DecompileResult:
        request_payload = _request_to_native_payload(request)
        try:
            target_error = self._validate_target_selection(request)
            if target_error is not None:
                return target_error
            raw_result = self._native_session.decompile_function(request_payload)
            return _coerce_decompile_result(raw_result, request)
        except Exception as exc:
            return _error_result(
                request,
                category="internal_error",
                message=f"native decompile failed: {exc}",
                retryable=False,
            )

    def _validate_target_selection(self, request: DecompileRequest) -> DecompileResult | None:
        known_pairs = self.list_language_compilers()
        compilers_by_language: dict[str, set[str]] = {}
        for pair in known_pairs:
            if pair.language_id not in compilers_by_language:
                compilers_by_language[pair.language_id] = set()
            compilers_by_language[pair.language_id].add(pair.compiler_spec)

        available_compilers = compilers_by_language.get(request.language_id)
        if available_compilers is None:
            return _error_result(
                request,
                category="unsupported_target",
                message=f"unsupported language_id: {request.language_id!r}",
                retryable=False,
            )

        if request.compiler_spec is None:
            return None

        if request.compiler_spec not in available_compilers:
            return _error_result(
                request,
                category="unsupported_target",
                message=(
                    f"unsupported compiler_spec {request.compiler_spec!r} "
                    f"for language_id {request.language_id!r}"
                ),
                retryable=False,
            )

        return None


def create_bridge_session(runtime_data_dir: str | None = None) -> BridgeSession:
    """Create a bridge session.

    Tries to use a compiled native bridge when available. Falls back to a
    deterministic pure-Python skeleton implementation otherwise.
    """
    normalized_runtime_data_dir = None
    if runtime_data_dir is not None:
        normalized_runtime_data_dir = fspath(runtime_data_dir)

    runtime_data_pairs = enumerate_runtime_data_language_compilers(normalized_runtime_data_dir)
    # Let the helper decide whether this install is a delvewheel-repaired Windows
    # wheel with bundled DLLs or an unrepaired build (CI tests, local editable
    # installs on Windows) that still needs local vcpkg zlib.
    configure_windows_native_dll_dirs()
    try:
        native_bridge = importlib.import_module("flatline._flatline_native")
    except ImportError:
        return _FallbackBridgeSession(
            runtime_data_dir=normalized_runtime_data_dir,
            runtime_data_pairs=runtime_data_pairs,
        )
    try:
        native_session = native_bridge.create_session(normalized_runtime_data_dir)
    except Exception as exc:
        if isinstance(exc, ConfigurationError):
            raise
        raise InternalError(f"native bridge session startup failed: {exc}") from exc
    return _NativeBridgeSession(
        native_session,
        runtime_data_pairs=runtime_data_pairs,
    )
