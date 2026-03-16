# Initial Public Release Workflow

This document records the repo-side procedure that finalized flatline's initial
public release and the SemVer decision behind it. The source-controlled manual
checklist for the human gate lives in `docs/release_review.md`; any per-run
review notes stay outside the repo.

## SemVer Decision

- Current development version before release: `0.1.0.dev0`
- Released public version: `0.1.0`
- SemVer classification: `initial_public_release`

Rationale:
- Before the release bump, the repo named the pending public line as
  `0.1.0.dev0` in `pyproject.toml`, `meson.build`, and
  `src/flatline/_version.py`.
- No earlier public flatline release line exists, so this step establishes the
  initial public SemVer baseline instead of incrementing an existing release.
- Future release classification then follows the normal `MAJOR` / `MINOR` /
  `PATCH` rules documented in `docs/specs.md`, `docs/roadmap.md`, and
  `docs/release_notes.md`.

## Readiness Check

Activate the repo venv first, then verify the documented release state:

```bash
source .venv/bin/activate
python tools/release.py
tox
python tools/compliance.py
python tools/footprint.py
```

`python tools/release.py` is the source-controlled readiness audit for the
initial public release gate. It checks the current version state, the expected
`0.1.0` recommendation, the presence of the required release documents, and a
clean git worktree so Meson cannot silently drop uncommitted changes from the
sdist. The release/diagnostic helpers live under `tools/` and are repo-only;
they are not part of the wheel or sdist payload.

## Release Steps

1. Activate the repo venv: `source .venv/bin/activate`
2. Confirm the worktree is clean with `git status --short` before building;
   Meson sdists omit uncommitted changes from the archive
3. Run `python tools/release.py`
4. Run `tox`
5. Run `python tools/compliance.py`
6. Run `python tools/footprint.py` and refresh `docs/footprint.md` if the
   installed-wheel baseline changed
7. Update `CHANGELOG.md` by moving the release-ready entries from
   `## [Unreleased]` into a dated `## [0.1.0]` section
8. Review `docs/release_notes.md`, `README.md`, and `docs/compliance.md` for
   any last release-facing drift
9. Bump `pyproject.toml`, `meson.build`, and `src/flatline/_version.py` from
   `0.1.0.dev0` to `0.1.0`
10. Build artifacts with `python -m build`
11. Audit the built sdist/wheel with `python tools/artifacts.py dist`
    so the current version, dependency pin, and shipped `LICENSE` / `NOTICE`
    files are verified from the actual release artifacts
12. Run the manual checklist in `docs/release_review.md`; keep reviewed
    commit/artifact notes outside the repo and wait for explicit approval.
    Do not commit review notes.
13. Create the release tag with `git tag v0.1.0`

## Hold Point

Do not run `git tag v0.1.0` until the public artifact review is explicitly
approved. `python tools/artifacts.py dist` provides deterministic artifact
evidence for that review, and `docs/release_review.md` records the checklist
criteria used for the final human sign-off. The operator reports approval
out-of-band. Do not commit review notes to this repo.

## GitHub Actions Release Automation

- `.github/workflows/release.yml` is the release publish pipeline.
- `release.published` builds the wheel and sdist, validates them with
  `twine check dist/*` plus `python tools/artifacts.py dist --repo-root .`,
  then trusted-publishes to PyPI.
- `workflow_dispatch` runs the same build and validation flow, but publishes to
  TestPyPI instead of PyPI.
- The manual review gate in this document and `docs/release_review.md` still
  happens before creating the tag/release that triggers the production publish.
