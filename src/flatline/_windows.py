"""Windows-specific runtime helpers.

Published wheels bundle zlib via delvewheel, so none of this is needed by
end-users.  It exists solely for unrepaired builds (CI contract tests and
local editable installs) where vcpkg zlib must be discovered at runtime.
"""

from __future__ import annotations

import contextlib
import os
import pathlib
import sys

_WINDOWS_DLL_DIRECTORY_HANDLE: object | None = None


def configure_windows_native_dll_dirs() -> None:
    """Register native DLL search paths needed by unrepaired Windows builds."""
    global _WINDOWS_DLL_DIRECTORY_HANDLE

    if sys.platform != "win32" or not hasattr(os, "add_dll_directory"):
        return

    vcpkg_root = os.environ.get("VCPKG_INSTALLATION_ROOT")
    if not vcpkg_root:
        return

    dll_dir = pathlib.Path(vcpkg_root) / "installed" / "x64-windows" / "bin"
    if not dll_dir.is_dir() or not (dll_dir / "zlib1.dll").is_file():
        return

    with contextlib.suppress(OSError):
        _WINDOWS_DLL_DIRECTORY_HANDLE = os.add_dll_directory(str(dll_dir))
