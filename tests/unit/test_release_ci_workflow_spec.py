"""Unit tests for release workflow smoke invariants."""

from __future__ import annotations

import tomllib
from pathlib import Path

import yaml


def _load_release_workflow() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[2]
    workflow_text = (repo_root / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )
    return yaml.load(workflow_text, Loader=yaml.BaseLoader)


def _job(workflow: dict[str, object], job_id: str) -> dict[str, object]:
    try:
        return workflow["jobs"][job_id]
    except KeyError as exc:
        raise AssertionError(f"missing release job {job_id}") from exc


def _uses_step(job: dict[str, object], action: str) -> dict[str, object]:
    for step in job["steps"]:
        if step.get("uses", "").startswith(action):
            return step
    raise AssertionError(f"missing step using {action}")


def _job_runs(job: dict[str, object]) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


def _job_uses(job: dict[str, object]) -> list[str]:
    return [step["uses"] for step in job["steps"] if "uses" in step]


def _runner_family(label: str) -> str:
    if label.startswith("ubuntu"):
        return "linux"
    if label.startswith("macos"):
        return "macos"
    if label.startswith("windows"):
        return "windows"
    return "other"


def test_u025_release_workflow_routes_manual_dispatches_to_testpypi() -> None:
    """U-025: Release automation keeps the build, audit, and publish-routing invariants."""
    repo_root = Path(__file__).resolve().parents[2]
    workflow = _load_release_workflow()
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))

    assert workflow["name"] == "Release"
    assert workflow["on"]["release"]["types"] == ["published"]
    assert "workflow_dispatch" in workflow["on"]

    # -- build-wheels: cibuildwheel-driven multi-platform builds --
    build_wheels_job = _job(workflow, "build-wheels")
    build_wheels_uses = _job_uses(build_wheels_job)
    assert any("cibuildwheel" in action for action in build_wheels_uses), (
        "build-wheels must use cibuildwheel"
    )
    _uses_step(build_wheels_job, "actions/upload-artifact")
    matrix_entries = {
        (entry["cibw-archs"], _runner_family(entry["os"]))
        for entry in build_wheels_job["strategy"]["matrix"]["include"]
    }
    assert matrix_entries == {
        ("x86_64", "linux"),
        ("aarch64", "linux"),
        ("AMD64", "windows"),
        ("arm64", "macos"),
        ("x86_64", "macos"),
    }

    # -- build-sdist: compliance audit + sdist build --
    build_sdist_job = _job(workflow, "build-sdist")
    sdist_runs = "\n".join(_job_runs(build_sdist_job))
    assert "python tools/compliance.py" in sdist_runs
    assert "python -m build --sdist" in sdist_runs

    # -- validate: twine + artifact audit on all built artifacts --
    validate_job = _job(workflow, "validate")
    validate_needs = validate_job["needs"]
    assert "build-wheels" in validate_needs
    assert "build-sdist" in validate_needs
    validate_runs = "\n".join(_job_runs(validate_job))
    assert "twine check dist/*" in validate_runs
    assert "python tools/artifacts.py dist --repo-root ." in validate_runs

    # -- publish: TestPyPI / PyPI routing --
    publish_job = _job(workflow, "publish")
    assert publish_job["needs"] == "validate"
    assert publish_job["permissions"]["id-token"] == "write"
    _uses_step(publish_job, "actions/download-artifact")
    publish_step = _uses_step(publish_job, "pypa/gh-action-pypi-publish")
    assert publish_step["with"]["repository-url"] == (
        "${{ github.event_name == 'workflow_dispatch' && "
        "'https://test.pypi.org/legacy/' || 'https://upload.pypi.org/legacy/' }}"
    )
    assert publish_step["with"]["skip-existing"] == (
        "${{ github.event_name == 'workflow_dispatch' }}"
    )
    cibuildwheel = pyproject["tool"]["cibuildwheel"]
    assert cibuildwheel["build"] == "cp313-* cp314-*"
    assert cibuildwheel["skip"] == "*-win32 *-win_arm64 *-musllinux_*"
    assert cibuildwheel["config-settings"] == {"setup-args": "-Dnative_bridge=enabled"}
    assert cibuildwheel["test-command"] == "python {project}/tools/flatline_dev/wheel_smoke.py"
    assert cibuildwheel["linux"]["archs"] == "x86_64 aarch64"
    assert cibuildwheel["linux"]["manylinux-x86_64-image"] == "manylinux_2_28"
    assert cibuildwheel["linux"]["manylinux-aarch64-image"] == "manylinux_2_28"
    assert cibuildwheel["windows"]["archs"] == "AMD64"
    assert cibuildwheel["macos"]["archs"] == "x86_64 arm64"
    assert cibuildwheel["macos"]["environment"]["MACOSX_DEPLOYMENT_TARGET"] == "11.0"
    assert (repo_root / "tools" / "flatline_dev" / "wheel_smoke.py").is_file()
