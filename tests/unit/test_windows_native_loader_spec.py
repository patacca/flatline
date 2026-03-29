"""Unit tests for Windows native DLL bootstrap behavior."""

from __future__ import annotations

import importlib
import sys
import types
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


def test_u030_windows_native_loader_skips_vcpkg_when_repaired_bundle_present(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """U-030: Repaired wheels skip the vcpkg fallback bootstrap entirely."""
    site_packages = tmp_path / "site-packages"
    package_dir = site_packages / "flatline"
    package_dir.mkdir(parents=True)
    bundle_dir = site_packages / "flatline.libs"
    bundle_dir.mkdir()
    (bundle_dir / "zlib1-bundled.dll").write_text("", encoding="ascii")

    vcpkg_root = tmp_path / "vcpkg"
    dll_dir = vcpkg_root / "installed" / "x64-windows" / "bin"
    dll_dir.mkdir(parents=True)
    (dll_dir / "zlib1.dll").write_text("", encoding="ascii")

    recorded_dirs: list[str] = []

    monkeypatch.setattr(windows_module.sys, "platform", "win32")
    monkeypatch.setenv("VCPKG_INSTALLATION_ROOT", str(vcpkg_root))
    monkeypatch.setattr(windows_module, "__file__", str(package_dir / "_windows.py"))
    monkeypatch.setattr(
        windows_module.os,
        "add_dll_directory",
        lambda raw_path: recorded_dirs.append(raw_path) or object(),
        raising=False,
    )
    monkeypatch.setattr(windows_module, "_WINDOWS_DLL_DIRECTORY_HANDLE", None)

    windows_module.configure_windows_native_dll_dirs()

    assert recorded_dirs == []


def test_u030_windows_native_loader_falls_back_to_vcpkg_on_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """U-030: Windows imports fall back to `vcpkg` on PATH when env is unset."""
    vcpkg_root = tmp_path / "vcpkg"
    dll_dir = vcpkg_root / "installed" / "x64-windows" / "bin"
    dll_dir.mkdir(parents=True)
    vcpkg_exe = vcpkg_root / "vcpkg.exe"
    vcpkg_exe.write_text("", encoding="ascii")
    (dll_dir / "zlib1.dll").write_text("", encoding="ascii")

    recorded_dirs: list[str] = []

    monkeypatch.setattr(windows_module.sys, "platform", "win32")
    monkeypatch.delenv("VCPKG_INSTALLATION_ROOT", raising=False)
    monkeypatch.setattr(
        windows_module.shutil,
        "which",
        lambda program: str(vcpkg_exe) if program == "vcpkg" else None,
    )
    monkeypatch.setattr(
        windows_module.os,
        "add_dll_directory",
        lambda raw_path: recorded_dirs.append(raw_path) or object(),
        raising=False,
    )
    monkeypatch.setattr(windows_module, "_WINDOWS_DLL_DIRECTORY_HANDLE", None)

    windows_module.configure_windows_native_dll_dirs()

    assert recorded_dirs == [str(dll_dir)]


def test_u030_package_init_bootstraps_windows_loader_without_vcpkg_env(
    monkeypatch,
) -> None:
    """U-030: Package import still boots the Windows loader without env gating."""
    original_flatline = sys.modules.get("flatline")
    original_windows = sys.modules.get("flatline._windows")
    fake_windows = types.ModuleType("flatline._windows")
    calls: list[str] = []

    fake_windows.configure_windows_native_dll_dirs = lambda: calls.append("called")

    monkeypatch.setattr(sys, "platform", "win32", raising=False)
    monkeypatch.delenv("VCPKG_INSTALLATION_ROOT", raising=False)
    monkeypatch.setitem(sys.modules, "flatline._windows", fake_windows)
    sys.modules.pop("flatline", None)

    try:
        importlib.import_module("flatline")
    finally:
        sys.modules.pop("flatline", None)
        if original_flatline is not None:
            sys.modules["flatline"] = original_flatline
        if original_windows is not None:
            sys.modules["flatline._windows"] = original_windows
        else:
            sys.modules.pop("flatline._windows", None)

    assert calls == ["called"]
