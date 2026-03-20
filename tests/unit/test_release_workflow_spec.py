"""Unit tests for the initial public release workflow and SemVer recommendation."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytest.importorskip("flatline_dev.release", reason="dev-only module not shipped in wheel")
from flatline_dev.release import audit_initial_public_release_readiness


def _write_minimal_release_ready_repo(repo_root: Path) -> None:
    (repo_root / "docs").mkdir(parents=True)
    (repo_root / "src" / "flatline").mkdir(parents=True)

    (repo_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'version = "0.1.0.dev0"',
                "",
                "[project.optional-dependencies]",
                'dev = ["build >= 1.2", "tox >= 4.0"]',
                "",
            ]
        ),
        encoding="ascii",
    )
    (repo_root / "meson.build").write_text(
        "\n".join(
            [
                "project(",
                "  'flatline',",
                "  'cpp',",
                "  version: '0.1.0.dev0',",
                ")",
                "",
            ]
        ),
        encoding="ascii",
    )
    (repo_root / "src" / "flatline" / "_version.py").write_text(
        '__version__ = "0.1.0.dev0"\n',
        encoding="ascii",
    )
    (repo_root / "CHANGELOG.md").write_text(
        "\n".join(
            [
                "# Changelog",
                "",
                "## [Unreleased]",
                "- Placeholder",
                "",
            ]
        ),
        encoding="ascii",
    )
    (repo_root / "README.md").write_text(
        "\n".join(
            [
                "# flatline",
                "",
                "## Requirements",
                "",
                "- Supported runtime host contract: Linux x86_64",
                ("- Published wheels: Linux x86_64/aarch64, Windows x86_64, macOS x86_64/arm64"),
                "",
                "## Project status",
                "",
                "The current roadmap focus is the P6.5 wheel distribution matrix.",
                "[docs/wheel_matrix.md](docs/wheel_matrix.md)",
                "",
                "[docs/release_notes.md](docs/release_notes.md)",
                "[docs/release_review.md](docs/release_review.md)",
                "[docs/release_workflow.md](docs/release_workflow.md)",
                "",
            ]
        ),
        encoding="ascii",
    )
    (repo_root / "docs" / "compliance.md").write_text(
        "# Compliance\n\npython tools/compliance.py\n",
        encoding="ascii",
    )
    (repo_root / "docs" / "release_notes.md").write_text(
        "\n".join(
            [
                "# Initial Public Release Notes",
                "",
                "## Support Tiers",
                "",
                "| Surface | Tier | Notes |",
                "| --- | --- | --- |",
                (
                    "| Host platform | Supported | Linux x86_64 only for the "
                    "runtime contract in this release line |"
                ),
                (
                    "| Wheel install availability | Published | `pip install "
                    "flatline` publishes wheels for Linux x86_64, Linux "
                    "aarch64, Windows x86_64, macOS x86_64, and macOS arm64, "
                    "so those installs work without a local compiler |"
                ),
                "",
                "Support-tier interpretation:",
                "- Wheel publication and supported-host status can differ.",
                "- Hosts reach support only after equivalent contract coverage.",
                "",
            ]
        )
        + "\n",
        encoding="ascii",
    )
    (repo_root / "docs" / "wheel_matrix.md").write_text(
        "# Platform/Architecture Wheel Matrix\n",
        encoding="ascii",
    )
    (repo_root / "docs" / "release_review.md").write_text(
        "\n".join(
            [
                "# Public Artifact Review Checklist",
                "",
                (
                    "This checklist is the manual human gate for the initial public "
                    "release of `0.1.0`."
                ),
                "",
                "## Preconditions",
                "- Run `python tools/release.py`",
                "- Run `tox`",
                "- Run `python tools/compliance.py`",
                "- Run `python tools/footprint.py`",
                "- Run `python -m build`",
                "- Run `python tools/artifacts.py dist`",
                "",
                "## Review Evidence",
                "- Verify `LICENSE` and `NOTICE` in the artifacts.",
                "- Review `docs/release_notes.md` and `CHANGELOG.md`.",
                "- Confirm `ghidra-sleigh` dependency is declared.",
                "",
                "## Approval Signal",
                "- Do not create `git tag v0.1.0` until the checklist passes.",
                "- Keep any manual review notes outside the repo; do not commit them.",
                "- Proceed only after the reviewer explicitly approves the release.",
                "",
            ]
        ),
        encoding="ascii",
    )
    (repo_root / "docs" / "release_workflow.md").write_text(
        "\n".join(
            [
                "# Initial Public Release Workflow",
                "",
                "- Current development version: `0.1.0.dev0`",
                "- Recommended first public version: `0.1.0`",
                "- Run `git status --short`",
                "- Run `python tools/release.py`",
                "- Run `python tools/compliance.py`",
                "- Run `python tools/footprint.py`",
                "- Run `tox`",
                "- Run `python -m build`",
                "- Run `python tools/artifacts.py dist`",
                "- Run the manual checklist in `docs/release_review.md`",
                "- Do not commit review notes",
                "- Update `CHANGELOG.md`",
                "- Create `git tag v0.1.0`",
                "",
            ]
        ),
        encoding="ascii",
    )


def _init_git_repo(repo_root: Path) -> None:
    subprocess.run(
        ["git", "-C", str(repo_root), "init", "--initial-branch=main"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.name", "flatline-tests"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.email", "flatline@example.com"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "add", "."],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "commit", "-m", "initial"],
        check=True,
        capture_output=True,
        text=True,
    )


def test_u021_release_readiness_audit_accepts_compliant_repo(tmp_path: Path) -> None:
    """U-021: A compliant synthetic repo passes the initial-public-release audit."""
    audit_repo_root = tmp_path / "release-ready"
    _write_minimal_release_ready_repo(audit_repo_root)
    _init_git_repo(audit_repo_root)

    report = audit_initial_public_release_readiness(audit_repo_root)

    assert report.is_ready
    assert report.current_version == "0.1.0.dev0"
    assert report.recommended_release_version == "0.1.0"
    assert report.semver_decision == "initial_public_release"
    assert report.required_artifacts == (
        "CHANGELOG.md",
        "README.md",
        "docs/compliance.md",
        "docs/release_notes.md",
        "docs/release_review.md",
        "docs/release_workflow.md",
    )
