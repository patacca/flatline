"""Unit tests for native-forced tox envs used by host-feasibility lanes."""

from __future__ import annotations

import tomllib
from pathlib import Path


def test_u026_native_tox_env_forces_native_bridge_builds() -> None:
    """U-026: The host-feasibility tox env forces `native_bridge=enabled`."""
    repo_root = Path(__file__).resolve().parents[2]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    tox_envs = pyproject["tool"]["tox"]["env"]

    native_env = tox_envs["py314-native"]
    build_env_name = native_env["wheel_build_env"]
    build_env = tox_envs[build_env_name]

    assert build_env["config_settings_prepare_metadata_for_build_wheel"] == {
        "setup-args": "-Dnative_bridge=enabled"
    }
    assert build_env["config_settings_build_wheel"] == {"setup-args": "-Dnative_bridge=enabled"}
