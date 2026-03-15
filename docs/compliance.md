# Compliance

## ADR-007 Decision

ADR-007 is resolved for flatline P3 packaging/compliance hardening.

Mandatory release-time checks for redistribution:

1. `python tools/compliance.py` must pass from the repo root.
2. Release artifacts must ship the root `LICENSE` and `NOTICE` files, with
   `pyproject.toml` declaring both through `license-files`.
3. `NOTICE` must record the pinned native-source baseline
   `Ghidra_12.0.4_build` / `e40ed13014025f82488b1f8f7bca566894ac376b`,
   plus the upstream attribution file locations
   `third_party/ghidra/LICENSE` and `third_party/ghidra/NOTICE`.
4. The default runtime dependency pin `ghidra-sleigh == 12.0.4` must remain
   explicit in both packaging metadata and the compliance docs so release
   review does not silently drift away from the pinned Ghidra baseline.
5. Fixture redistribution stays documented through
   `tests/fixtures/README.md`; release review must keep that synthetic-fixture
   note intact.

This decision resolves the redistribution-check process only. Default-install
footprint remains a separate P3 tracking item, now recorded through
`python tools/footprint.py` and `docs/footprint.md`.

## Artifact Manifest

| Artifact | Scope | Purpose |
| --- | --- | --- |
| `LICENSE` | Wheel, sdist, repo | Flatline's own Apache-2.0 license text |
| `NOTICE` | Wheel, sdist, repo | Flatline redistribution notice with pinned Ghidra attribution and dependency references |
| `docs/compliance.md` | Repo | ADR-007 decision record, manifest, and release checklist |
| `docs/footprint.md` | Repo | Default-install footprint baseline and explicit size-policy note |
| `third_party/ghidra/LICENSE` | Repo | Upstream Ghidra license text for the pinned native-source baseline |
| `third_party/ghidra/NOTICE` | Repo | Upstream Ghidra attribution notice for the pinned native-source baseline |
| `tests/fixtures/README.md` | Repo | Synthetic-fixture redistribution note and fixture manifest |
| `ghidra-sleigh == 12.0.4` | Separate dependency | Default runtime-data companion package; review it as a pinned dependency, not as a bundled flatline artifact |

## Release Checklist

1. Activate the repo venv: `source .venv/bin/activate`
2. Run the compliance audit: `python tools/compliance.py`
3. Verify the audit still reports the pinned Ghidra baseline
   `Ghidra_12.0.4_build` / `e40ed13014025f82488b1f8f7bca566894ac376b`
   and the dependency pin `ghidra-sleigh == 12.0.4`
4. Preserve the root `LICENSE` and `NOTICE` files in release artifacts
5. Preserve the `tests/fixtures/README.md` redistribution note
6. Refresh `docs/footprint.md` from an installed-wheel environment with
   `python tools/footprint.py`
7. Re-run `tox` before tagging a release
8. After `python -m build`, run `python tools/artifacts.py dist` so the
   built wheel and sdist are checked for the expected `LICENSE` / `NOTICE`
   files plus the current version and dependency metadata

## Notes

- `third_party/ghidra` remains a read-only submodule pinned to the upstream
  baseline above.
- The compliance audit is intentionally small and deterministic; it validates
  artifact presence and pinned references, not broader legal interpretation.
- The compliance, footprint, release, and artifact-audit helpers live under
  `tools/` as repo-only scripts and are intentionally absent from wheel and
  sdist artifacts.
