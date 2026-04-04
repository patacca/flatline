"""Unit tests for Windows native DLL bootstrap behavior."""

from __future__ import annotations

from pathlib import Path

import tests.conftest as pytest_config
from flatline.bridge import core as bridge_module
from flatline.runtime import windows as windows_module


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
    monkeypatch.setattr(windows_module, "__file__", str(package_dir / "runtime" / "windows.py"))
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


def test_u030_bridge_session_bootstraps_windows_loader_without_vcpkg_env(
    monkeypatch,
) -> None:
    """U-030: Bridge-session startup still boots the Windows loader without env gating."""
    calls: list[str] = []

    monkeypatch.delenv("VCPKG_INSTALLATION_ROOT", raising=False)
    monkeypatch.setattr(
        bridge_module,
        "configure_windows_native_dll_dirs",
        lambda: calls.append("called"),
    )
    monkeypatch.setattr(
        bridge_module,
        "enumerate_runtime_data_language_compilers",
        lambda runtime_data_dir: [],
    )

    def raise_import_error(module_name: str) -> object:
        raise ImportError(module_name)

    monkeypatch.setattr(bridge_module.importlib, "import_module", raise_import_error)

    session = bridge_module.create_bridge_session()

    assert calls == ["called"]
    assert session.list_language_compilers() == []


def test_u030_pytest_native_gate_bootstraps_windows_loader_before_import(
    monkeypatch,
) -> None:
    """U-030: The strict-native pytest gate uses the same Windows DLL bootstrap."""
    calls: list[str] = []

    monkeypatch.setattr(
        pytest_config.importlib.util,
        "find_spec",
        lambda module_name: object() if module_name == pytest_config.NATIVE_MODULE else None,
    )
    monkeypatch.setattr(
        pytest_config,
        "configure_windows_native_dll_dirs",
        lambda: calls.append("called"),
    )

    def raise_import_error(module_name: str) -> object:
        assert module_name == pytest_config.NATIVE_MODULE
        assert calls == ["called"]
        raise ImportError("DLL load failed while importing flatline._flatline_native")

    monkeypatch.setattr(pytest_config.importlib, "import_module", raise_import_error)

    assert pytest_config._native_bridge_available() is False
