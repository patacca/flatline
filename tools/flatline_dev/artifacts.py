"""Built release artifact audit helpers for flatline."""

from __future__ import annotations

import argparse
import re
import tarfile
import tomllib
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from email.parser import Parser
from pathlib import Path, PurePosixPath

REQUIRED_ARTIFACT_KINDS = ("wheel", "sdist")
_LEGACY_DEV_TOOL_FILES = frozenset(
    {"_artifacts.py", "_compliance.py", "_footprint.py", "_release.py"}
)


@dataclass(frozen=True)
class BuiltArtifactIssue:
    """One deterministic built-artifact audit failure."""

    code: str
    message: str


@dataclass(frozen=True)
class BuiltArtifactAuditReport:
    """Audit result for built wheel and sdist artifacts."""

    expected_version: str
    expected_dependency: str
    required_artifact_kinds: tuple[str, ...]
    wheel_artifacts: tuple[str, ...]
    sdist_artifacts: tuple[str, ...]
    issues: tuple[BuiltArtifactIssue, ...]

    @property
    def is_valid(self) -> bool:
        """Return True when the built artifacts satisfy the release audit."""
        return not self.issues


def _append_issue(issues: list[BuiltArtifactIssue], code: str, message: str) -> None:
    issues.append(BuiltArtifactIssue(code=code, message=message))


def _read_text(
    path: Path,
    *,
    missing_code: str,
    issues: list[BuiltArtifactIssue],
) -> str | None:
    if not path.is_file():
        _append_issue(issues, missing_code, f"Required file is missing: {path}")
        return None

    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        _append_issue(issues, f"{missing_code}_unreadable", f"Could not read {path}: {exc}")
        return None


def _load_repo_version(repo_root: Path, issues: list[BuiltArtifactIssue]) -> str:
    pyproject_text = _read_text(
        repo_root / "pyproject.toml",
        missing_code="pyproject_missing",
        issues=issues,
    )
    if pyproject_text is None:
        return "<unknown>"

    try:
        loaded = tomllib.loads(pyproject_text)
    except tomllib.TOMLDecodeError as exc:
        _append_issue(
            issues,
            "pyproject_invalid",
            f"pyproject.toml is not valid TOML: {exc}",
        )
        return "<unknown>"

    project_table = loaded.get("project")
    if not isinstance(project_table, dict):
        _append_issue(
            issues,
            "pyproject_project_missing",
            "pyproject.toml is missing the [project] table.",
        )
        return "<unknown>"

    version = project_table.get("version")
    if not isinstance(version, str) or not version:
        _append_issue(
            issues,
            "pyproject_version_missing",
            "pyproject.toml must declare a non-empty project version.",
        )
        return "<unknown>"
    return version


def _normalize_requirement(requirement: str) -> str:
    return re.sub(r"\s+", "", requirement).lower()


def _metadata_parser() -> Parser:
    return Parser()


def _audit_metadata(
    *,
    metadata_text: str,
    expected_version: str,
    expected_dependency: str,
    artifact_label: str,
    artifact_path: Path,
    issues: list[BuiltArtifactIssue],
) -> None:
    metadata = _metadata_parser().parsestr(metadata_text)
    version = metadata.get("Version")
    if version != expected_version:
        _append_issue(
            issues,
            f"{artifact_label}_version_mismatch",
            (f"{artifact_path} records version {version!r}; expected {expected_version!r}."),
        )

    requires_dist = metadata.get_all("Requires-Dist", failobj=[]) or []
    normalized_expected = _normalize_requirement(expected_dependency)
    if not any(
        _normalize_requirement(value).startswith(normalized_expected) for value in requires_dist
    ):
        _append_issue(
            issues,
            f"{artifact_label}_dependency_missing",
            (f"{artifact_path} does not declare the expected dependency {expected_dependency!r}."),
        )


def _has_named_member(member_names: Sequence[str], required_name: str) -> bool:
    return any(PurePosixPath(member_name).name == required_name for member_name in member_names)


def _contains_dev_only_content(
    member_names: Sequence[str],
    *,
    artifact_label: str,
    issues: list[BuiltArtifactIssue],
    strip_archive_root: bool = False,
) -> None:
    leaked_members: list[str] = []
    for member_name in member_names:
        member_path = PurePosixPath(member_name)
        parts = member_path.parts
        if strip_archive_root and parts:
            parts = parts[1:]
        if not parts:
            continue

        relative_path = PurePosixPath(*parts)
        if parts[0] == "tools":
            leaked_members.append(relative_path.as_posix())
            continue
        if "flatline_dev" in parts:
            leaked_members.append(relative_path.as_posix())
            continue
        if parts[0] == "flatline" and relative_path.name in _LEGACY_DEV_TOOL_FILES:
            leaked_members.append(relative_path.as_posix())

    if leaked_members:
        _append_issue(
            issues,
            f"{artifact_label}_dev_only_content_present",
            (
                f"{artifact_label} artifact contains repo-only dev tooling: "
                + ", ".join(sorted(leaked_members))
            ),
        )


_NATIVE_EXTENSION_SUFFIXES = (".so", ".dylib", ".pyd")


def _is_platform_specific_wheel(path: Path) -> bool:
    """Return True if the wheel filename indicates a platform-specific build."""
    stem = path.stem
    parts = stem.rsplit("-", maxsplit=1)
    if len(parts) < 2:
        return False
    platform_tag = parts[-1]
    return platform_tag != "any"


def _has_native_extension(member_names: Sequence[str]) -> bool:
    """Return True if the wheel contains a flatline native extension."""
    for member_name in member_names:
        member_path = PurePosixPath(member_name)
        if (
            member_path.parts
            and member_path.parts[0] == "flatline"
            and member_path.name.startswith("_flatline_native")
            and any(member_path.name.endswith(suffix) for suffix in _NATIVE_EXTENSION_SUFFIXES)
        ):
            return True
    return False


def _audit_wheel(
    path: Path,
    *,
    expected_version: str,
    expected_dependency: str,
    issues: list[BuiltArtifactIssue],
) -> None:
    try:
        with zipfile.ZipFile(path) as wheel_file:
            member_names = wheel_file.namelist()
            _contains_dev_only_content(
                member_names,
                artifact_label="wheel",
                issues=issues,
            )
            if not _has_named_member(member_names, "LICENSE"):
                _append_issue(
                    issues,
                    "wheel_license_missing",
                    f"{path} is missing LICENSE.",
                )
            if not _has_named_member(member_names, "NOTICE"):
                _append_issue(
                    issues,
                    "wheel_notice_missing",
                    f"{path} is missing NOTICE.",
                )

            if _is_platform_specific_wheel(path) and not _has_native_extension(member_names):
                _append_issue(
                    issues,
                    "wheel_native_extension_missing",
                    f"{path} is a platform-specific wheel but does not contain "
                    f"the native extension (_flatline_native).",
                )

            metadata_name = next(
                (
                    member_name
                    for member_name in member_names
                    if member_name.endswith(".dist-info/METADATA")
                ),
                None,
            )
            if metadata_name is None:
                _append_issue(
                    issues,
                    "wheel_metadata_missing",
                    f"{path} is missing dist-info/METADATA.",
                )
                return

            metadata_text = wheel_file.read(metadata_name).decode("utf-8")
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        _append_issue(issues, "wheel_archive_invalid", f"Could not inspect {path}: {exc}")
        return

    _audit_metadata(
        metadata_text=metadata_text,
        expected_version=expected_version,
        expected_dependency=expected_dependency,
        artifact_label="wheel",
        artifact_path=path,
        issues=issues,
    )


def _audit_sdist(
    path: Path,
    *,
    expected_version: str,
    expected_dependency: str,
    issues: list[BuiltArtifactIssue],
) -> None:
    try:
        with tarfile.open(path, mode="r:*") as sdist_file:
            members = [member for member in sdist_file.getmembers() if member.isfile()]
            member_names = [member.name for member in members]
            _contains_dev_only_content(
                member_names,
                artifact_label="sdist",
                issues=issues,
                strip_archive_root=True,
            )
            if not _has_named_member(member_names, "LICENSE"):
                _append_issue(
                    issues,
                    "sdist_license_missing",
                    f"{path} is missing LICENSE.",
                )
            if not _has_named_member(member_names, "NOTICE"):
                _append_issue(
                    issues,
                    "sdist_notice_missing",
                    f"{path} is missing NOTICE.",
                )

            metadata_member = next(
                (member for member in members if PurePosixPath(member.name).name == "PKG-INFO"),
                None,
            )
            if metadata_member is None:
                _append_issue(
                    issues,
                    "sdist_metadata_missing",
                    f"{path} is missing PKG-INFO.",
                )
                return

            extracted_member = sdist_file.extractfile(metadata_member)
            if extracted_member is None:
                _append_issue(
                    issues,
                    "sdist_metadata_missing",
                    f"{path} is missing readable PKG-INFO contents.",
                )
                return

            metadata_text = extracted_member.read().decode("utf-8")
    except (OSError, UnicodeDecodeError, tarfile.TarError) as exc:
        _append_issue(issues, "sdist_archive_invalid", f"Could not inspect {path}: {exc}")
        return

    _audit_metadata(
        metadata_text=metadata_text,
        expected_version=expected_version,
        expected_dependency=expected_dependency,
        artifact_label="sdist",
        artifact_path=path,
        issues=issues,
    )


def audit_built_release_artifacts(
    repo_root: str | Path,
    dist_dir: str | Path = "dist",
) -> BuiltArtifactAuditReport:
    """Audit the built wheel and sdist artifacts for the current repo version."""
    root = Path(repo_root).resolve()
    resolved_dist_dir = Path(dist_dir)
    if not resolved_dist_dir.is_absolute():
        resolved_dist_dir = root / resolved_dist_dir
    resolved_dist_dir = resolved_dist_dir.resolve()

    issues: list[BuiltArtifactIssue] = []
    expected_version = _load_repo_version(root, issues)
    expected_dependency = "ghidra-sleigh"

    wheel_paths: tuple[str, ...] = ()
    sdist_paths: tuple[str, ...] = ()
    if not resolved_dist_dir.is_dir():
        _append_issue(
            issues,
            "dist_dir_missing",
            f"Built artifact directory is missing: {resolved_dist_dir}",
        )
    else:
        wheels = tuple(sorted(resolved_dist_dir.glob("flatline-*.whl")))
        sdists = tuple(sorted(resolved_dist_dir.glob("flatline-*.tar.gz")))

        if not wheels:
            _append_issue(
                issues,
                "wheel_artifact_missing",
                f"No flatline wheel artifacts found in {resolved_dist_dir}",
            )
        if not sdists:
            _append_issue(
                issues,
                "sdist_artifact_missing",
                f"No flatline sdist artifacts found in {resolved_dist_dir}",
            )

        wheel_paths = tuple(str(path.resolve()) for path in wheels)
        sdist_paths = tuple(str(path.resolve()) for path in sdists)

        for wheel_path in wheels:
            _audit_wheel(
                wheel_path,
                expected_version=expected_version,
                expected_dependency=expected_dependency,
                issues=issues,
            )
        for sdist_path in sdists:
            _audit_sdist(
                sdist_path,
                expected_version=expected_version,
                expected_dependency=expected_dependency,
                issues=issues,
            )

    return BuiltArtifactAuditReport(
        expected_version=expected_version,
        expected_dependency=expected_dependency,
        required_artifact_kinds=REQUIRED_ARTIFACT_KINDS,
        wheel_artifacts=wheel_paths,
        sdist_artifacts=sdist_paths,
        issues=tuple(issues),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the built-artifact audit as a small release-time CLI."""
    parser = argparse.ArgumentParser(
        prog="python tools/artifacts.py",
        description="Audit built flatline wheel and sdist artifacts.",
    )
    parser.add_argument(
        "dist_dir",
        nargs="?",
        default="dist",
        help="Directory containing built artifacts (default: dist).",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used to derive the expected version (default: current directory).",
    )
    args = parser.parse_args(argv)

    report = audit_built_release_artifacts(args.repo_root, args.dist_dir)
    audited_dist_dir = Path(args.dist_dir)
    if not audited_dist_dir.is_absolute():
        audited_dist_dir = Path(args.repo_root) / audited_dist_dir
    audited_dist_dir = audited_dist_dir.resolve()

    if report.is_valid:
        print(f"Built artifact audit passed: {audited_dist_dir}")
        print(f"- Expected version: {report.expected_version}")
        print(f"- Expected dependency: {report.expected_dependency}")
        for wheel_path in report.wheel_artifacts:
            print(f"- Wheel: {wheel_path}")
        for sdist_path in report.sdist_artifacts:
            print(f"- Sdist: {sdist_path}")
        return 0

    print(f"Built artifact audit failed: {audited_dist_dir}")
    print(f"- Expected version: {report.expected_version}")
    print(f"- Expected dependency: {report.expected_dependency}")
    for issue in report.issues:
        print(f"- {issue.code}: {issue.message}")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
