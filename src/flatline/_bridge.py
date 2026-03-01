"""Bridge session abstraction and fallback implementation.

This module defines the internal bridge-session boundary between the stable
Python API and the unstable native bridge implementation.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Protocol

from flatline._models import DecompileResult, ErrorItem, LanguageCompilerPair
from flatline._version import __version__

if TYPE_CHECKING:
    from flatline._models import DecompileRequest


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
    internal_error responses for unimplemented native operations.
    """

    def __init__(self, runtime_data_dir: str | None = None) -> None:
        self._runtime_data_dir = runtime_data_dir
        self._closed = False

    def close(self) -> None:
        self._closed = True

    def list_language_compilers(self) -> list[LanguageCompilerPair]:
        if self._closed:
            return []
        return []

    def decompile_function(self, request: DecompileRequest) -> DecompileResult:
        if self._closed:
            return DecompileResult(
                c_code=None,
                function_info=None,
                warnings=[],
                error=ErrorItem(
                    category="internal_error",
                    message="bridge session is closed",
                    retryable=False,
                ),
                metadata={
                    "decompiler_version": __version__,
                    "language_id": request.language_id,
                    "compiler_spec": request.compiler_spec or "",
                    "diagnostics": {},
                },
            )

        return DecompileResult(
            c_code=None,
            function_info=None,
            warnings=[],
            error=ErrorItem(
                category="internal_error",
                message="native bridge is not implemented in this build",
                retryable=False,
            ),
            metadata={
                "decompiler_version": __version__,
                "language_id": request.language_id,
                "compiler_spec": request.compiler_spec or "",
                "diagnostics": {},
            },
        )


def create_bridge_session(runtime_data_dir: str | None = None) -> BridgeSession:
    """Create a bridge session.

    Tries to use a compiled native bridge when available. Falls back to a
    deterministic pure-Python skeleton implementation otherwise.
    """
    try:
        native_bridge = importlib.import_module("flatline._flatline_native")
    except ImportError:
        return _FallbackBridgeSession(runtime_data_dir=runtime_data_dir)

    return native_bridge.create_session(runtime_data_dir)
