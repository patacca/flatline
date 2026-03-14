"""Unit tests for the initial public release workflow and SemVer recommendation."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytest.importorskip("flatline._release", reason="dev-only module not shipped in wheel")
from flatline._release import audit_initial_public_release_readiness


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
                "[docs/release_notes.md](docs/release_notes.md)",
                "[docs/release_review.md](docs/release_review.md)",
                "[docs/release_workflow.md](docs/release_workflow.md)",
                "",
            ]
        ),
        encoding="ascii",
    )
    (repo_root / "docs" / "compliance.md").write_text(
        "# Compliance\n\npython -m flatline._compliance\n",
        encoding="ascii",
    )
    (repo_root / "docs" / "release_notes.md").write_text(
        "# Initial Public Release Notes\n",
        encoding="ascii",
    )
    (repo_root / "docs" / "release_review.md").write_text(
        "\n".join(
            [
                "# Public Artifact Review Checklist",
                "",
                "## Preconditions",
                "- Current development version: `0.1.0.dev0`",
                "- Planned public tag: `0.1.0`",
                "- Run `python -m flatline._release`",
                "- Run `tox`",
                "- Run `python -m flatline._compliance`",
                "- Run `python -m flatline._footprint`",
                "- Run `python -m build`",
                "- Run `python -m flatline._artifacts dist`",
                "",
                "## Review Evidence",
                "- Verify `LICENSE` and `NOTICE` in the artifacts.",
                "- Review `docs/release_notes.md` and `CHANGELOG.md`.",
                "- Confirm `ghidra-sleigh == 12.0.4`.",
                "",
                "## Approval Record",
                "- Reviewer:",
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
                "- Run `python -m flatline._release`",
                "- Run `python -m flatline._compliance`",
                "- Run `python -m flatline._footprint`",
                "- Run `tox`",
                "- Run `python -m build`",
                "- Run `python -m flatline._artifacts dist`",
                "- Review `docs/release_review.md`",
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


def test_u021_initial_public_release_workflow_is_source_controlled(tmp_path: Path) -> None:
    """U-021: Initial public release workflow and SemVer decision stay explicit."""
    workspace_repo_root = Path(__file__).resolve().parents[2]
    workflow_doc = (workspace_repo_root / "docs" / "release_workflow.md").read_text(
        encoding="utf-8"
    )
    readme = (workspace_repo_root / "README.md").read_text(encoding="utf-8")
    pyproject = (workspace_repo_root / "pyproject.toml").read_text(encoding="utf-8")

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

    required_workflow_fragments = (
        "# Initial Public Release Workflow",
        "0.1.0.dev0",
        "`0.1.0`",
        "git status --short",
        "python -m flatline._release",
        "python -m flatline._compliance",
        "python -m flatline._footprint",
        "tox",
        "python -m build",
        "python -m flatline._artifacts",
        "docs/release_review.md",
        "CHANGELOG.md",
        "git tag v0.1.0",
    )
    for fragment in required_workflow_fragments:
        assert fragment in workflow_doc

    assert "docs/release_workflow.md" in readme
    assert "docs/release_review.md" in readme
    assert '"build >= ' in pyproject


def test_u021_release_readiness_audit_rejects_missing_workflow_and_version_drift(
    tmp_path: Path,
) -> None:
    """U-021: Missing workflow docs and version drift fail the readiness audit."""
    _write_minimal_release_ready_repo(tmp_path)
    _init_git_repo(tmp_path)

    (tmp_path / "docs" / "release_workflow.md").unlink()
    (tmp_path / "meson.build").write_text(
        "\n".join(
            [
                "project(",
                "  'flatline',",
                "  'cpp',",
                "  version: '0.2.0.dev0',",
                ")",
                "",
            ]
        ),
        encoding="ascii",
    )

    report = audit_initial_public_release_readiness(tmp_path)

    assert not report.is_ready
    issue_codes = {issue.code for issue in report.issues}
    assert "git_worktree_dirty" in issue_codes
    assert "release_workflow_missing" in issue_codes
    assert "version_mismatch" in issue_codes
