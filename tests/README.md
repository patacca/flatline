# Test Plan (Definitions Only)

This `tests/` tree contains specification artifacts and pytest skeletons only.
No file in this directory performs real native integration calls yet.

## Layout

- `tests/specs/test_catalog.md`: canonical list of test definitions and oracle strategy.
- `tests/specs/fixtures.md`: minimal fixture set and update policy.
- `tests/unit/`: unit-level contract and model checks (skeleton only).
- `tests/contract/`: public API stability contract checks (skeleton only).
- `tests/integration/`: end-to-end workflow checks (skeleton only, currently skipped).
- `tests/regression/`: pinned-output regression checks (skeleton only).
- `tests/negative/`: error-path and invalid-input checks (skeleton only).
- `tests/fixtures/README.md`: fixture inventory placeholder.

## Source Attribution

Test requirements derive from:
- `notes/api/decompiler_inventory.md`
- `notes/api/mvp_contract.md`
- `notes/experiments/E3_decompile_known_func.md`
- `notes/experiments/E4_invalid_address.md`
- `notes/experiments/E5_jump_table_switch.md`
