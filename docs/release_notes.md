# Initial Public Release Notes

These notes define the release-facing contract for the `0.1.x` release line.
They summarize what users can rely on, which targets are fixture-backed versus
best-effort, how published wheel availability maps to runtime support, and how
upgrades are handled as the project moves past the initial Linux MVP. This
document accompanies the initial `0.1.0` public release plus the subsequent
host-support and wheel-distribution updates on the same release line.

## Contract Guarantees

- The public Python API is the stable contract: `DecompilerSession`,
  `decompile_function()`, `list_language_compilers()`, the frozen result value
  types, and the six public error categories documented in `docs/specs.md`.
- Successful decompiles always return populated `function_info` and `c_code`.
  Error results always return `error` plus `function_info=None` and
  `c_code=None`.
- Invalid language/compiler pairs, invalid addresses, malformed setup, and
  invalid `analysis_budget` inputs are hard errors. Flatline does not silently
  fall back to a different language or compiler.
- Native failures are normalized into structured public results. No native
  exception is part of the supported user contract.
- The default runtime-data path comes from the `ghidra-sleigh` dependency.
  Callers may still pass an explicit `runtime_data_dir`, but that override is
  caller-managed. Any installed `ghidra-sleigh` version is accepted for default
  runtime data.
- Deterministic regression coverage is committed on Linux x86_64 for the
  fixture-backed confidence matrix: x86 (32/64), ARM64, RISC-V 64, and MIPS32.
- Release history and per-version deltas belong in `CHANGELOG.md`. The
  normative API and error-model rules remain in `docs/specs.md`.

## Support Tiers

| Surface | Tier | Notes |
| --- | --- | --- |
| Host platform | Supported | Linux x86_64, macOS arm64, and Windows x86_64 for the runtime contract in this release line |
| Wheel install availability | Published | `pip install flatline` publishes wheels for Linux x86_64, Linux aarch64, Windows x86_64, macOS x86_64, and macOS arm64, so those installs work without a local compiler |
| Target ISA variants | Fixture-backed | x86 (32/64), ARM64, RISC-V 64, and MIPS32 |
| Other bundled ISAs and variants | best-effort | Enumerated and loadable when runtime data ships them, but without dedicated fixture-backed output or perf guarantees |
| Custom runtime-data roots | Caller-managed | Explicit `runtime_data_dir` overrides stay supported, but compatibility is validated at runtime rather than guaranteed by the default release matrix |

Support-tier interpretation:
- `list_language_compilers()` may enumerate more pairs than the fixture-backed
  matrix. Enumeration means the runtime data contains loadable assets, not that
  flatline promises fixture-backed output quality for that pair.
- Wheel publication and supported-host status can differ. Wheel publication
  means the packaged install path and wheel smoke checks are green for that
  target, not that the host has reached equivalent contract coverage.
- macOS arm64 and Windows x86_64 now satisfy the equivalent-contract-coverage
  bar through dedicated native contract lanes plus published-wheel smoke.
- CI regression gates and warm-session budgets are source-controlled only for
  the fixture-backed matrix above.
- Linux aarch64 and macOS x86_64 remain installable through the published wheel
  matrix, but they are not yet promoted into the supported runtime-host tier
  because the repo does not keep dedicated equivalent-contract lanes for those
  targets.

## Known Variant Limits

- x86 32-bit and 64-bit targets are the only x86 variants with committed
  fixture-backed confidence in this release line.
- ARM64 (AArch64) is fixture-backed. ARM32, Thumb, and Thumb-2 remain
  best-effort because they do not yet have dedicated fixtures or regression
  budgets.
- RISC-V 64 is fixture-backed. RV32 and extension-heavy RISC-V profiles remain
  best-effort until they have dedicated fixtures and release-note coverage.
- MIPS32 is fixture-backed. MIPS64 and microMIPS remain best-effort.
- Additional language/compiler pairs that appear in runtime-data enumeration are
  still subject to upstream Sleigh/decompiler maturity; they are available, but
  not individually qualified beyond the default error contract.

## Upgrade Policy

- Flatline follows a latest-upstream-only policy: each flatline release line
  ships one vendored Ghidra decompiler revision. Any compatible `ghidra-sleigh`
  version provides the default runtime data.
- SemVer classification rules are:
  - `MAJOR`: breaking public Python API or contract changes.
  - `MINOR`: backward-compatible features, additive metadata/warnings, or an
    upstream bump that preserves the public contract.
  - `PATCH`: bug fixes and determinism/perf fixes with unchanged contract shape.
- Public API removals require at least one minor release of deprecation notice
  before removal, except for emergency security or compliance removals.
- Default installs should take flatline and `ghidra-sleigh` together.
  Custom `runtime_data_dir` roots are caller-managed and may
  need extra validation after upgrades.
- Before upgrading a deployed workflow, review `CHANGELOG.md`, check these
  release notes for support-tier changes, and rerun `tox` or equivalent
  fixture-backed validation for the targets you depend on.
