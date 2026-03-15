# Initial Public Release Workflow

This document records the remaining P5 release decision and the exact repo-side
workflow to execute once the public artifact review is approved. The source-
controlled checklist for that human gate lives in `docs/release_review.md`.

## SemVer Decision

- Current development version: `0.1.0.dev0`
- Recommended first public version: `0.1.0`
- SemVer classification: `initial_public_release`

Rationale:
- The repo already names the pending public line as `0.1.0.dev0` in
  `pyproject.toml`, `meson.build`, and `src/flatline/_version.py`.
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
12. Complete `docs/release_review.md` for the final human artifact review by
    recording the reviewed git commit, built artifact filenames, and the
    outcomes of the deterministic release commands
13. Create the release tag with `git tag v0.1.0`

## Hold Point

Do not run `git tag v0.1.0` until the public artifact review is explicitly
approved. `python tools/artifacts.py dist` provides deterministic artifact
evidence for that review, and `docs/release_review.md` records the checklist,
candidate metadata, and command outcomes used for the final human sign-off.
This workflow is only the source-controlled procedure that prepares the repo
for that final sign-off.
