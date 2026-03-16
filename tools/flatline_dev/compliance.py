"""Release-compliance audit helpers for packaging and redistribution."""

from __future__ import annotations

import argparse
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_ARTIFACTS = (
    "LICENSE",
    "NOTICE",
    "docs/compliance.md",
    "third_party/ghidra/LICENSE",
    "third_party/ghidra/NOTICE",
    "tests/fixtures/README.md",
)


@dataclass(frozen=True)
class ComplianceIssue:
    """One deterministic compliance-audit failure."""

    code: str
    message: str


@dataclass(frozen=True)
class ComplianceReport:
    """Compliance-audit result for one repo root."""

    required_artifacts: tuple[str, ...]
    issues: tuple[ComplianceIssue, ...]

    @property
    def is_compliant(self) -> bool:
        """Return True when no compliance issues were found."""
        return not self.issues


def _append_issue(issues: list[ComplianceIssue], code: str, message: str) -> None:
    issues.append(ComplianceIssue(code=code, message=message))


def _read_text(path: Path, *, missing_code: str, issues: list[ComplianceIssue]) -> str | None:
    if not path.is_file():
        _append_issue(issues, missing_code, f"Required file is missing: {path}")
        return None

    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        _append_issue(issues, f"{missing_code}_unreadable", f"Could not read {path}: {exc}")
        return None


def _require_fragments(
    *,
    text: str,
    fragments: Sequence[str],
    code: str,
    label: str,
    issues: list[ComplianceIssue],
) -> None:
    missing_fragments = [fragment for fragment in fragments if fragment not in text]
    if missing_fragments:
        joined_fragments = ", ".join(missing_fragments)
        _append_issue(
            issues,
            code,
            f"{label} is missing required references: {joined_fragments}",
        )


def _load_pyproject(repo_root: Path, issues: list[ComplianceIssue]) -> dict[str, Any] | None:
    pyproject_path = repo_root / "pyproject.toml"
    pyproject_text = _read_text(
        pyproject_path,
        missing_code="pyproject_missing",
        issues=issues,
    )
    if pyproject_text is None:
        return None

    try:
        loaded = tomllib.loads(pyproject_text)
    except tomllib.TOMLDecodeError as exc:
        _append_issue(
            issues,
            "pyproject_invalid",
            f"pyproject.toml is not valid TOML: {exc}",
        )
        return None

    project_table = loaded.get("project")
    if not isinstance(project_table, dict):
        _append_issue(
            issues,
            "pyproject_project_missing",
            "pyproject.toml is missing the [project] table.",
        )
        return None
    return project_table


def _audit_pyproject(project_table: dict[str, Any], issues: list[ComplianceIssue]) -> None:
    if project_table.get("license") != "Apache-2.0":
        _append_issue(
            issues,
            "project_license_mismatch",
            'pyproject.toml must declare `license = "Apache-2.0"`.',
        )

    license_files = project_table.get("license-files")
    if not isinstance(license_files, list) or not {"LICENSE", "NOTICE"}.issubset(
        {str(item) for item in license_files}
    ):
        _append_issue(
            issues,
            "pyproject_license_files_missing",
            'pyproject.toml must declare `license-files = ["LICENSE", "NOTICE"]`.',
        )

    dependencies = project_table.get("dependencies")
    if not isinstance(dependencies, list) or not any(
        isinstance(dep, str) and dep.startswith("ghidra-sleigh")
        for dep in dependencies
    ):
        _append_issue(
            issues,
            "dependency_missing",
            "pyproject.toml must declare `ghidra-sleigh` as a dependency.",
        )


def audit_release_compliance(repo_root: str | Path) -> ComplianceReport:
    """Audit the repo's mandatory redistribution artifacts and references."""
    root = Path(repo_root).resolve()
    issues: list[ComplianceIssue] = []

    project_table = _load_pyproject(root, issues)
    if project_table is not None:
        _audit_pyproject(project_table, issues)

    artifact_texts: dict[str, str | None] = {}
    for relative_path, code in (
        ("LICENSE", "license_file_missing"),
        ("NOTICE", "notice_file_missing"),
        ("docs/compliance.md", "compliance_doc_missing"),
        ("third_party/ghidra/LICENSE", "ghidra_license_missing"),
        ("third_party/ghidra/NOTICE", "ghidra_notice_missing"),
        ("tests/fixtures/README.md", "fixture_manifest_missing"),
    ):
        artifact_texts[relative_path] = _read_text(
            root / relative_path,
            missing_code=code,
            issues=issues,
        )

    notice_text = artifact_texts["NOTICE"]
    if notice_text is not None:
        _require_fragments(
            text=notice_text,
            fragments=(
                "third_party/ghidra/LICENSE",
                "third_party/ghidra/NOTICE",
                "tests/fixtures/README.md",
            ),
            code="notice_missing_reference",
            label="NOTICE",
            issues=issues,
        )

    compliance_doc_text = artifact_texts["docs/compliance.md"]
    if compliance_doc_text is not None:
        _require_fragments(
            text=compliance_doc_text,
            fragments=(
                "ADR-007",
                "Artifact Manifest",
                "Release Checklist",
                "python tools/compliance.py",
                "NOTICE",
            ),
            code="compliance_doc_missing_reference",
            label="docs/compliance.md",
            issues=issues,
        )

    fixture_manifest_text = artifact_texts["tests/fixtures/README.md"]
    if fixture_manifest_text is not None:
        _require_fragments(
            text=fixture_manifest_text,
            fragments=(
                "License / redistribution note:",
                "redistributable synthetic machine code",
            ),
            code="fixture_notice_missing",
            label="tests/fixtures/README.md",
            issues=issues,
        )

    readme_text = _read_text(root / "README.md", missing_code="readme_missing", issues=issues)
    if readme_text is not None and "NOTICE" not in readme_text:
        _append_issue(
            issues,
            "readme_notice_reference_missing",
            "README.md must reference NOTICE for redistribution guidance.",
        )

    return ComplianceReport(
        required_artifacts=REQUIRED_ARTIFACTS,
        issues=tuple(issues),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the compliance audit as a small release-time CLI."""
    parser = argparse.ArgumentParser(
        prog="python tools/compliance.py",
        description="Audit the flatline repo's release-compliance artifacts.",
    )
    parser.add_argument(
        "repo_root",
        nargs="?",
        default=".",
        help="Repository root to audit (default: current directory).",
    )
    args = parser.parse_args(argv)

    report = audit_release_compliance(args.repo_root)
    audited_root = Path(args.repo_root).resolve()
    if report.is_compliant:
        print(f"Compliance audit passed: {audited_root}")
        return 0

    print(f"Compliance audit failed: {audited_root}")
    for issue in report.issues:
        print(f"- {issue.code}: {issue.message}")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
