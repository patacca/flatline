# Public Artifact Review Checklist

This checklist is the source-controlled human gate for the initial public
release. Run it after the deterministic release helpers have passed and before
creating `git tag v0.1.0`.

## Release Candidate Record

- Git commit under review:
- Flatline version under review: `0.1.0.dev0`
- Planned public tag: `0.1.0`
- Built artifact filenames:

## Preconditions

- The repo worktree is clean before building so Meson cannot omit local edits
  from the sdist.
- The documented readiness commands have all passed from the repo venv:
  - `python tools/release.py`
  - `tox`
  - `python tools/compliance.py`
  - `python tools/footprint.py`
  - `python -m build`
  - `python tools/artifacts.py dist`

## Review Evidence

- Confirm `python tools/release.py` still reports the expected `0.1.0`
  recommendation from the `0.1.0.dev0` branch state.
- Confirm `tox` passed on the release matrix and no release-facing docs drifted
  while fixing the branch for release.
- Confirm `python tools/compliance.py` passed and still reports the pinned
  `ghidra-sleigh == 12.0.4` dependency plus the expected native-source
  attribution references.
- Confirm `python tools/footprint.py` matches `docs/footprint.md`, or the
  footprint baseline was intentionally refreshed in the same review.
- Confirm `python -m build` produced exactly the current release artifacts that
  are under review.
- Confirm `python tools/artifacts.py dist` passed against the built wheel
  and sdist for the current version.
- Inspect the reviewed artifacts and verify `LICENSE` and `NOTICE` are shipped
  in both the wheel and the sdist.
- Review `CHANGELOG.md` and `docs/release_notes.md` for release-facing drift so
  the published support tiers, upgrade policy, and per-version delta remain
  aligned with the audited artifacts.

## Command Outcomes

- `python tools/release.py`:
- `tox`:
- `python tools/compliance.py`:
- `python tools/footprint.py`:
- `python -m build`:
- `python tools/artifacts.py dist`:

## Approval Record

- Reviewer:
- Date:
- Reviewed git commit:
- Reviewed artifact filenames:
- Outcome: approved | blocked | follow-up required
- Follow-up notes:
