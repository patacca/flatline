"""Shared pytest configuration, markers, and fixture stubs for flatline tests."""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
NATIVE_MODULE = "flatline._flatline_native"
NATIVE_SKIP_REASON = (
    "requires native bridge extension; ensure flatline._flatline_native is importable "
    "(for example: pip install -e \".[dev]\" -Csetup-args=-Dnative_bridge=enabled)"
)


def _native_bridge_available() -> bool:
    """Return whether the compiled native bridge extension is importable."""
    return importlib.util.find_spec(NATIVE_MODULE) is not None


# ---------------------------------------------------------------------------
# Auto-apply markers based on test directory
# ---------------------------------------------------------------------------

def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Automatically add category markers (unit, contract, ...) based on path."""
    marker_map: dict[str, str] = {
        "unit": "unit",
        "contract": "contract",
        "integration": "integration",
        "regression": "regression",
        "negative": "negative",
    }
    native_bridge_available = _native_bridge_available()
    for item in items:
        rel = pathlib.Path(item.fspath).relative_to(REPO_ROOT / "tests")
        top_dir = rel.parts[0] if rel.parts else ""
        if top_dir in marker_map:
            item.add_marker(getattr(pytest.mark, marker_map[top_dir]))
        if item.get_closest_marker("requires_native") and not native_bridge_available:
            item.add_marker(pytest.mark.skip(reason=NATIVE_SKIP_REASON))


# ---------------------------------------------------------------------------
# Fixture directory helper
# ---------------------------------------------------------------------------

@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    """Return the path to the test fixtures directory."""
    return FIXTURES_DIR
