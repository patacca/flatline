"""Unit tests for the repo-only dev-tool layout."""

from __future__ import annotations

from pathlib import Path


def test_u024_repo_only_dev_tools_live_outside_the_shipped_package() -> None:
    """U-024: Dev/release tooling stays physically separated from src/flatline."""
    repo_root = Path(__file__).resolve().parents[2]
    package_dir = repo_root / "src" / "flatline"
    tools_dir = repo_root / "tools"
    dev_package_dir = tools_dir / "flatline_dev"

    assert (tools_dir / "artifacts.py").is_file()
    assert (tools_dir / "compliance.py").is_file()
    assert (tools_dir / "footprint.py").is_file()
    assert (tools_dir / "release.py").is_file()
    assert (dev_package_dir / "__init__.py").is_file()
    assert (dev_package_dir / "artifacts.py").is_file()
    assert (dev_package_dir / "compliance.py").is_file()
    assert (dev_package_dir / "footprint.py").is_file()
    assert (dev_package_dir / "release.py").is_file()

    assert not (package_dir / "_artifacts.py").exists()
    assert not (package_dir / "_compliance.py").exists()
    assert not (package_dir / "_footprint.py").exists()
    assert not (package_dir / "_release.py").exists()
