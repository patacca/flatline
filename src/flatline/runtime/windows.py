"""Windows-specific runtime helpers.

Published wheels repaired by delvewheel already carry their DLL bootstrap, so
this module exists for unrepaired builds (CI contract tests and local editable
installs) where vcpkg zlib must be discovered at runtime.
"""

from __future__ import annotations

import contextlib
import os
import pathlib
import shutil
import sys

_WINDOWS_DLL_DIRECTORY_HANDLE: object | None = None


def _has_repaired_dll_bundle() -> bool:
    """Return whether a delvewheel-style bundled DLL directory is present."""
    # `windows.py` lives under `flatline/runtime/`, but delvewheel places the
    # sibling bundle next to the top-level `flatline/` package directory.
    package_root = pathlib.Path(__file__).resolve().parents[1]
    bundle_dir = package_root.parent / f"{package_root.name}.libs"
    if not bundle_dir.is_dir():
        return False
    return any(bundle_dir.glob("*.dll"))


def _resolve_vcpkg_root() -> pathlib.Path | None:
    """Resolve the vcpkg installation root from env or PATH."""
    vcpkg_root = os.environ.get("VCPKG_INSTALLATION_ROOT")
    if vcpkg_root:
        return pathlib.Path(vcpkg_root)

    vcpkg_exe = shutil.which("vcpkg")
    if not vcpkg_exe:
        return None
    return pathlib.Path(vcpkg_exe).resolve().parent


def configure_windows_native_dll_dirs() -> None:
    """Register native DLL search paths needed by unrepaired Windows builds."""
    global _WINDOWS_DLL_DIRECTORY_HANDLE

    if sys.platform != "win32" or not hasattr(os, "add_dll_directory"):
        return

    if _has_repaired_dll_bundle():
        return

    vcpkg_root = _resolve_vcpkg_root()
    if vcpkg_root is None:
        return

    dll_dir = vcpkg_root / "installed" / "x64-windows" / "bin"
    if not dll_dir.is_dir() or not (dll_dir / "zlib1.dll").is_file():
        return

    with contextlib.suppress(OSError):
        _WINDOWS_DLL_DIRECTORY_HANDLE = os.add_dll_directory(str(dll_dir))
