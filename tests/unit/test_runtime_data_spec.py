"""Unit tests for runtime-data language/compiler enumeration behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from flatline import InternalError, LanguageCompilerPair
from flatline import _runtime_data as runtime_data_module
from flatline._runtime_data import (
    enumerate_runtime_data_language_compilers,
    resolve_session_runtime_data_dir,
)
from flatline._version import UPSTREAM_COMMIT, UPSTREAM_TAG


class _GhidraSleighModuleDouble:
    """Minimal ghidra-sleigh package double for default-runtime resolution tests."""

    def __init__(
        self,
        runtime_dir: Path,
        *,
        ghidra_tag: str = UPSTREAM_TAG,
        ghidra_commit: str = UPSTREAM_COMMIT,
    ) -> None:
        self.GHIDRA_TAG = ghidra_tag
        self.GHIDRA_COMMIT = ghidra_commit
        self._runtime_dir = runtime_dir

    def get_runtime_data_dir(self) -> Path:
        return self._runtime_dir


def _make_valid_runtime_data(runtime_dir: Path) -> None:
    languages_dir = runtime_dir / "languages"
    languages_dir.mkdir(parents=True)
    (languages_dir / "x86-gcc.cspec").write_text("<compiler_spec/>", encoding="ascii")
    (languages_dir / "x86.ldefs").write_text(
        (
            "<language_definitions>\n"
            "  <language id=\"x86:LE:64:default\">\n"
            "    <compiler id=\"gcc\" spec=\"x86-gcc.cspec\"/>\n"
            "  </language>\n"
            "</language_definitions>\n"
        ),
        encoding="ascii",
    )


def test_runtime_data_enumeration_skips_malformed_ldefs_when_valid_pairs_exist(
    tmp_path: Path,
) -> None:
    """Malformed `.ldefs` are skipped when valid files provide pairs."""
    runtime_dir = tmp_path / "runtime_data"
    _make_valid_runtime_data(runtime_dir)
    (runtime_dir / "languages" / "bad.ldefs").write_text("", encoding="ascii")

    with pytest.warns(RuntimeWarning, match="Skipped malformed .ldefs files") as warning_records:
        pairs = enumerate_runtime_data_language_compilers(str(runtime_dir))

    assert pairs == [LanguageCompilerPair(language_id="x86:LE:64:default", compiler_spec="gcc")]
    assert len(warning_records) == 1
    warning_message = str(warning_records[0].message)
    assert str(runtime_dir / "languages" / "bad.ldefs") in warning_message


def test_runtime_data_enumeration_raises_when_only_malformed_ldefs_exist(
    tmp_path: Path,
) -> None:
    """All-malformed `.ldefs` files produce deterministic `InternalError`."""
    runtime_dir = tmp_path / "runtime_data"
    languages_dir = runtime_dir / "languages"
    languages_dir.mkdir(parents=True)
    (languages_dir / "bad1.ldefs").write_text("", encoding="ascii")
    (languages_dir / "bad2.ldefs").write_text("<language_definitions>", encoding="ascii")

    with pytest.raises(InternalError) as exc_info:
        enumerate_runtime_data_language_compilers(str(runtime_dir))

    error_message = exc_info.value.message
    assert "No valid language/compiler pairs found" in error_message
    assert str(runtime_dir / "languages" / "bad1.ldefs") in error_message
    assert str(runtime_dir / "languages" / "bad2.ldefs") in error_message


def test_runtime_data_enumeration_returns_empty_list_for_none_runtime_dir() -> None:
    """`runtime_data_dir=None` keeps returning an empty pair list."""
    assert enumerate_runtime_data_language_compilers(None) == []


def test_runtime_data_enumeration_rejects_missing_runtime_dir(tmp_path: Path) -> None:
    """Missing runtime-data directory remains a deterministic startup error."""
    missing_runtime_dir = tmp_path / "does-not-exist"

    with pytest.raises(InternalError) as exc_info:
        enumerate_runtime_data_language_compilers(str(missing_runtime_dir))

    error_message = exc_info.value.message
    assert "runtime_data_dir does not exist" in error_message
    assert str(missing_runtime_dir) in error_message


def test_runtime_data_resolution_uses_compatible_ghidra_sleigh_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Compatible ghidra-sleigh installs become the public default runtime-data root."""
    runtime_dir = tmp_path / "runtime_data"
    runtime_dir.mkdir()
    ghidra_sleigh_module = _GhidraSleighModuleDouble(runtime_dir)
    monkeypatch.setattr(
        runtime_data_module.importlib,
        "import_module",
        lambda _: ghidra_sleigh_module,
    )

    assert resolve_session_runtime_data_dir(None) == str(runtime_dir)


def test_runtime_data_resolution_warns_on_default_pin_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Auto-discovered defaults stay usable but warn on upstream-pin drift."""
    runtime_dir = tmp_path / "runtime_data"
    runtime_dir.mkdir()
    ghidra_sleigh_module = _GhidraSleighModuleDouble(
        runtime_dir,
        ghidra_tag="Ghidra_12.0.3_build",
        ghidra_commit="09f14c92d3da6e5d5f6b7dea115409719db3cce1",
    )
    monkeypatch.setattr(
        runtime_data_module.importlib,
        "import_module",
        lambda _: ghidra_sleigh_module,
    )

    with pytest.warns(RuntimeWarning, match="does not match flatline's pinned Ghidra"):
        resolved_runtime_dir = resolve_session_runtime_data_dir(None)

    assert resolved_runtime_dir == str(runtime_dir)


def test_runtime_data_resolution_rejects_missing_packaged_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Omitted runtime_data_dir is a startup error when the dependency is absent."""

    def _raise_import_error(_: str) -> Path:
        raise ImportError("module not found")

    monkeypatch.setattr(runtime_data_module.importlib, "import_module", _raise_import_error)

    with pytest.raises(InternalError) as exc_info:
        resolve_session_runtime_data_dir(None)

    assert "flatline requires ghidra-sleigh" in exc_info.value.message


def test_runtime_data_resolution_preserves_explicit_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Explicit runtime-data overrides bypass ghidra-sleigh auto-discovery."""
    runtime_dir = tmp_path / "runtime_data"
    runtime_dir.mkdir()

    def _unexpected_import(_: str) -> Path:
        raise AssertionError("explicit runtime_data_dir should not import ghidra_sleigh")

    monkeypatch.setattr(runtime_data_module.importlib, "import_module", _unexpected_import)

    assert resolve_session_runtime_data_dir(runtime_dir) == str(runtime_dir)
