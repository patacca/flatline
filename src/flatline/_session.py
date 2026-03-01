"""Public session lifecycle API for decompilation operations.

Implements DecompilerSession (specs.md section 3.1) and the module-level
convenience wrappers decompile_function / list_language_compilers (specs.md section 3.2).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flatline._bridge import create_bridge_session
from flatline._errors import InvalidArgumentError

if TYPE_CHECKING:
    from flatline._bridge import BridgeSession
    from flatline._models import DecompileRequest, DecompileResult, LanguageCompilerPair


class DecompilerSession:
    """Owns one bridge session and its native lifecycle.

    Session lifecycle maps to native architecture construction/destruction.
    """

    def __init__(
        self,
        runtime_data_dir: str | None = None,
        *,
        _bridge_session: BridgeSession | None = None,
    ) -> None:
        self._runtime_data_dir = runtime_data_dir
        self._bridge_session = _bridge_session or create_bridge_session(runtime_data_dir)
        self._closed = False

    @property
    def is_closed(self) -> bool:
        """Report whether close() has already been called."""
        return self._closed

    def close(self) -> None:
        """Release session resources. Safe to call multiple times."""
        if self._closed:
            return
        self._bridge_session.close()
        self._closed = True

    def list_language_compilers(self) -> list[LanguageCompilerPair]:
        """Enumerate valid language/compiler pairs for this session."""
        self._ensure_open()
        return self._bridge_session.list_language_compilers()

    def decompile_function(self, request: DecompileRequest) -> DecompileResult:
        """Decompile a single function request in this session."""
        self._ensure_open()
        return self._bridge_session.decompile_function(request)

    def _ensure_open(self) -> None:
        if self._closed:
            raise InvalidArgumentError("session is closed")

    def __enter__(self) -> DecompilerSession:
        self._ensure_open()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()


def list_language_compilers(runtime_data_dir: str | None = None) -> list[LanguageCompilerPair]:
    """Convenience wrapper for one-shot language/compiler enumeration."""
    with DecompilerSession(runtime_data_dir=runtime_data_dir) as session:
        return session.list_language_compilers()


def decompile_function(request: DecompileRequest) -> DecompileResult:
    """Convenience wrapper for one-shot single-function decompilation."""
    with DecompilerSession(runtime_data_dir=request.runtime_data_dir) as session:
        return session.decompile_function(request)
