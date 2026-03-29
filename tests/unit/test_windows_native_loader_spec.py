"""Unit tests for Windows native DLL bootstrap behavior."""

from __future__ import annotations

from pathlib import Path

import flatline._windows as windows_module


def test_u030_windows_native_loader_registers_vcpkg_zlib_bin_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """U-030: Windows imports register the vcpkg zlib DLL directory when available."""
    vcpkg_root = tmp_path / "vcpkg"
    dll_dir = vcpkg_root / "installed" / "x64-windows" / "bin"
    dll_dir.mkdir(parents=True)
    (dll_dir / "zlib1.dll").write_text("", encoding="ascii")

    recorded_dirs: list[str] = []

    monkeypatch.setattr(windows_module.sys, "platform", "win32")
    monkeypatch.setenv("VCPKG_INSTALLATION_ROOT", str(vcpkg_root))
    monkeypatch.setattr(
        windows_module.os,
        "add_dll_directory",
        lambda raw_path: recorded_dirs.append(raw_path) or object(),
        raising=False,
    )
    monkeypatch.setattr(windows_module, "_WINDOWS_DLL_DIRECTORY_HANDLE", None)

    windows_module.configure_windows_native_dll_dirs()

    assert recorded_dirs == [str(dll_dir)]


def test_u030_windows_native_loader_skips_missing_vcpkg_zlib_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """U-030: Windows imports skip DLL registration when the vcpkg zlib DLL is absent."""
    vcpkg_root = tmp_path / "vcpkg"
    recorded_dirs: list[str] = []

    monkeypatch.setattr(windows_module.sys, "platform", "win32")
    monkeypatch.setenv("VCPKG_INSTALLATION_ROOT", str(vcpkg_root))
    monkeypatch.setattr(
        windows_module.os,
        "add_dll_directory",
        lambda raw_path: recorded_dirs.append(raw_path) or object(),
        raising=False,
    )
    monkeypatch.setattr(windows_module, "_WINDOWS_DLL_DIRECTORY_HANDLE", None)

    windows_module.configure_windows_native_dll_dirs()

    assert recorded_dirs == []
