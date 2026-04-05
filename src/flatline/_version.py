"""Version and upstream-pin constants for the flatline package."""

from __future__ import annotations

__version__ = "0.1.2"

# Ghidra decompiler engine version for the pinned upstream snapshot.
# Must match the native decompiler_version_string() output (ghidra-{major}.{minor}).
DECOMPILER_VERSION = "ghidra-6.1"
