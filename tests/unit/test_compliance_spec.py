"""Unit tests for release-compliance audit behavior."""

from __future__ import annotations

from pathlib import Path

from flatline._compliance import audit_release_compliance, expected_ghidra_sleigh_version
from flatline._version import UPSTREAM_COMMIT, UPSTREAM_TAG


def _write_minimal_compliant_repo(repo_root: Path) -> None:
    (repo_root / "docs").mkdir(parents=True)
    (repo_root / "tests" / "fixtures").mkdir(parents=True)
    (repo_root / "third_party" / "ghidra").mkdir(parents=True)

    expected_version = expected_ghidra_sleigh_version()

    (repo_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'license = "Apache-2.0"',
                'license-files = ["LICENSE", "NOTICE"]',
                "dependencies = [",
                f'    "ghidra-sleigh == {expected_version}",',
                "]",
                "",
            ]
        ),
        encoding="ascii",
    )
    (repo_root / "LICENSE").write_text("Apache License placeholder\n", encoding="ascii")
    (repo_root / "NOTICE").write_text(
        "\n".join(
            [
                "flatline release notice",
                f"Bundled native-source baseline: {UPSTREAM_TAG} ({UPSTREAM_COMMIT})",
                "Upstream notices: third_party/ghidra/LICENSE and third_party/ghidra/NOTICE",
                f"Default runtime dependency: ghidra-sleigh == {expected_version}",
                "Fixture redistribution note: tests/fixtures/README.md",
                "",
            ]
        ),
        encoding="ascii",
    )
    (repo_root / "README.md").write_text(
        "See NOTICE for release-time third-party attribution.\n",
        encoding="ascii",
    )
    (repo_root / "docs" / "compliance.md").write_text(
        "\n".join(
            [
                "# Compliance",
                "",
                "## ADR-007 Decision",
                f"- Pinned baseline: {UPSTREAM_TAG} / {UPSTREAM_COMMIT}",
                f"- Default runtime dependency: ghidra-sleigh == {expected_version}",
                "",
                "## Artifact Manifest",
                "- Root notice file: NOTICE",
                "",
                "## Release Checklist",
                "- Run `python -m flatline._compliance` before release.",
                "",
            ]
        ),
        encoding="ascii",
    )
    (repo_root / "tests" / "fixtures" / "README.md").write_text(
        (
            "License / redistribution note: all fixture bytes are redistributable "
            "synthetic machine code.\n"
        ),
        encoding="ascii",
    )
    (repo_root / "third_party" / "ghidra" / "LICENSE").write_text(
        "Upstream license placeholder\n",
        encoding="ascii",
    )
    (repo_root / "third_party" / "ghidra" / "NOTICE").write_text(
        "Upstream notice placeholder\n",
        encoding="ascii",
    )


def test_u017_release_compliance_audit_accepts_current_repo_manifest() -> None:
    """U-017: The committed repo satisfies the ADR-007 compliance audit."""
    repo_root = Path(__file__).resolve().parents[2]

    report = audit_release_compliance(repo_root)

    assert report.is_compliant
    assert report.issues == ()
    assert report.required_artifacts == (
        "LICENSE",
        "NOTICE",
        "docs/compliance.md",
        "third_party/ghidra/LICENSE",
        "third_party/ghidra/NOTICE",
        "tests/fixtures/README.md",
    )


def test_u017_release_compliance_audit_rejects_missing_notice_and_pin_drift(
    tmp_path: Path,
) -> None:
    """U-017: Missing notice files and dependency pin drift are surfaced deterministically."""
    _write_minimal_compliant_repo(tmp_path)
    (tmp_path / "NOTICE").unlink()
    (tmp_path / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'license = "Apache-2.0"',
                'license-files = ["LICENSE", "NOTICE"]',
                "dependencies = [",
                '    "ghidra-sleigh == 12.0.3",',
                "]",
                "",
            ]
        ),
        encoding="ascii",
    )

    report = audit_release_compliance(tmp_path)

    assert not report.is_compliant
    issue_codes = {issue.code for issue in report.issues}
    assert "notice_file_missing" in issue_codes
    assert "dependency_pin_mismatch" in issue_codes
