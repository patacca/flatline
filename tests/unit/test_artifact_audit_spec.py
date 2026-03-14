"""Unit tests for built release artifact auditing."""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

from flatline._artifacts import audit_built_release_artifacts
from flatline._compliance import expected_ghidra_sleigh_version


def _write_repo_version(repo_root: Path, version: str = "0.1.0.dev0") -> None:
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                f'version = "{version}"',
                "",
            ]
        ),
        encoding="ascii",
    )


def _write_wheel(
    dist_dir: Path,
    *,
    version: str = "0.1.0.dev0",
    dependency_version: str | None = None,
    include_license: bool = True,
    include_notice: bool = True,
) -> Path:
    if dependency_version is None:
        dependency_version = expected_ghidra_sleigh_version()

    wheel_path = dist_dir / f"flatline-{version}-py3-none-any.whl"
    dist_info_dir = f"flatline-{version}.dist-info"
    metadata = "\n".join(
        [
            "Metadata-Version: 2.4",
            "Name: flatline",
            f"Version: {version}",
            f"Requires-Dist: ghidra-sleigh == {dependency_version}",
            "",
        ]
    )

    with zipfile.ZipFile(wheel_path, mode="w") as wheel_file:
        wheel_file.writestr(f"{dist_info_dir}/METADATA", metadata)
        if include_license:
            wheel_file.writestr(f"{dist_info_dir}/licenses/LICENSE", "Apache-2.0\n")
        if include_notice:
            wheel_file.writestr(f"{dist_info_dir}/licenses/NOTICE", "flatline notice\n")

    return wheel_path


def _write_sdist(
    dist_dir: Path,
    *,
    version: str = "0.1.0.dev0",
    dependency_version: str | None = None,
    include_license: bool = True,
    include_notice: bool = True,
) -> Path:
    if dependency_version is None:
        dependency_version = expected_ghidra_sleigh_version()

    sdist_path = dist_dir / f"flatline-{version}.tar.gz"
    archive_root = f"flatline-{version}"
    metadata = "\n".join(
        [
            "Metadata-Version: 2.4",
            "Name: flatline",
            f"Version: {version}",
            f"Requires-Dist: ghidra-sleigh == {dependency_version}",
            "",
        ]
    )

    with tarfile.open(sdist_path, mode="w:gz") as sdist_file:
        _add_tar_text_file(sdist_file, f"{archive_root}/PKG-INFO", metadata)
        if include_license:
            _add_tar_text_file(sdist_file, f"{archive_root}/LICENSE", "Apache-2.0\n")
        if include_notice:
            _add_tar_text_file(sdist_file, f"{archive_root}/NOTICE", "flatline notice\n")

    return sdist_path


def _add_tar_text_file(archive: tarfile.TarFile, path: str, contents: str) -> None:
    data = contents.encode("ascii")
    info = tarfile.TarInfo(name=path)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


def test_u022_built_release_artifact_audit_accepts_expected_wheel_and_sdist(
    tmp_path: Path,
) -> None:
    """U-022: Built wheel and sdist audits pass when metadata and notices align."""
    repo_root = tmp_path / "repo"
    dist_dir = repo_root / "dist"
    dist_dir.mkdir(parents=True)
    _write_repo_version(repo_root)
    wheel_path = _write_wheel(dist_dir)
    sdist_path = _write_sdist(dist_dir)

    report = audit_built_release_artifacts(repo_root)

    assert report.is_valid
    assert report.expected_version == "0.1.0.dev0"
    assert report.expected_dependency_pin == "ghidra-sleigh == 12.0.4"
    assert report.required_artifact_kinds == ("wheel", "sdist")
    assert report.wheel_artifacts == (str(wheel_path.resolve()),)
    assert report.sdist_artifacts == (str(sdist_path.resolve()),)
    assert report.issues == ()


def test_u022_built_release_artifact_audit_rejects_notice_loss_and_metadata_drift(
    tmp_path: Path,
) -> None:
    """U-022: Missing notices and stale artifact metadata fail deterministically."""
    repo_root = tmp_path / "repo"
    dist_dir = repo_root / "dist"
    dist_dir.mkdir(parents=True)
    _write_repo_version(repo_root)
    _write_wheel(dist_dir, include_notice=False)
    _write_sdist(dist_dir, version="0.2.0.dev0", dependency_version="12.0.3")

    report = audit_built_release_artifacts(repo_root)

    assert not report.is_valid
    issue_codes = {issue.code for issue in report.issues}
    assert "wheel_notice_missing" in issue_codes
    assert "sdist_version_mismatch" in issue_codes
    assert "sdist_dependency_pin_missing" in issue_codes


def test_u022_built_release_artifact_audit_rejects_missing_dist_dir(
    tmp_path: Path,
) -> None:
    """U-022: Missing dist directory fails the artifact audit deterministically."""
    repo_root = tmp_path / "repo"
    _write_repo_version(repo_root)

    report = audit_built_release_artifacts(repo_root)

    assert not report.is_valid
    issue_codes = {issue.code for issue in report.issues}
    assert "dist_dir_missing" in issue_codes
