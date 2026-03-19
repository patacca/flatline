"""Unit tests for the pinned CI workflow."""

from __future__ import annotations

from pathlib import Path

import yaml


def _load_ci_workflow() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[2]
    workflow_text = (repo_root / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    return yaml.load(workflow_text, Loader=yaml.BaseLoader)


def _job(workflow: dict[str, object], job_id: str) -> dict[str, object]:
    try:
        return workflow["jobs"][job_id]
    except KeyError as exc:
        raise AssertionError(f"missing CI job {job_id}") from exc


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


def test_u019_ci_workflow_enforces_runner_and_python_policy() -> None:
    """U-019: CI keeps the pinned Ubuntu matrix and latest-stable non-Ubuntu jobs."""
    workflow = _load_ci_workflow()
    assert workflow["name"] == "CI"

    lint_job = _job(workflow, "lint")
    assert lint_job["runs-on"] == "ubuntu-latest"
    assert _uses_step(lint_job, "actions/setup-python@v5")["with"]["python-version"] == "3.14"

    build_job = _job(workflow, "build")
    assert build_job["runs-on"] == "ubuntu-latest"
    assert _uses_step(build_job, "actions/setup-python@v5")["with"]["python-version"] == "3.14"

    test_job = _job(workflow, "test")
    assert test_job["runs-on"] == "ubuntu-24.04"
    assert test_job["strategy"]["matrix"]["include"] == [
        {"python-version": "3.13", "tox-env": "py313"},
        {"python-version": "3.14", "tox-env": "py314"},
    ]
    assert (
        _named_step(test_job, "Run non-regression tests")["run"].strip()
        == 'tox -e ${{ matrix.tox-env }} -- -m "not regression"'
    )

    regression_job = _job(workflow, "regression")
    assert regression_job["runs-on"] == "ubuntu-24.04"
    assert (
        _uses_step(regression_job, "actions/setup-python@v5")["with"]["python-version"]
        == "3.14"
    )
    assert _named_step(regression_job, "Run regression gates")["run"].strip() == (
        "tox -e py314 -- -m regression"
    )


def test_u026_ci_workflow_promotes_macos_native_contract_lane() -> None:
    """U-026: CI keeps a pinned macOS lane on the native non-regression matrix."""
    workflow = _load_ci_workflow()
    macos_job = _job(workflow, "macos-contract")

    assert macos_job["runs-on"] == "macos-15"
    assert _uses_step(macos_job, "actions/checkout@v4")["with"]["submodules"] == "recursive"
    assert _uses_step(macos_job, "actions/setup-python@v5")["with"]["python-version"] == "3.14"
    assert _named_step(macos_job, "Install system dependencies")["run"].strip() == (
        "brew install ninja zlib"
    )
    assert _named_step(macos_job, "Install tox")["run"].strip() == "pip install tox"
    run_step = _named_step(macos_job, "Run macOS non-regression contract matrix")["run"].strip()
    assert run_step == 'tox -e py314-native -- -m "not regression"'
    assert "CPPFLAGS" not in run_step
    assert "LDFLAGS" not in run_step
    assert "PKG_CONFIG_PATH" not in run_step
