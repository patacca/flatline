"""Unit tests for default-install footprint measurement and documentation."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

pytest.importorskip("flatline._footprint", reason="dev-only module not shipped in wheel")
from flatline._compliance import expected_ghidra_sleigh_version
from flatline._footprint import (
    format_default_install_footprint,
    measure_default_install_footprint,
)


class _DistributionDouble:
    """Small importlib.metadata distribution double for payload-size tests."""

    def __init__(self, name: str, root: Path, files: list[str]) -> None:
        self.metadata = {"Name": name}
        self.files = tuple(PurePosixPath(relative_path) for relative_path in files)
        self._root = root

    def locate_file(self, relative_path: PurePosixPath) -> Path:
        return self._root / Path(relative_path)


def _write_sized_file(path: Path, size_bytes: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size_bytes)


def test_u018_default_install_footprint_uses_payload_files_only(tmp_path: Path) -> None:
    """U-018: Default-install footprint excludes `__pycache__` noise deterministically."""
    site_packages = tmp_path / "site-packages"
    runtime_data_dir = site_packages / "ghidra_sleigh" / "data"

    _write_sized_file(site_packages / "flatline" / "__init__.py", 11)
    _write_sized_file(site_packages / "flatline" / "_bridge.py", 29)
    _write_sized_file(site_packages / "flatline" / "__pycache__" / "__init__.pyc", 999)
    _write_sized_file(site_packages / "flatline-0.1.0.dev0.dist-info" / "METADATA", 7)

    _write_sized_file(site_packages / "ghidra_sleigh" / "__init__.py", 13)
    _write_sized_file(runtime_data_dir / "processors" / "x86.sla", 100)
    _write_sized_file(runtime_data_dir / "languages" / "x86.ldefs", 20)
    _write_sized_file(site_packages / "ghidra_sleigh" / "__pycache__" / "__init__.pyc", 888)
    _write_sized_file(site_packages / "ghidra_sleigh-12.0.4.dist-info" / "METADATA", 17)

    distributions = {
        "flatline": _DistributionDouble(
            "flatline",
            site_packages,
            [
                "flatline/__init__.py",
                "flatline/_bridge.py",
                "flatline/__pycache__/__init__.pyc",
                "flatline-0.1.0.dev0.dist-info/METADATA",
            ],
        ),
        "ghidra-sleigh": _DistributionDouble(
            "ghidra-sleigh",
            site_packages,
            [
                "ghidra_sleigh/__init__.py",
                "ghidra_sleigh/data/processors/x86.sla",
                "ghidra_sleigh/data/languages/x86.ldefs",
                "ghidra_sleigh/__pycache__/__init__.pyc",
                "ghidra_sleigh-12.0.4.dist-info/METADATA",
            ],
        ),
    }

    report = measure_default_install_footprint(
        distribution_loader=lambda name: distributions[name],
        runtime_data_dir_resolver=lambda: runtime_data_dir,
    )

    assert report.flatline_distribution.size_bytes == 47
    assert report.flatline_distribution.file_count == 3
    assert report.ghidra_sleigh_distribution.size_bytes == 150
    assert report.ghidra_sleigh_distribution.file_count == 4
    assert report.ghidra_sleigh_runtime_data.size_bytes == 120
    assert report.ghidra_sleigh_runtime_data.file_count == 2
    assert report.combined_distribution.size_bytes == 197
    assert report.combined_distribution.file_count == 7

    rendered = format_default_install_footprint(report)
    assert "payload files only; excludes __pycache__" in rendered
    assert "197 bytes" in rendered
    assert "Runtime data share of combined footprint: 60.9%" in rendered


def test_u018_footprint_doc_records_current_policy() -> None:
    """U-018: The committed footprint doc preserves the pinned measurement workflow."""
    repo_root = Path(__file__).resolve().parents[2]
    footprint_doc = (repo_root / "docs" / "footprint.md").read_text(encoding="utf-8")

    assert "python -m flatline._footprint" in footprint_doc
    assert "payload files only" in footprint_doc
    assert f"ghidra-sleigh == {expected_ghidra_sleigh_version()}" in footprint_doc
    assert "all_processors=false" in footprint_doc
    assert "silent default ISA pruning" in footprint_doc
