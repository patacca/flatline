"""Public session lifecycle API for decompilation operations.

Implements DecompilerSession (specs.md section 3.1) and the module-level
convenience wrappers decompile_function / list_language_compilers (specs.md section 3.2).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from flatline._bridge import create_bridge_session
from flatline._errors import InvalidArgumentError
from flatline._runtime_data import resolve_session_runtime_data_dir

if TYPE_CHECKING:
    from flatline._bridge import BridgeSession
    from flatline._models import DecompileRequest, DecompileResult, LanguageCompilerPair


class DecompilerSession:
    """Long-lived decompiler session owning one native architecture instance.

    A session manages the lifecycle of a native Ghidra ``Architecture`` object.
    Use it as a context manager for deterministic resource cleanup, or call
    :meth:`close` explicitly when done.

    Args:
        runtime_data_dir: Path to the Ghidra runtime data directory containing
            processor ``.sla`` files and compiler specs.  When ``None``
            (default), the directory is auto-discovered from the installed
            ``ghidra-sleigh`` package.

    Example:
        ```python
        with DecompilerSession() as session:
            result = session.decompile_function(request)
            pairs = session.list_language_compilers()
        ```
    """

    def __init__(
        self,
        runtime_data_dir: str | Path | None = None,
        *,
        _bridge_session: BridgeSession | None = None,
    ) -> None:
        normalized_runtime_data_dir = None
        if _bridge_session is None:
            normalized_runtime_data_dir = resolve_session_runtime_data_dir(runtime_data_dir)
        elif runtime_data_dir is not None:
            normalized_runtime_data_dir = str(Path(runtime_data_dir))
        self._runtime_data_dir = normalized_runtime_data_dir
        self._bridge_session = _bridge_session or create_bridge_session(
            normalized_runtime_data_dir
        )
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
        """Enumerate valid language/compiler pairs available in this session.

        Returns only pairs whose backing assets (``.sla`` files and compiler
        specs) are present in the session's runtime data directory.  Covers
        all bundled ISAs including x86, ARM, RISC-V, MIPS, and others.

        Returns:
            List of :class:`~flatline.LanguageCompilerPair` entries.

        Raises:
            InvalidArgumentError: If the session has been closed.
        """
        self._ensure_open()
        return self._bridge_session.list_language_compilers()

    def decompile_function(self, request: DecompileRequest) -> DecompileResult:
        """Decompile a single function described by *request*.

        Args:
            request: A :class:`~flatline.DecompileRequest` specifying the
                memory image, addresses, and target architecture.

        Returns:
            A :class:`~flatline.DecompileResult` containing the decompiled C
            code, structured :class:`~flatline.FunctionInfo`, warnings, and
            any error information.

        Raises:
            InvalidArgumentError: If the session has been closed or the
                request contains invalid arguments.
            UnsupportedTargetError: If the ``language_id`` or
                ``compiler_spec`` is not recognized.
            InvalidAddressError: If the function address is outside the
                memory image.
            DecompileFailedError: If the decompiler engine fails
                internally.
        """
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


def list_language_compilers(
    runtime_data_dir: str | Path | None = None,
) -> list[LanguageCompilerPair]:
    """Enumerate valid language/compiler pairs (one-shot convenience wrapper).

    Creates a short-lived :class:`DecompilerSession`, runs the enumeration,
    and closes the session deterministically.

    Args:
        runtime_data_dir: Optional path to the Ghidra runtime data directory.
            When ``None``, auto-discovered from ``ghidra-sleigh``.

    Returns:
        List of :class:`~flatline.LanguageCompilerPair` entries.
    """
    with DecompilerSession(runtime_data_dir=runtime_data_dir) as session:
        return session.list_language_compilers()


def decompile_function(request: DecompileRequest) -> DecompileResult:
    """Decompile a single function (one-shot convenience wrapper).

    Creates a short-lived :class:`DecompilerSession`, runs the
    decompilation, and closes the session deterministically.

    Args:
        request: A :class:`~flatline.DecompileRequest` specifying the
            memory image, addresses, and target architecture.

    Returns:
        A :class:`~flatline.DecompileResult` with decompiled output.

    Raises:
        InvalidArgumentError: If the request contains invalid arguments.
        UnsupportedTargetError: If the target is not recognized.
        InvalidAddressError: If the function address is unmapped.
        DecompileFailedError: If decompilation fails internally.
    """
    with DecompilerSession(runtime_data_dir=request.runtime_data_dir) as session:
        return session.decompile_function(request)
