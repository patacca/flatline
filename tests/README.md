# Test Plan

This `tests/` tree now mixes specification artifacts with executable pytest
coverage. Unit and contract suites remain pure Python; integration,
regression, and negative suites use committed native-memory fixtures and the
installed `ghidra_sleigh` runtime-data package when the native bridge is available.

## Layout

- `tests/specs/test_catalog.md`: canonical list of test definitions and oracle strategy.
- `tests/specs/fixtures.md`: minimal fixture set and update policy.
- `tests/unit/`: unit-level contract and adapter checks.
- `tests/contract/`: public API stability contract checks.
- `tests/integration/`: end-to-end native decompile checks against committed fixtures.
- `tests/regression/`: normalized output, jump-table, and latency guards.
- `tests/negative/`: structured rejection/error-path checks.
- `tests/fixtures/README.md`: fixture inventory, recipes, hashes, and provenance.

## Source Attribution

Test requirements derive from:
- `docs/specs.md`
- `docs/roadmap.md`
- `notes/api/decompiler_inventory.md`
- Consolidated baseline experiment findings captured in the spec and test catalog
