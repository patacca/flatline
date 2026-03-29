"""Unit tests for release workflow smoke invariants."""

from __future__ import annotations

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


def _matrix_platform_families(job: dict[str, object]) -> set[str]:
    return {_runner_family(entry["os"]) for entry in job["strategy"]["matrix"]["include"]}


def test_u025_release_workflow_routes_manual_dispatches_to_testpypi() -> None:
    """U-025: Release automation keeps the build, audit, and publish-routing invariants."""
    workflow = _load_release_workflow()

    assert workflow["on"]["release"]["types"] == ["published"]
    assert "workflow_dispatch" in workflow["on"]

    # -- build-wheels: cibuildwheel-driven multi-platform builds --
    build_wheels_job = _job(workflow, "build-wheels")
    build_wheels_uses = _job_uses(build_wheels_job)
    assert any("cibuildwheel" in action for action in build_wheels_uses), (
        "build-wheels must use cibuildwheel"
    )
    assert not any("ilammy/msvc-dev-cmd" in action for action in build_wheels_uses)
    _uses_step(build_wheels_job, "actions/upload-artifact")
    assert _matrix_platform_families(build_wheels_job) == {"linux", "windows", "macos"}

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

    # -- smoke-published: index-backed install smoke on each Tier-1 target --
    smoke_published_job = _job(workflow, "smoke-published")
    assert smoke_published_job["needs"] == "publish"
    assert _matrix_platform_families(smoke_published_job) == {"linux", "windows", "macos"}
    smoke_runs = "\n".join(_job_runs(smoke_published_job))
    assert "python tools/flatline_dev/published_wheel_smoke.py" in smoke_runs
    assert "--repository" in smoke_runs
    assert "workflow_dispatch" in smoke_runs
