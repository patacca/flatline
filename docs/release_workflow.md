# Initial Public Release Workflow

This document records the remaining P5 release decision and the exact repo-side
workflow to execute once the public artifact review is approved.

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
python -m flatline._release
tox
python -m flatline._compliance
python -m flatline._footprint
```

`python -m flatline._release` is the source-controlled readiness audit for the
initial public release gate. It checks the current version state, the expected
`0.1.0` recommendation, and the presence of the required release documents.

## Release Steps

1. Activate the repo venv: `source .venv/bin/activate`
2. Run `python -m flatline._release`
3. Run `tox`
4. Run `python -m flatline._compliance`
5. Run `python -m flatline._footprint` and refresh `docs/footprint.md` if the
   installed-wheel baseline changed
6. Update `CHANGELOG.md` by moving the release-ready entries from
   `## [Unreleased]` into a dated `## [0.1.0]` section
7. Review `docs/release_notes.md`, `README.md`, and `docs/compliance.md` for
   any last release-facing drift
8. Bump `pyproject.toml`, `meson.build`, and `src/flatline/_version.py` from
   `0.1.0.dev0` to `0.1.0`
9. Build artifacts with `python -m build`
10. Inspect the built sdist/wheel for the expected license and notice files
11. Create the release tag with `git tag v0.1.0`

## Hold Point

Do not run `git tag v0.1.0` until the public artifact review is explicitly
approved. The review remains the human gate; this workflow is only the
source-controlled procedure that prepares the repo for that final sign-off.
