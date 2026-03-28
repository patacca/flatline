# Release Workflow

This document records the current repo-side procedure for promoting the active
`.devN` candidate to a public release. The source-controlled manual checklist
for the human gate lives in `docs/release_review.md`; any per-run review notes
stay outside the repo. Historical note: `0.1.0` already established the
initial public release baseline. The current production publish candidate is
`0.1.1.dev1`, and the next public version target is `0.1.1`.

## Release Decision

- Current release candidate: `0.1.1.dev1`
- Recommended public version: `0.1.1`
- Release decision: `pre_1_0_patch_release`

Rationale:
- `0.1.0` already established the initial public SemVer baseline for flatline.
- Flatline remains on a public `0.1.x` pre-1.0 line while the contract and
  support matrix continue to settle.
- The current delta is backward-compatible: host-support expansion, Tier-1
  wheel publication, and opt-in enriched output extend the contract without
  breaking existing callers.
- The public version for this publish therefore drops only the `.dev1` suffix
  from the audited release candidate.

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
current production publish gate. It checks the current version state, the
audited `0.1.1.dev1` to `0.1.1` recommendation, the presence of the required
release documents, and a clean git worktree so Meson cannot silently drop
uncommitted changes from the sdist. The release/diagnostic helpers live under
`tools/` and are repo-only; they are not part of the wheel or sdist payload.

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
   `## [Unreleased]` into a dated `## [0.1.1]` section
8. Review `docs/release_notes.md`, `README.md`, and `docs/compliance.md` for
   any last release-facing drift
9. Bump `pyproject.toml`, `meson.build`, and `src/flatline/_version.py` from
   `0.1.1.dev1` to `0.1.1`
10. Build artifacts with `python -m build`
11. Audit the built sdist/wheel with `python tools/artifacts.py dist`
    so the current version, dependency metadata, and shipped `LICENSE` / `NOTICE`
    files are verified from the actual release artifacts
12. Run the manual checklist in `docs/release_review.md`; keep reviewed
    commit/artifact notes outside the repo and wait for explicit approval.
    Do not commit review notes.
13. Create the release tag with `git tag v0.1.1`
14. Push the release tag with `git push origin v0.1.1`
15. Publish the GitHub release with `gh release create v0.1.1 --generate-notes`
16. Wait for the `release.published` workflow to finish, then verify the PyPI
    publish and the post-publish smoke matrix.

## Hold Point

Do not run `git tag v0.1.1` or publish GitHub release `v0.1.1` until the
public artifact review is explicitly approved. `python tools/artifacts.py dist`
provides deterministic artifact evidence for that review, and
`docs/release_review.md` records the checklist criteria used for the final
human sign-off. The operator reports approval out-of-band. Do not commit
review notes to this repo.

## GitHub Actions Release Automation

- `.github/workflows/release.yml` is the release publish pipeline.
- Publishing the GitHub release fires `release.published`, which builds the
  Tier-1 wheel set via `cibuildwheel`
  (manylinux `x86_64` / `aarch64`, Windows `AMD64`, and macOS `x86_64` / `arm64`
  for CPython 3.13 and 3.14) plus the sdist.
- The wheel jobs run `tools/flatline_dev/wheel_smoke.py` through
  `cibuildwheel`'s test hook, so the installed wheel must import,
  auto-discover `ghidra-sleigh` runtime data, and decompile `fx_add_elf64`
  before publish continues.
- A validation job merges the built artifacts, runs `twine check dist/*`, and
  runs `python tools/artifacts.py dist --repo-root .`.
- `workflow_dispatch` runs the same build, smoke, and validation flow, but
  publishes the full wheel set plus sdist to TestPyPI instead of PyPI.
  Manual TestPyPI dispatches must use a unique version because duplicate
  uploads now fail instead of being skipped.
- After publish, a runner matrix installs the exact tagged version back from
  TestPyPI or PyPI with `--only-binary=:all:` and runs
  `tools/flatline_dev/published_wheel_smoke.py` on every Tier-1
  platform/arch/Python combination so the published wheel path, transitive
  `ghidra-sleigh` dependency, and omitted-`runtime_data_dir` UX are all
  exercised from the package index rather than only from local build artifacts.
- The manual review gate in this document and `docs/release_review.md` still
  happens before creating and publishing the GitHub release that triggers the
  production publish.
