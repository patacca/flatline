# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Native C++ decompiler bridge via nanobind (session lifecycle, target selection, decompile pipeline)
- End-to-end decompilation verified: x86_64 produces correct structured C output
- Ghidra decompiler library compilation and native startup/pair enumeration
- Runtime-data bridge enumeration with fallback for malformed `.ldefs`
- `ghidra-sleigh` package design for compiled Sleigh runtime data (ADR-010)
- `.sla` assets compiled for priority ISAs (DATA, x86, AARCH64, RISCV, MIPS)
- Meson build system with C++20, nanobind, debug/release/debugoptimized build types
- Python data models and `FlatlineError` error hierarchy
- Contract test harness with 28 passing tests (22 unit, 6 contract)
- Tox configuration for multi-version Python testing (py313, py314, lint)
- Code style guide enforcing ASCII-only source files via ruff
- ADR-009 decided: ISA variant scope (x86 32+64, ARM64, RISC-V 64, MIPS32)
- ADR-010 decided: separate `ghidra-sleigh` pip package for runtime data
- Initial public release notes documenting contract guarantees, support tiers,
  known-variant limits, and upgrade policy
- Initial public release workflow documentation and a release-readiness audit
  that keeps the `0.1.0` first-public-tag recommendation explicit

### Fixed
- Size-aware `std::string` construction for `nb::bytes` to preserve embedded null bytes
- Editable native rebuild nanobind paths
- Tolerance for malformed `.ldefs` during runtime-data enumeration

### Changed
- Renamed project from ghidralib to flatline repo-wide
- Repository agent instructions now live in `AGENTS.md`
