"""Unit tests for runtime-data language/compiler enumeration behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from flatline import InternalError, LanguageCompilerPair
from flatline._runtime_data import enumerate_runtime_data_language_compilers


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
    assert "bad.ldefs" in str(warning_records[0].message)


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

    assert "No valid language/compiler pairs found" in exc_info.value.message
    assert "bad1.ldefs" in exc_info.value.message
    assert "bad2.ldefs" in exc_info.value.message


def test_runtime_data_enumeration_returns_empty_list_for_none_runtime_dir() -> None:
    """`runtime_data_dir=None` keeps returning an empty pair list."""
    assert enumerate_runtime_data_language_compilers(None) == []


def test_runtime_data_enumeration_rejects_missing_runtime_dir(tmp_path: Path) -> None:
    """Missing runtime-data directory remains a deterministic startup error."""
    missing_runtime_dir = tmp_path / "does-not-exist"

    with pytest.raises(InternalError) as exc_info:
        enumerate_runtime_data_language_compilers(str(missing_runtime_dir))

    assert "runtime_data_dir does not exist" in exc_info.value.message

