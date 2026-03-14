"""Unit tests for the initial public release workflow and SemVer recommendation."""

from __future__ import annotations

from pathlib import Path

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
    (repo_root / "docs" / "release_workflow.md").write_text(
        "\n".join(
            [
                "# Initial Public Release Workflow",
                "",
                "- Current development version: `0.1.0.dev0`",
                "- Recommended first public version: `0.1.0`",
                "- Run `python -m flatline._release`",
                "- Run `python -m flatline._compliance`",
                "- Run `python -m flatline._footprint`",
                "- Run `tox`",
                "- Run `python -m build`",
                "- Update `CHANGELOG.md`",
                "- Create `git tag v0.1.0`",
                "",
            ]
        ),
        encoding="ascii",
    )


def test_u021_initial_public_release_workflow_is_source_controlled() -> None:
    """U-021: Initial public release workflow and SemVer decision stay explicit."""
    repo_root = Path(__file__).resolve().parents[2]
    workflow_doc = (repo_root / "docs" / "release_workflow.md").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")

    report = audit_initial_public_release_readiness(repo_root)

    assert report.is_ready
    assert report.current_version == "0.1.0.dev0"
    assert report.recommended_release_version == "0.1.0"
    assert report.semver_decision == "initial_public_release"
    assert report.required_artifacts == (
        "CHANGELOG.md",
        "README.md",
        "docs/compliance.md",
        "docs/release_notes.md",
        "docs/release_workflow.md",
    )

    required_workflow_fragments = (
        "# Initial Public Release Workflow",
        "0.1.0.dev0",
        "`0.1.0`",
        "python -m flatline._release",
        "python -m flatline._compliance",
        "python -m flatline._footprint",
        "tox",
        "python -m build",
        "CHANGELOG.md",
        "git tag v0.1.0",
    )
    for fragment in required_workflow_fragments:
        assert fragment in workflow_doc

    assert "docs/release_workflow.md" in readme


def test_u021_release_readiness_audit_rejects_missing_workflow_and_version_drift(
    tmp_path: Path,
) -> None:
    """U-021: Missing workflow docs and version drift fail the readiness audit."""
    _write_minimal_release_ready_repo(tmp_path)

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
    assert "release_workflow_missing" in issue_codes
    assert "version_mismatch" in issue_codes
