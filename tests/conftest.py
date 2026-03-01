"""Shared pytest configuration, markers, and fixture stubs for ghidralib tests."""

from __future__ import annotations

import pathlib

import pytest

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


# ---------------------------------------------------------------------------
# Auto-apply markers based on test directory
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Automatically add category markers (unit, contract, …) based on path."""
    marker_map: dict[str, str] = {
        "unit": "unit",
        "contract": "contract",
        "integration": "integration",
        "regression": "regression",
        "negative": "negative",
    }
    for item in items:
        rel = pathlib.Path(item.fspath).relative_to(REPO_ROOT / "tests")
        top_dir = rel.parts[0] if rel.parts else ""
        if top_dir in marker_map:
            item.add_marker(getattr(pytest.mark, marker_map[top_dir]))


# ---------------------------------------------------------------------------
# Fixture directory helper
# ---------------------------------------------------------------------------

@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    """Return the path to the test fixtures directory."""
    return FIXTURES_DIR
