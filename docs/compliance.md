# Compliance

## ADR-007 Decision

ADR-007 is resolved for flatline P3 packaging/compliance hardening.

Mandatory release-time checks for redistribution:

1. `python tools/compliance.py` must pass from the repo root.
2. Release artifacts must ship the root `LICENSE` and `NOTICE` files, with
   `pyproject.toml` declaring both through `license-files`.
3. `NOTICE` must reference the upstream attribution file locations
   `third_party/ghidra/LICENSE` and `third_party/ghidra/NOTICE`.
4. The default runtime dependency `ghidra-sleigh` must be declared in
   packaging metadata.
5. Fixture redistribution stays documented through
   `tests/fixtures/README.md`; release review must keep that synthetic-fixture
   note intact.

Source provenance for the vendored decompiler is tracked by the
`third_party/ghidra` git submodule pointer; `python tools/compliance.py`
verifies the submodule is present and pinned.

This decision resolves the redistribution-check process only. Default-install
footprint remains a separate P3 tracking item, now recorded through
`python tools/footprint.py` and `docs/footprint.md`.

## Artifact Manifest

| Artifact | Scope | Purpose |
| --- | --- | --- |
| `LICENSE` | Wheel, sdist, repo | Flatline's own Apache-2.0 license text |
| `NOTICE` | Wheel, sdist, repo | Flatline redistribution notice with Ghidra decompiler attribution and dependency references |
| `docs/compliance.md` | Repo | ADR-007 decision record, manifest, and release checklist |
| `docs/footprint.md` | Repo | Default-install footprint baseline and explicit size-policy note |
| `third_party/ghidra/LICENSE` | Repo | Upstream Ghidra license text for the vendored decompiler source |
| `third_party/ghidra/NOTICE` | Repo | Upstream Ghidra attribution notice for the vendored decompiler source |
| `tests/fixtures/README.md` | Repo | Synthetic-fixture redistribution note and fixture manifest |
| `ghidra-sleigh` | Separate dependency | Default runtime-data companion package; review it as a declared dependency, not as a bundled flatline artifact |

## Release Checklist

1. Activate the repo venv: `source .venv/bin/activate`
2. Run the compliance audit: `python tools/compliance.py`
3. Verify the audit reports the `third_party/ghidra` submodule is present
   and the `ghidra-sleigh` dependency is declared
4. Preserve the root `LICENSE` and `NOTICE` files in release artifacts
5. Preserve the `tests/fixtures/README.md` redistribution note
6. Refresh `docs/footprint.md` from an installed-wheel environment with
   `python tools/footprint.py`
7. Re-run `tox` before tagging a release
8. After `python -m build`, run `python tools/artifacts.py dist` so the
   built wheel and sdist are checked for the expected `LICENSE` / `NOTICE`
   files plus the current version and dependency metadata

## Notes

- `third_party/ghidra` remains a read-only submodule; its pinned commit is
  the authoritative source-provenance record for the vendored decompiler.
- The compliance audit is intentionally small and deterministic; it validates
  artifact presence and dependency references, not broader legal interpretation.
- The compliance, footprint, release, and artifact-audit helpers live under
  `tools/` as repo-only scripts and are intentionally absent from wheel and
  sdist artifacts.
