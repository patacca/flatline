"""Unit tests for the lint tox env and lint extra dependency contract."""

from __future__ import annotations

import tomllib
from pathlib import Path


def test_u033_lint_tox_env_matches_lint_extra_dependencies() -> None:
    """U-033: The tox lint env mirrors the published lint extra dependencies."""
    repo_root = Path(__file__).resolve().parents[2]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))

    lint_extra = pyproject["project"]["optional-dependencies"]["lint"]
    lint_env = pyproject["tool"]["tox"]["env"]["lint"]

    assert lint_env["package"] == "skip"
    assert lint_env["extras"] == []
    assert lint_env["deps"] == lint_extra
