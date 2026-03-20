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
    assert all(action != "ilammy/msvc-dev-cmd@v1" for action in build_wheels_uses)
    cibuildwheel_step = _uses_step(build_wheels_job, "pypa/cibuildwheel")
    assert cibuildwheel_step["uses"] == "pypa/cibuildwheel@v3.4.0"
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

    # -- dev-checks: tox -e dev gates build jobs --
    dev_checks_job = _job(workflow, "dev-checks")
    dev_checks_runs = "\n".join(_job_runs(dev_checks_job))
    assert "tox -e dev" in dev_checks_runs
    assert "dev-checks" in build_wheels_job.get("needs", [])

    # -- build-sdist: sdist build --
    build_sdist_job = _job(workflow, "build-sdist")
    assert "dev-checks" in build_sdist_job.get("needs", [])
    sdist_runs = "\n".join(_job_runs(build_sdist_job))
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
    assert "skip-existing" not in publish_step["with"]
    cibuildwheel = pyproject["tool"]["cibuildwheel"]
    assert cibuildwheel["build"] == "cp313-* cp314-*"
    assert cibuildwheel["skip"] == "*-win32 *-win_arm64 *-musllinux_*"
    assert cibuildwheel["config-settings"] == {
        "setup-args": ["-Dnative_bridge=enabled", "--vsenv"]
    }
    assert cibuildwheel["test-command"] == "python {project}/tools/flatline_dev/wheel_smoke.py"
    assert cibuildwheel["linux"]["archs"] == "x86_64 aarch64"
    assert cibuildwheel["linux"]["manylinux-x86_64-image"] == "manylinux_2_28"
    assert cibuildwheel["linux"]["manylinux-aarch64-image"] == "manylinux_2_28"
    assert cibuildwheel["windows"]["archs"] == "AMD64"
    assert cibuildwheel["windows"]["before-build"] == "pip install delvewheel"
    assert (
        cibuildwheel["windows"]["repair-wheel-command"]
        == "delvewheel repair -w {dest_dir} {wheel}"
    )
    assert cibuildwheel["macos"]["archs"] == "x86_64 arm64"
    assert cibuildwheel["macos"]["environment"]["MACOSX_DEPLOYMENT_TARGET"] == "11.0"
    assert (repo_root / "tools" / "flatline_dev" / "wheel_smoke.py").is_file()

    # -- smoke-published: index-backed install smoke on each Tier-1 target --
    smoke_published_job = _job(workflow, "smoke-published")
    assert smoke_published_job["needs"] == "publish"
    smoke_matrix = {
        (entry["cibw-archs"], _runner_family(entry["os"]), entry["python-version"])
        for entry in smoke_published_job["strategy"]["matrix"]["include"]
    }
    assert smoke_matrix == {
        ("x86_64", "linux", "3.13"),
        ("x86_64", "linux", "3.14"),
        ("aarch64", "linux", "3.13"),
        ("aarch64", "linux", "3.14"),
        ("AMD64", "windows", "3.13"),
        ("AMD64", "windows", "3.14"),
        ("arm64", "macos", "3.13"),
        ("arm64", "macos", "3.14"),
        ("x86_64", "macos", "3.13"),
        ("x86_64", "macos", "3.14"),
    }
    _uses_step(smoke_published_job, "actions/setup-python")
    smoke_runs = "\n".join(_job_runs(smoke_published_job))
    assert "python tools/flatline_dev/published_wheel_smoke.py" in smoke_runs
    assert "--repository" in smoke_runs
    assert "workflow_dispatch" in smoke_runs
    assert (repo_root / "tools" / "flatline_dev" / "published_wheel_smoke.py").is_file()
