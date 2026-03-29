# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `DecompileRequest.enriched` and `DecompileResult.enriched` as the public
  opt-in enriched-output contract
- `Enriched.pcode` and `Pcode.get_pcode_op()`, `Pcode.get_varnode()`, and
  `Pcode.to_graph()` for deterministic ID lookup and graph projection over the
  exported raw pcode / varnode payload

### Changed
- The enriched-output contract now keeps pcode under its own future-proof
  layer and exposes a caller-owned `networkx.MultiDiGraph` projection instead
  of helper-specific data-flow traversal APIs
- Release compliance, built-artifact auditing, and footprint measurement now
  account for the `networkx` runtime dependency alongside `ghidra-sleigh`
- Redistribution/compliance policy now lives in `NOTICE`, ADR-007, and the
  release docs instead of a dedicated compliance manifest page
- Roadmap, spec, and release-state docs now record that `0.1.1` was published
  on PyPI and that P7 is closed in the repo

### Removed
- `docs/compliance.md`, which duplicated ADR-007, `NOTICE`, and the release
  checklists without being part of the shipped artifact contract

## [0.1.1] - 2026-03-28

### Added
- Opt-in enriched output via `DecompileRequest.include_enriched_output` and
  `DecompileResult.enriched_output`, exposing post-simplification pcode ops and
  varnode use-def graphs as frozen value types

### Changed
- `VersionInfo` now exposes `decompiler_version` (Ghidra engine version) instead
  of `upstream_tag` and `upstream_commit`
- `ghidra-sleigh` dependency is no longer pinned to an exact version
- Compliance attribution references the vendored decompiler source via the
  `third_party/ghidra` git submodule instead of hardcoded tag/commit constants
- `metadata["decompiler_version"]` in `DecompileResult` now always reflects the
  Ghidra decompiler engine version, not the flatline package version
- Manual TestPyPI release dispatches now require a unique package version
  instead of silently skipping duplicate uploads
- The supported runtime-host contract now includes macOS arm64 and Windows
  x86_64; Linux aarch64 and macOS x86_64 remain published-wheel-only targets
  pending dedicated equivalent-contract lanes
- The Tier-1 wheel matrix is now validated end to end on TestPyPI ahead of the
  first production PyPI publish
- Release readiness tooling and docs now audit the staged `0.1.1` production
  publish path after collapsing the prior `0.1.1.dev1` TestPyPI candidate, and
  they keep the GitHub-release trigger to PyPI explicit
- The public `0.1.x` release-line policy now explicitly allows
  backward-compatible support expansion and opt-in capabilities to ship as
  documented patch releases while flatline remains pre-1.0

### Removed
- `UPSTREAM_TAG` and `UPSTREAM_COMMIT` constants from `flatline._version`
- Runtime pin-drift warning when `ghidra-sleigh` version differs from a
  hardcoded baseline

## [0.1.0] - 2026-03-15

### Added
- Native C++ decompiler bridge via nanobind (session lifecycle, target selection,
  decompile pipeline)
- End-to-end decompilation verified: x86_64 produces correct structured C output
- Ghidra decompiler library compilation and native startup/pair enumeration
- Runtime-data bridge enumeration with fallback for malformed `.ldefs`
- `ghidra-sleigh` package design for compiled Sleigh runtime data (ADR-010)
- `.sla` assets compiled for priority ISAs (DATA, x86, AARCH64, RISCV, MIPS)
- Meson build system with C++20, nanobind, debug/release/debugoptimized build types
- Python data models and `FlatlineError` error hierarchy
- `AnalysisBudget` frozen value type with per-request `max_instructions` default
  of 100,000 instructions (ADR-005)
- Structured `WarningItem` / `ErrorItem` diagnostics with full filesystem paths
  for debuggability (ADR-006)
- `configuration_error` category for user-fixable install, startup, and
  runtime-data failures (ADR-011)
- Compliance process: `LICENSE` + `NOTICE` shipped in wheels/sdists, vendored
  source attribution kept explicit, and `python tools/compliance.py` audit
  (ADR-007)
- Auto-discovery of `ghidra-sleigh` runtime data when `runtime_data_dir` is omitted,
  with a runtime warning on upstream pin drift (ADR-004)
- Default-install footprint measurement via `python tools/footprint.py` with
  baseline recorded in `docs/footprint.md`
- Built artifact audit for wheel/sdist validation via `python tools/artifacts.py`
- Committed native memory fixtures for x86_64, x86_32, AArch64, RISC-V 64, and
  MIPS32 under `tests/fixtures/*.hex`
- Fixture source snippets and regeneration script under `tests/fixtures/sources/`
- Warm-session p95 regression budgets across priority-ISA add fixtures and
  the switch fixture
- Switch-site regression baseline asserting recovered site `0x1009` and 9 targets
- GitHub Actions CI with lint/build on `ubuntu-latest`, test/regression lanes
  pinned to `ubuntu-24.04`, and Python 3.13/3.14 matrix
- Tox configuration for multi-version Python testing (py313, py314, dev, lint)
- Code style guide enforcing ASCII-only source files via ruff
- ADR-009 decided: ISA variant scope (x86 32+64, ARM64, RISC-V 64, MIPS32)
- ADR-010 decided: separate `ghidra-sleigh` pip package for runtime data
- Initial public release notes documenting contract guarantees, support tiers,
  known-variant limits, and upgrade policy
- Public artifact review checklist documenting the final human sign-off gate
  for the initial public release
- Initial public release workflow documentation and a release-readiness audit
  that keeps the `0.1.0` first-public-tag recommendation explicit

### Changed
- Renamed project from ghidralib to flatline repo-wide
- Repository agent instructions now live in `AGENTS.md` / `CLAUDE.md`
- Upstream pin bumped to `Ghidra_12.0.4_build` (`e40ed13014`)
- `third_party/ghidra` tracked as a git submodule instead of a plain checkout
- Tox `py313`/`py314` envs now build and test installed wheel artifacts
  instead of the source tree
- Dev-only release helpers moved from `src/flatline` to `tools/flatline_dev/`,
  excluded from wheel and sdist distribution artifacts
- Version strings normalized to PEP 440 form `0.1.0.dev0`
- Initial public release workflow now keeps the manual artifact checklist
  source-controlled while the review notes stay outside the repo

### Fixed
- Size-aware `std::string` construction for `nb::bytes` to preserve embedded
  null bytes
- Editable native rebuild nanobind paths
- Tolerance for malformed `.ldefs` during runtime-data enumeration
- Dist script reference guarded for sdist-to-wheel builds
