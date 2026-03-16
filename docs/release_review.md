# Public Artifact Review Checklist

This checklist is the source-controlled human gate for the initial public
release of `0.1.0`. Run it after the deterministic release helpers have passed
and before creating `git tag v0.1.0`. Keep per-run review notes, reviewed
commit hashes, and artifact filenames outside the repo; the checklist stays
source-controlled, but the results do not.

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
  recommendation for the initial public release workflow.
- Confirm `tox` passed on the release matrix and no release-facing docs drifted
  while fixing the branch for release.
- Confirm `python tools/compliance.py` passed and still reports the
  `ghidra-sleigh` dependency plus the expected native-source attribution
  references.
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

## Approval Signal

- Do not create `git tag v0.1.0` until every checklist item passes.
- Keep any manual review notes outside the repo; do not commit them to
  `docs/release_review.md`.
- Proceed only after the reviewer explicitly approves the release.
