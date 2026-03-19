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
        if step.get("uses") == action:
            return step
    raise AssertionError(f"missing step using {action}")


def _named_step(job: dict[str, object], name: str) -> dict[str, object]:
    for step in job["steps"]:
        if step.get("name") == name:
            return step
    raise AssertionError(f"missing named step {name}")


def _job_runs(job: dict[str, object]) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


def test_u025_release_workflow_routes_manual_dispatches_to_testpypi() -> None:
    """U-025: Release automation keeps the build, audit, and publish-routing invariants."""
    workflow = _load_release_workflow()

    assert workflow["name"] == "Release"
    assert workflow["on"]["release"]["types"] == ["published"]
    assert "workflow_dispatch" in workflow["on"]

    build_job = _job(workflow, "build")
    build_runs = "\n".join(_job_runs(build_job))
    assert "python tools/compliance.py" in build_runs
    assert "python -m build --wheel --outdir dist" in build_runs
    assert "python -m build --sdist --outdir dist" in build_runs
    assert "twine check dist/*" in build_runs
    assert "python tools/artifacts.py dist --repo-root ." in build_runs
    _uses_step(build_job, "actions/upload-artifact@v4")

    publish_job = _job(workflow, "publish")
    assert publish_job["needs"] == "build"
    assert publish_job["permissions"]["id-token"] == "write"
    _uses_step(publish_job, "actions/download-artifact@v4")
    publish_step = _uses_step(publish_job, "pypa/gh-action-pypi-publish@release/v1")
    assert publish_step["with"]["repository-url"] == (
        "${{ github.event_name == 'workflow_dispatch' && "
        "'https://test.pypi.org/legacy/' || 'https://upload.pypi.org/legacy/' }}"
    )
    assert publish_step["with"]["skip-existing"] == (
        "${{ github.event_name == 'workflow_dispatch' }}"
    )
