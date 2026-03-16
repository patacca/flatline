"""Unit tests for the release publish workflow."""

from __future__ import annotations

import re
from pathlib import Path


def _job_block(workflow: str, job_id: str) -> str:
    pattern = rf"^  {re.escape(job_id)}:\n(?P<body>(?:(?:    .*|)\n?)*)"
    match = re.search(pattern, workflow, flags=re.MULTILINE)
    assert match is not None, f"missing release job {job_id}"
    return match.group("body")


def test_u025_release_workflow_routes_manual_dispatches_to_testpypi() -> None:
    """U-025: Release automation publishes GitHub releases to PyPI and manual runs to TestPyPI."""
    repo_root = Path(__file__).resolve().parents[2]
    workflow = (repo_root / ".github" / "workflows" / "release.yml").read_text(
        encoding="ascii"
    )

    assert "name: Release" in workflow
    assert "release:" in workflow
    assert "types: [published]" in workflow
    assert "workflow_dispatch:" in workflow

    build_job = _job_block(workflow, "build")
    assert "runs-on: ubuntu-latest" in build_job
    assert "submodules: recursive" in build_job
    assert 'python-version: "3.13"' in build_job
    assert "cache: pip" in build_job
    assert "sudo apt-get install -y ninja-build zlib1g-dev" in build_job
    assert "pip install build twine" in build_job
    assert "python tools/compliance.py" in build_job
    assert "python -m build --wheel --outdir dist" in build_job
    assert "python -m build --sdist --outdir dist" in build_job
    assert "twine check dist/*" in build_job
    assert "python tools/artifacts.py dist --repo-root ." in build_job
    assert "name: python-distributions" in build_job
    assert "if-no-files-found: error" in build_job

    publish_job = _job_block(workflow, "publish")
    assert "needs: build" in publish_job
    assert "id-token: write" in publish_job
    assert "github.event_name == 'workflow_dispatch' && 'testpypi' || 'pypi'" in publish_job
    assert (
        "github.event_name == 'workflow_dispatch' && "
        "'https://test.pypi.org/project/flatline/' || 'https://pypi.org/project/flatline/'"
    ) in publish_job
    assert "name: python-distributions" in publish_job
    assert "uses: pypa/gh-action-pypi-publish@release/v1" in publish_job
    assert (
        "github.event_name == 'workflow_dispatch' && "
        "'https://test.pypi.org/legacy/' || 'https://upload.pypi.org/legacy/'"
    ) in publish_job
    assert "skip-existing: ${{ github.event_name == 'workflow_dispatch' }}" in publish_job
