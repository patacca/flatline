"""Unit tests for release-compliance audit behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("flatline_dev.compliance", reason="dev-only module not shipped in wheel")
from flatline_dev.compliance import audit_release_compliance


def _write_minimal_compliant_repo(repo_root: Path) -> None:
    (repo_root / "tests" / "fixtures").mkdir(parents=True)
    (repo_root / "third_party" / "ghidra").mkdir(parents=True)

    (repo_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'license = "GPL-3.0-or-later"',
                'license-files = ["LICENSE", "THIRD_PARTY_NOTICES"]',
                "dependencies = [",
                '    "ghidra-sleigh",',
                '    "networkx",',
                "]",
                "",
            ]
        ),
        encoding="ascii",
    )
    (repo_root / "LICENSE").write_text("GPL-3.0-or-later placeholder\n", encoding="ascii")
    (repo_root / "THIRD_PARTY_NOTICES").write_text(
        "\n".join(
            [
                "Ghidra upstream license text",
                "OGDF upstream license text",
                "libavoid upstream license text",
                "zlib upstream license text",
                "nanobind upstream license text",
                "",
            ]
        ),
        encoding="ascii",
    )
    (repo_root / "README.md").write_text(
        "See THIRD_PARTY_NOTICES for release-time third-party attribution.\n",
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
        "THIRD_PARTY_NOTICES",
        "third_party/ghidra/LICENSE",
        "third_party/ghidra/NOTICE",
        "tests/fixtures/README.md",
    )


def test_u017_release_compliance_audit_rejects_missing_notice_and_dependency_gap(
    tmp_path: Path,
) -> None:
    """U-017: Missing notice files and missing dependency are surfaced deterministically."""
    _write_minimal_compliant_repo(tmp_path)
    (tmp_path / "THIRD_PARTY_NOTICES").unlink()
    (tmp_path / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'license = "GPL-3.0-or-later"',
                'license-files = ["LICENSE", "THIRD_PARTY_NOTICES"]',
                "dependencies = []",
                "",
            ]
        ),
        encoding="ascii",
    )

    report = audit_release_compliance(tmp_path)

    assert not report.is_compliant
    issue_codes = {issue.code for issue in report.issues}
    assert "notice_file_missing" in issue_codes
    assert "dependency_missing" in issue_codes
