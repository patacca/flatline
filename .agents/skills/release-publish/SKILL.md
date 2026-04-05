---
name: release-publish
description: Run the production PyPI release workflow for flatline. Executes local readiness gates, pauses for human review of `docs/release_review.md`, then creates the tag/release and verifies CI completion. Use when the user says "release", "publish", "ship it", or wants to publish a new version to PyPI.
---

# Release Publish

Execute the **production PyPI release workflow** for the current repo version. Run deterministic readiness gates, stop for human approval, then tag, release, and verify CI.

**This skill covers the production publish path only (not TestPyPI rehearsal).**

## Read first

1. `docs/release_workflow.md` (operator runbook, release decision record)
2. `docs/release_review.md` (human approval checklist)
3. `docs/release_notes.md` (release contract, support tiers)
4. `CHANGELOG.md` (release history)
5. `AGENTS.md` (repo conventions, build commands)

## Rules

- Never modify dated release entries in `CHANGELOG.md`.
- Never commit review notes to the repo.
- Never create the tag or GitHub release before explicit human approval.
- Always work inside the Python venv (`source .venv/bin/activate`).
- If any readiness command fails, stop and report the failure before continuing.

## Workflow

### Phase 0 -- Local readiness gates

1. Activate the repo venv: `source .venv/bin/activate`
2. Confirm the worktree is clean: `git status --short` must produce no output.
3. Read the current version from `src/flatline/_version.py` and confirm it matches `pyproject.toml` and `meson.build`.
4. Run `python tools/release.py` -- must exit 0.
5. Run `tox` -- must exit 0.
6. Run `python tools/compliance.py` -- must exit 0.
7. Run `python tools/footprint.py` -- informational, always exits 0.
8. Review `CHANGELOG.md` for an empty `## [Unreleased]` section above the most recent dated entry.
9. Review `docs/release_notes.md`, `README.md`, and `NOTICE` for release-facing drift.
10. Build artifacts: `python -m build` -- must succeed.
11. Audit artifacts: `python tools/artifacts.py dist --repo-root . --require-pypi-metadata` -- must exit 0.

### Phase 1 -- Human approval gate

12. **STOP.** Present the operator with `docs/release_review.md` and ask them to review every checklist item against the readiness output from Phase 0.
13. Wait for the operator to explicitly approve the release. Do not proceed without a clear approval signal.

### Phase 2 -- Tag and release

14. Prompt the operator to update the **Release Decision** section in `docs/release_workflow.md` with the version being released and its rationale. Commit the update.
15. Create the release tag locally: `git tag v<version>`
16. **STOP.** Request explicit push approval from the operator with:

```
Ready to push tag v<version> to remote.

  git push origin v<version>

Please confirm you want to proceed with the push.
Reply with "push approved" or "confirm push" to continue, or "cancel" to abort.
```

17. After explicit approval, instruct the operator to execute the push manually:

```
Please run the following command:

  git push origin v<version>

Let me know when complete.
```

**Do NOT execute `git push` yourself.** The operator runs this command manually.

18. Create the GitHub release: `gh release create v<version> --generate-notes`

### Phase 3 -- CI verification

19. Wait for the `release.yml` workflow triggered by `release.published` to complete. Monitor with `gh run list --workflow=release.yml --limit=1`.
20. Verify all jobs passed: dev-checks, build-wheels (5 platforms), build-sdist, validate, publish, and smoke-published (10 matrix entries).
21. Report the final CI status to the operator. If any job failed, link to the failed run.

## Checks

- Every readiness command from Phase 0 exited successfully before reaching the human gate.
- The operator explicitly approved the release before any tag was created.
- The Release Decision section in `docs/release_workflow.md` was updated and committed.
- The GitHub release exists and the `release.yml` workflow completed with all jobs green.
- The published wheel set covers the Tier-1 matrix: manylinux x86_64/aarch64, Windows AMD64, macOS x86_64/arm64 for CPython 3.13 and 3.14.
