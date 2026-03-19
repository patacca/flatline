"""Unit tests for the release publish workflow."""

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


def test_u025_release_workflow_routes_manual_dispatches_to_testpypi() -> None:
    """U-025: Release automation publishes GitHub releases to PyPI and manual runs to TestPyPI."""
    workflow = _load_release_workflow()

    assert workflow["name"] == "Release"
    assert workflow["on"]["release"]["types"] == ["published"]
    assert "workflow_dispatch" in workflow["on"]

    build_job = _job(workflow, "build")
    assert build_job["runs-on"] == "ubuntu-latest"
    assert _uses_step(build_job, "actions/checkout@v4")["with"]["submodules"] == "recursive"
    assert _uses_step(build_job, "actions/setup-python@v5")["with"]["python-version"] == "3.14"
    assert _uses_step(build_job, "actions/setup-python@v5")["with"]["cache"] == "pip"
    assert "sudo apt-get install -y ninja-build zlib1g-dev" in _named_step(
        build_job, "Install system dependencies"
    )["run"]
    assert "pip install build twine" in _named_step(build_job, "Install build tooling")["run"]
    assert "python tools/compliance.py" in _named_step(build_job, "Run compliance audit")["run"]
    assert "python -m build --wheel --outdir dist" in _named_step(build_job, "Build wheel")["run"]
    assert "python -m build --sdist --outdir dist" in _named_step(build_job, "Build sdist")["run"]
    validate_run = _named_step(build_job, "Validate distribution artifacts")["run"]
    assert "twine check dist/*" in validate_run
    assert "python tools/artifacts.py dist --repo-root ." in validate_run
    upload_step = _uses_step(build_job, "actions/upload-artifact@v4")
    assert upload_step["with"]["name"] == "python-distributions"
    assert upload_step["with"]["if-no-files-found"] == "error"

    publish_job = _job(workflow, "publish")
    assert publish_job["needs"] == "build"
    assert publish_job["permissions"]["id-token"] == "write"
    assert publish_job["environment"]["name"] == (
        "${{ github.event_name == 'workflow_dispatch' && 'testpypi' || 'pypi' }}"
    )
    assert publish_job["environment"]["url"] == (
        "${{ github.event_name == 'workflow_dispatch' && "
        "'https://test.pypi.org/project/flatline/' || 'https://pypi.org/project/flatline/' }}"
    )
    download_step = _uses_step(publish_job, "actions/download-artifact@v4")
    assert download_step["with"]["name"] == "python-distributions"
    publish_step = _uses_step(publish_job, "pypa/gh-action-pypi-publish@release/v1")
    assert publish_step["with"]["repository-url"] == (
        "${{ github.event_name == 'workflow_dispatch' && "
        "'https://test.pypi.org/legacy/' || 'https://upload.pypi.org/legacy/' }}"
    )
    assert publish_step["with"]["skip-existing"] == (
        "${{ github.event_name == 'workflow_dispatch' }}"
    )
