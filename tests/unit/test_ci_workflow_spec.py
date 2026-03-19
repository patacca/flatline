"""Unit tests for CI workflow smoke invariants."""

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


def _job_runs(job: dict[str, object]) -> list[str]:
    return [step["run"] for step in job["steps"] if "run" in step]


def test_u019_ci_workflow_keeps_supported_test_matrix_and_regression_lane() -> None:
    """U-019: CI keeps the supported test matrix and a dedicated regression lane."""
    workflow = _load_ci_workflow()
    assert workflow["name"] == "CI"

    test_job = _job(workflow, "test")
    supported_matrix = {
        (entry["python-version"], entry["tox-env"])
        for entry in test_job["strategy"]["matrix"]["include"]
    }
    assert supported_matrix == {("3.13", "py313"), ("3.14", "py314")}
    assert any(
        'tox -e ${{ matrix.tox-env }} -- -m "not regression"' in run
        for run in _job_runs(test_job)
    )

    regression_job = _job(workflow, "regression")
    assert any(
        "tox -e py314 -- -m regression" in run for run in _job_runs(regression_job)
    )


def test_u026_ci_workflow_keeps_macos_native_contract_lane() -> None:
    """U-026: CI keeps a macOS lane on the native non-regression matrix."""
    workflow = _load_ci_workflow()
    macos_job = _job(workflow, "macos-contract")

    assert str(macos_job["runs-on"]).startswith("macos-")
    job_runs = "\n".join(_job_runs(macos_job))
    assert 'tox -e py314-native -- -m "not regression"' in job_runs
    assert "CPPFLAGS" not in job_runs
    assert "LDFLAGS" not in job_runs
    assert "PKG_CONFIG_PATH" not in job_runs


def test_u027_ci_workflow_keeps_windows_native_contract_lane() -> None:
    """U-027: CI keeps a Windows lane on the native non-regression matrix."""
    workflow = _load_ci_workflow()
    windows_job = _job(workflow, "windows-contract")

    assert str(windows_job["runs-on"]).startswith("windows-")
    job_runs = "\n".join(_job_runs(windows_job))
    assert 'tox -e py314-native -- -m "not regression"' in job_runs
    assert "CPPFLAGS" not in job_runs
    assert "LDFLAGS" not in job_runs
    assert "PKG_CONFIG_PATH" not in job_runs
