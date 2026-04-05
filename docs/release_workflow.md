# Release Workflow

Operator procedure for `0.1.x` patch publishes, baselined on the `0.1.1`
release. The human approval checklist lives in `docs/release_review.md`;
per-run review notes stay outside the repo.

## Release Decision

- Published baseline version: `0.1.1`
- Release classification: `pre_1_0_patch_release`

Rationale:
- `0.1.0` already established the initial public SemVer baseline for flatline.
- Flatline remains on a public `0.1.x` pre-1.0 line while the contract and
  support matrix continue to settle.
- The current delta is backward-compatible: host-support expansion, Tier-1
  wheel publication, and opt-in enriched output extend the contract without
  breaking existing callers.
- The TestPyPI rehearsal exercised the same release line as `0.1.1.dev1`
  before the final GitHub release and PyPI publish of `0.1.1`.

## Readiness Check

```bash
source .venv/bin/activate
python tools/release.py
tox
python tools/compliance.py
python tools/footprint.py
```

## Release Steps

1. Activate the repo venv: `source .venv/bin/activate`
2. Confirm the worktree is clean with `git status --short` before building;
   Meson sdists omit uncommitted changes from the archive
3. Run `python tools/release.py`
4. Run `tox`
5. Run `python tools/compliance.py`
6. Run `python tools/footprint.py` as an informational footprint measurement
7. Keep `CHANGELOG.md` with an empty `## [Unreleased]` section above the most
   recent dated release entry
8. Review `docs/release_notes.md`, `README.md`, and `NOTICE` for any last
   release-facing drift
9. Confirm `pyproject.toml`, `meson.build`, and `src/flatline/_version.py`
   already agree on the current repo version
10. Build artifacts with `python -m build`
11. Audit the built sdist/wheel with
    `python tools/artifacts.py dist --repo-root . --require-pypi-metadata`
12. Run the manual checklist in `docs/release_review.md` and wait for explicit
    approval before proceeding. Do not commit review notes.
13. Create the release tag with `git tag v<current-version>`
14. Push the release tag with `git push origin v<current-version>`
15. Publish the GitHub release with `gh release create v<current-version> --generate-notes`
16. Wait for the `release.published` workflow to finish, then verify the PyPI
    publish and the post-publish smoke matrix.

## Hold Point

Do not create the release tag or publish the GitHub release until the review
checklist in `docs/release_review.md` is explicitly approved out-of-band.

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
  runs `python tools/artifacts.py dist --repo-root . --require-pypi-metadata`.
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
