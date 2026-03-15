"""Unit tests for the public artifact review checklist."""

from __future__ import annotations

from pathlib import Path


def test_u023_public_artifact_review_checklist_is_source_controlled() -> None:
    """U-023: The human P5 artifact-review gate stays explicit and auditable."""
    repo_root = Path(__file__).resolve().parents[2]
    review_doc = (repo_root / "docs" / "release_review.md").read_text(encoding="utf-8")
    workflow_doc = (repo_root / "docs" / "release_workflow.md").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")

    required_review_fragments = (
        "# Public Artifact Review Checklist",
        "## Preconditions",
        "## Review Evidence",
        "## Approval Signal",
        "`0.1.0`",
        "python tools/release.py",
        "tox",
        "python tools/compliance.py",
        "python tools/footprint.py",
        "python -m build",
        "python tools/artifacts.py dist",
        "LICENSE",
        "NOTICE",
        "docs/release_notes.md",
        "CHANGELOG.md",
        "ghidra-sleigh == 12.0.4",
        "do not commit",
        "explicitly approves the release",
    )

    for fragment in required_review_fragments:
        assert fragment in review_doc

    assert "docs/release_review.md" in workflow_doc
    assert "docs/release_review.md" in readme
