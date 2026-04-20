"""POSIX-only timeout context manager using SIGALRM.

Provides a time_budget context manager for enforcing timeouts on layout
operations. Uses signal.SIGALRM which is only available on POSIX systems.

Convention: Each layout operation has a configured per-case budget (default
300s). The overall benchmark suite has a 30-minute budget for all layouts.
"""

from __future__ import annotations

import contextlib
import signal
import sys
from typing import Generator


@contextlib.contextmanager
def time_budget(seconds: int) -> Generator[None, None, None]:
    """Enforce a timeout using SIGALRM (POSIX only).

    Raises:
        TimeoutError: If the block does not complete within the specified
            number of seconds.
        RuntimeError: If called on Windows (SIGALRM not available).

    Example:
        >>> with time_budget(5):
        ...     long_running_operation()
    """
    if sys.platform == "win32":
        msg = "time_budget uses SIGALRM which is not available on Windows"
        raise RuntimeError(msg)

    def _handler(signum: int, frame: object) -> None:
        raise TimeoutError(f"Layout timed out after {seconds}s")

    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
