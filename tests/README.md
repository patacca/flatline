# Test Plan

This `tests/` tree now mixes specification artifacts with executable pytest
coverage. Unit and contract suites remain pure Python; integration,
regression, and negative suites use committed native-memory fixtures and the
installed `ghidra_sleigh` runtime-data package when the native bridge is available.
Tox test envs install the built `flatline[test]` package, so native suites
exercise the installed artifact instead of `PYTHONPATH=src`.

## Running the suite

- `source .venv/bin/activate && tox`: all configured test and lint envs (including dev-only).
- `source .venv/bin/activate && tox -e py313,py314`: tests only (against installed wheel; dev-only tests skip).
- `source .venv/bin/activate && tox -e dev`: dev-only tests (compliance, footprint, release workflow, artifact audit).
- `source .venv/bin/activate && tox -e py313,py314 -- -m requires_native`: native-only coverage against the installed wheel artifact.
- `source .venv/bin/activate && tox -e lint`: Ruff only.

### Dev-only tests

Four test files exercise dev-only modules (`_compliance`, `_footprint`, `_release`, `_artifacts`)
that are excluded from wheel and sdist artifacts. The `dev` tox env runs them against the source
tree via `PYTHONPATH=src` (no wheel build). Under `py313`/`py314` these tests skip gracefully
because `pytest.importorskip` cannot find the modules in the installed wheel.

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
