"""Shared pytest configuration, markers, and fixture stubs for flatline tests."""

from __future__ import annotations

import importlib
import importlib.util
import os
import pathlib

import pytest

from flatline._windows import configure_windows_native_dll_dirs
from tests._native_fixtures import get_native_runtime_data_dir

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
NATIVE_MODULE = "flatline._flatline_native"
NATIVE_SKIP_REASON = (
    "requires native bridge extension; ensure the tox test env can build/install "
    "flatline with flatline._flatline_native importable and ghidra-sleigh available"
)
STRICT_NATIVE_ENV_VAR = "FLATLINE_REQUIRE_NATIVE_BRIDGE"


def _native_bridge_available() -> bool:
    """Return whether the compiled native bridge extension is importable."""
    if importlib.util.find_spec(NATIVE_MODULE) is None:
        return False
    # Match the package runtime import path so Windows source-built wheels can
    # register the vcpkg zlib DLL directory before the extension import.
    configure_windows_native_dll_dirs()
    try:
        importlib.import_module(NATIVE_MODULE)
    except ImportError:
        return False
    return True


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
    strict_native_required = os.environ.get(STRICT_NATIVE_ENV_VAR) == "1"
    if strict_native_required and not native_bridge_available:
        requires_native_items = [
            item for item in items if item.get_closest_marker("requires_native")
        ]
        if requires_native_items:
            raise pytest.UsageError(
                "strict native test mode requires flatline._flatline_native to be importable; "
                + NATIVE_SKIP_REASON
            )
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


@pytest.fixture
def native_runtime_data_dir() -> str:
    """Return the installed `ghidra_sleigh` runtime-data root used by native tests."""
    try:
        return get_native_runtime_data_dir()
    except RuntimeError as exc:
        pytest.skip(str(exc))
