"""Unit tests for the pinned CI regression workflow."""

from __future__ import annotations

import re
from pathlib import Path


def _job_block(workflow: str, job_id: str) -> str:
    pattern = rf"^  {re.escape(job_id)}:\n(?P<body>(?:(?:    .*|)\n?)*)"
    match = re.search(pattern, workflow, flags=re.MULTILINE)
    assert match is not None, f"missing CI job {job_id}"
    return match.group("body")


def test_u019_ci_workflow_enforces_pinned_regression_gates() -> None:
    """U-019: CI pins the regression lane and runs committed budgets explicitly."""
    repo_root = Path(__file__).resolve().parents[2]
    workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="ascii")

    # Perf-sensitive jobs pin the runner; lint/build may float.
    test_job = _job_block(workflow, "test")
    assert "runs-on: ubuntu-24.04" in test_job
    assert "submodules: recursive" in test_job
    assert 'python-version: "3.13"' in test_job
    assert "tox-env: py313" in test_job
    assert 'python-version: "3.14"' in test_job
    assert "tox-env: py314" in test_job
    assert 'tox -e ${{ matrix.tox-env }} -- -m "not regression"' in test_job

    regression_job = _job_block(workflow, "regression")
    assert "runs-on: ubuntu-24.04" in regression_job
    assert "submodules: recursive" in regression_job
    assert 'python-version: "3.14"' in regression_job
    assert "tox -e py314 -- -m regression" in regression_job
