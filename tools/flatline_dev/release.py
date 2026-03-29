"""Release-readiness helpers for flatline."""

from __future__ import annotations

import argparse
import re
import subprocess
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REQUIRED_ARTIFACTS = (
    "CHANGELOG.md",
    "README.md",
    "LICENSE",
    "NOTICE",
    "docs/release_notes.md",
    "docs/release_review.md",
    "docs/release_workflow.md",
)
PRE_1_0_PATCH_RELEASE_DECISION = "pre_1_0_patch_release"


@dataclass(frozen=True)
class ReleaseReadinessIssue:
    """One deterministic release-readiness audit failure."""

    code: str
    message: str


@dataclass(frozen=True)
class ReleaseReadinessReport:
    """Readiness report for the current release gate."""

    current_version: str
    recommended_release_version: str
    semver_decision: str
    required_artifacts: tuple[str, ...]
    issues: tuple[ReleaseReadinessIssue, ...]

    @property
    def is_ready(self) -> bool:
        """Return True when the current repo encodes the expected release state."""
        return not self.issues


def recommended_release_version(current_version: str) -> str:
    """Collapse a development version into the final public-release version."""
    dev_match = re.fullmatch(r"(?P<base>\d+\.\d+\.\d+)\.dev\d+", current_version)
    if dev_match is not None:
        return dev_match.group("base")
    return current_version


def current_release_decision(current_version: str) -> str:
    """Return the current release-line classification for the repo version."""
    if recommended_release_version(current_version) == "0.1.0":
        return "initial_public_release"
    return PRE_1_0_PATCH_RELEASE_DECISION


def _append_issue(issues: list[ReleaseReadinessIssue], code: str, message: str) -> None:
    issues.append(ReleaseReadinessIssue(code=code, message=message))


def _read_text(
    path: Path,
    *,
    missing_code: str,
    issues: list[ReleaseReadinessIssue],
) -> str | None:
    if not path.is_file():
        _append_issue(issues, missing_code, f"Required file is missing: {path}")
        return None

    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        _append_issue(issues, f"{missing_code}_unreadable", f"Could not read {path}: {exc}")
        return None


def _load_pyproject_version(
    repo_root: Path,
    issues: list[ReleaseReadinessIssue],
) -> str | None:
    pyproject_text = _read_text(
        repo_root / "pyproject.toml",
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

    version = project_table.get("version")
    if not isinstance(version, str) or not version:
        _append_issue(
            issues,
            "pyproject_version_missing",
            "pyproject.toml must declare a non-empty project version.",
        )
        return None

    optional_dependencies = project_table.get("optional-dependencies")
    if not isinstance(optional_dependencies, dict):
        _append_issue(
            issues,
            "pyproject_optional_dependencies_missing",
            "pyproject.toml must declare [project.optional-dependencies].",
        )
        return version

    dev_dependencies = optional_dependencies.get("dev")
    if not isinstance(dev_dependencies, list) or not any(
        isinstance(dependency, str) and re.match(r"build\b", dependency)
        for dependency in dev_dependencies
    ):
        _append_issue(
            issues,
            "dev_dependency_missing_build",
            "pyproject.toml dev extras must include the `build` package for release builds.",
        )
    return version


def _load_meson_version(repo_root: Path, issues: list[ReleaseReadinessIssue]) -> str | None:
    meson_text = _read_text(
        repo_root / "meson.build",
        missing_code="meson_build_missing",
        issues=issues,
    )
    if meson_text is None:
        return None

    version_match = re.search(r"version:\s*'([^']+)'", meson_text)
    if version_match is None:
        _append_issue(
            issues,
            "meson_version_missing",
            "meson.build must declare the flatline project version.",
        )
        return None
    return version_match.group(1)


def _load_package_version(repo_root: Path, issues: list[ReleaseReadinessIssue]) -> str | None:
    package_text = _read_text(
        repo_root / "src" / "flatline" / "_version.py",
        missing_code="package_version_file_missing",
        issues=issues,
    )
    if package_text is None:
        return None

    version_match = re.search(r'__version__\s*=\s*"([^"]+)"', package_text)
    if version_match is None:
        _append_issue(
            issues,
            "package_version_missing",
            "src/flatline/_version.py must declare __version__.",
        )
        return None
    return version_match.group(1)


def _audit_git_worktree(repo_root: Path, issues: list[ReleaseReadinessIssue]) -> None:
    try:
        repo_probe = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        _append_issue(
            issues,
            "git_unavailable",
            "git is required to audit release readiness.",
        )
        return
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        detail = f": {stderr}" if stderr else ""
        _append_issue(
            issues,
            "git_repo_missing",
            f"Release readiness requires a git worktree rooted at {repo_root}{detail}",
        )
        return

    repo_toplevel = Path(repo_probe.stdout.strip()).resolve()
    if repo_toplevel != repo_root:
        _append_issue(
            issues,
            "git_repo_root_mismatch",
            (
                "Release readiness must be run from the repository root: "
                f"expected {repo_root}, got {repo_toplevel}."
            ),
        )
        return

    status_result = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--short", "--untracked-files=all"],
        check=True,
        capture_output=True,
        text=True,
    )
    status_output = status_result.stdout.strip()
    if not status_output:
        return

    _append_issue(
        issues,
        "git_worktree_dirty",
        (
            "Git worktree must be clean before building release artifacts because "
            "Meson sdists omit uncommitted changes: "
            f"{status_output}"
        ),
    )


def audit_release_readiness(repo_root: str | Path) -> ReleaseReadinessReport:
    """Audit the repo's current release workflow and version recommendation."""
    root = Path(repo_root).resolve()
    issues: list[ReleaseReadinessIssue] = []

    _audit_git_worktree(root, issues)

    project_version = _load_pyproject_version(root, issues)
    meson_version = _load_meson_version(root, issues)
    package_version = _load_package_version(root, issues)

    resolved_versions = {
        value for value in (project_version, meson_version, package_version) if value is not None
    }
    current_version = project_version or package_version or meson_version or "<unknown>"
    release_version = recommended_release_version(current_version)
    semver_decision = current_release_decision(current_version)
    if len(resolved_versions) > 1:
        _append_issue(
            issues,
            "version_mismatch",
            (
                "Version strings must match across pyproject.toml, meson.build, and "
                f"src/flatline/_version.py: {sorted(resolved_versions)}"
            ),
        )

    for relative_path, code in (
        ("CHANGELOG.md", "changelog_missing"),
        ("README.md", "readme_missing"),
        ("LICENSE", "license_missing"),
        ("NOTICE", "notice_missing"),
        ("docs/release_notes.md", "release_notes_missing"),
        ("docs/release_review.md", "release_review_missing"),
        ("docs/release_workflow.md", "release_workflow_missing"),
    ):
        if not (root / relative_path).is_file():
            _append_issue(issues, code, f"Required file is missing: {root / relative_path}")

    return ReleaseReadinessReport(
        current_version=current_version,
        recommended_release_version=release_version,
        semver_decision=semver_decision,
        required_artifacts=REQUIRED_ARTIFACTS,
        issues=tuple(issues),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the release-readiness audit as a small CLI."""
    parser = argparse.ArgumentParser(
        prog="python tools/release.py",
        description="Audit the repo's current release workflow and version recommendation.",
    )
    parser.add_argument(
        "repo_root",
        nargs="?",
        default=".",
        help="Repository root to audit (default: current directory).",
    )
    args = parser.parse_args(argv)

    report = audit_release_readiness(args.repo_root)
    audited_root = Path(args.repo_root).resolve()
    if report.is_ready:
        print(f"Release readiness passed: {audited_root}")
        print(f"- Current version: {report.current_version}")
        print(f"- Recommended release version: {report.recommended_release_version}")
        print(f"- SemVer decision: {report.semver_decision}")
        return 0

    print(f"Release readiness failed: {audited_root}")
    print(f"- Current version: {report.current_version}")
    print(f"- Recommended release version: {report.recommended_release_version}")
    print(f"- SemVer decision: {report.semver_decision}")
    for issue in report.issues:
        print(f"- {issue.code}: {issue.message}")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
