"""Release-compliance audit helpers for packaging and redistribution."""

from __future__ import annotations

import argparse
import re
import subprocess
import tomllib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_ARTIFACTS = (
    "LICENSE",
    "THIRD_PARTY_NOTICES",
    "third_party/ghidra/LICENSE",
    "third_party/ghidra/NOTICE",
    "tests/fixtures/README.md",
)
PROJECT_LICENSE_SPDX = "GPL-3.0-or-later"
REQUIRED_LICENSE_FILES = ("LICENSE", "THIRD_PARTY_NOTICES")
REQUIRED_DEPENDENCIES = ("ghidra-sleigh", "networkx")

LICENSE_SCAN_ROOTS = ("src", "tests", "tools")
LICENSE_SCAN_GLOB = "*.py"
THIRD_PARTY_NOTICES_FILENAME = "THIRD_PARTY_NOTICES"
THIRD_PARTY_DIRNAME = "third_party"
# Captures the SPDX identifier value (e.g. "GPL-3.0-or-later") from a
# header-style line such as "# SPDX-License-Identifier: GPL-3.0-or-later".
# Anchored to comment-prefix characters so prose mentions in docstrings or
# help text are not picked up as false positives.
_SPDX_HEADER_RE = re.compile(r"(?m)^[\s#/*;-]*SPDX-License-Identifier:\s*([A-Za-z0-9.\-+]+)")


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
    if project_table.get("license") != PROJECT_LICENSE_SPDX:
        _append_issue(
            issues,
            "project_license_mismatch",
            f'pyproject.toml must declare `license = "{PROJECT_LICENSE_SPDX}"`.',
        )

    license_files = project_table.get("license-files")
    if not isinstance(license_files, list) or not set(REQUIRED_LICENSE_FILES).issubset(
        {str(item) for item in license_files}
    ):
        required_repr = ", ".join(f'"{name}"' for name in REQUIRED_LICENSE_FILES)
        _append_issue(
            issues,
            "pyproject_license_files_missing",
            f"pyproject.toml must declare `license-files = [{required_repr}]`.",
        )

    dependencies = project_table.get("dependencies")
    if not isinstance(dependencies, list):
        missing_dependencies = REQUIRED_DEPENDENCIES
    else:
        missing_dependencies = tuple(
            dependency
            for dependency in REQUIRED_DEPENDENCIES
            if not any(isinstance(dep, str) and dep.startswith(dependency) for dep in dependencies)
        )
    if missing_dependencies:
        _append_issue(
            issues,
            "dependency_missing",
            "pyproject.toml must declare these dependencies: "
            + ", ".join(f"`{dependency}`" for dependency in missing_dependencies)
            + ".",
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
        ("THIRD_PARTY_NOTICES", "notice_file_missing"),
        ("third_party/ghidra/LICENSE", "ghidra_license_missing"),
        ("third_party/ghidra/NOTICE", "ghidra_notice_missing"),
        ("tests/fixtures/README.md", "fixture_manifest_missing"),
    ):
        artifact_texts[relative_path] = _read_text(
            root / relative_path,
            missing_code=code,
            issues=issues,
        )

    notice_text = artifact_texts["THIRD_PARTY_NOTICES"]
    if notice_text is not None:
        # The aggregated THIRD_PARTY_NOTICES file inlines each upstream's full
        # license text; the audit ensures every required upstream section is
        # present (and not silently dropped during a future edit).
        _require_fragments(
            text=notice_text,
            fragments=(
                "Ghidra",
                "OGDF",
                "libavoid",
                "zlib",
                "nanobind",
            ),
            code="notice_missing_reference",
            label="THIRD_PARTY_NOTICES",
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
    if readme_text is not None and "THIRD_PARTY_NOTICES" not in readme_text:
        _append_issue(
            issues,
            "readme_notice_reference_missing",
            "README.md must reference THIRD_PARTY_NOTICES for redistribution guidance.",
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
    parser.add_argument(
        "--license",
        dest="license_spdx",
        metavar="SPDX",
        default=None,
        help=(
            "Run a license-only audit: assert every SPDX-tagged file under "
            "src/, tests/, tools/ matches SPDX, that pyproject.toml `license` "
            "matches SPDX, and that THIRD_PARTY_NOTICES references every "
            "directory under third_party/. Exits non-zero on first mismatch."
        ),
    )
    args = parser.parse_args(argv)

    audited_root = Path(args.repo_root).resolve()

    if args.license_spdx is not None:
        return _run_license_audit(audited_root, args.license_spdx)

    report = audit_release_compliance(args.repo_root)
    if report.is_compliant:
        print(f"Compliance audit passed: {audited_root}")
        return 0

    print(f"Compliance audit failed: {audited_root}")
    for issue in report.issues:
        print(f"- {issue.code}: {issue.message}")
    return 1


def _iter_spdx_tagged_files(repo_root: Path) -> Iterable[Path]:
    for relative_root in LICENSE_SCAN_ROOTS:
        scan_root = repo_root / relative_root
        if not scan_root.is_dir():
            continue
        for path in sorted(scan_root.rglob(LICENSE_SCAN_GLOB)):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if "SPDX-License-Identifier" in text:
                yield path


def audit_license_headers(repo_root: Path, expected_spdx: str) -> ComplianceIssue | None:
    """Return the first SPDX header mismatch, or ``None`` if all match."""
    for path in _iter_spdx_tagged_files(repo_root):
        match = _SPDX_HEADER_RE.search(path.read_text(encoding="utf-8"))
        if match is None:
            continue
        found = match.group(1).rstrip(",;")
        if found != expected_spdx:
            return ComplianceIssue(
                code="spdx_header_mismatch",
                message=(
                    f"SPDX header mismatch in {path.relative_to(repo_root)}: "
                    f"expected {expected_spdx!r}, found {found!r}."
                ),
            )
    return None


def audit_pyproject_license(repo_root: Path, expected_spdx: str) -> ComplianceIssue | None:
    """Return an issue if pyproject.toml's `license` field deviates from SPDX."""
    issues: list[ComplianceIssue] = []
    project_table = _load_pyproject(repo_root, issues)
    if issues:
        return issues[0]
    if project_table is None:
        return ComplianceIssue(
            code="pyproject_project_missing",
            message="pyproject.toml is missing the [project] table.",
        )
    declared = project_table.get("license")
    if declared != expected_spdx:
        return ComplianceIssue(
            code="pyproject_license_mismatch",
            message=(f"pyproject.toml `license` is {declared!r}, expected {expected_spdx!r}."),
        )
    return None


def _notices_mention_dir(notices_text: str, dir_name: str) -> bool:
    # A vendored directory like "libavoid_src" is acknowledged by the project's
    # canonical name "libavoid" in THIRD_PARTY_NOTICES; strip common vendoring
    # suffixes so the audit accepts either form.
    candidates = {dir_name}
    for suffix in ("_src", "-src"):
        if dir_name.endswith(suffix):
            candidates.add(dir_name[: -len(suffix)])
    haystack = notices_text.lower()
    return any(candidate.lower() in haystack for candidate in candidates)


def _tracked_third_party_dirs(repo_root: Path) -> list[str] | None:
    """Return git-tracked subdirs under ``third_party/``, or ``None`` if git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "ls-tree", "--name-only", "HEAD", f"{THIRD_PARTY_DIRNAME}/"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError, subprocess.CalledProcessError:
        return None
    names: list[str] = []
    prefix = f"{THIRD_PARTY_DIRNAME}/"
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith(prefix):
            continue
        name = line[len(prefix) :].rstrip("/")
        if "/" in name or not name:
            continue
        names.append(name)
    return sorted(names)


def audit_third_party_notices(repo_root: Path) -> ComplianceIssue | None:
    """Return an issue if any tracked ``third_party/`` subdir is unmentioned in notices."""
    notices_path = repo_root / THIRD_PARTY_NOTICES_FILENAME
    if not notices_path.is_file():
        return ComplianceIssue(
            code="third_party_notices_missing",
            message=f"{THIRD_PARTY_NOTICES_FILENAME} is missing at repo root.",
        )
    third_party_dir = repo_root / THIRD_PARTY_DIRNAME
    if not third_party_dir.is_dir():
        return None

    tracked = _tracked_third_party_dirs(repo_root)
    if tracked is None:
        candidates = sorted(entry.name for entry in third_party_dir.iterdir() if entry.is_dir())
    else:
        candidates = tracked

    notices_text = notices_path.read_text(encoding="utf-8")
    missing = [name for name in candidates if not _notices_mention_dir(notices_text, name)]
    if missing:
        return ComplianceIssue(
            code="third_party_notices_incomplete",
            message=(
                f"{THIRD_PARTY_NOTICES_FILENAME} is missing entries for: " + ", ".join(missing)
            ),
        )
    return None


def _run_license_audit(repo_root: Path, expected_spdx: str) -> int:
    checks = (
        audit_license_headers(repo_root, expected_spdx),
        audit_pyproject_license(repo_root, expected_spdx),
        audit_third_party_notices(repo_root),
    )
    for issue in checks:
        if issue is not None:
            print(f"License audit failed: {repo_root}")
            print(f"- {issue.code}: {issue.message}")
            return 1
    print(f"License audit passed: {repo_root} ({expected_spdx})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
