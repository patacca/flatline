# Fixture Strategy

## 1. Minimal Fixture Set

| Fixture ID | Type | Purpose | Notes |
| --- | --- | --- | --- |
| `fx_add_elf64` | ELF x86_64 | Baseline known-function happy path | Mirrors E3-style simple arithmetic function scenario |
| `fx_switch_elf64` | ELF x86_64 | Jump-table/switch CFG coverage | Mirrors E5-style switch recovery scenario |
| `fx_invalid_addr_case` | Logical case over `fx_add_elf64` | Invalid address negative behavior | Uses unmapped address input, not a separate binary |
| `fx_runtime_data_min` | Runtime data directory | Pair enumeration and startup validation | Contains curated language/compiler assets required for MVP |
| `fx_corrupt_bin` | Corrupt/truncated binary | Binary load failure negative behavior | Truncated header; not a valid loadable target |

Note: Fixture format (ELF binaries vs raw memory images) depends on ADR-001 scope resolution.
Current IDs assume binary-file fixtures; names and content may be adjusted once the input model is decided.

## 2. Expected-Output Strategy

Textual outputs:
- Compare normalized token/structure representation, not raw formatting.
- Ignore whitespace-only differences and non-contractual comments.

Diagnostics:
- Assert stable error/warning categories and codes.
- Treat message strings as informative but not exact-match unless explicitly marked stable.

Metadata:
- Enforce required keys and value types.
- Allow additive keys in minor releases.

## 3. Determinism Rules

- Freeze fixture binaries and runtime-data revision identifiers per release branch.
- Run regression suites under pinned upstream version only.
- Any fixture content change requires baseline regeneration in the same change set.

## 4. Fixture Update Process on Upstream Change

1. Create upstream bump branch and record new pin.
2. Re-run fixture generation pipeline and produce new revision ids.
3. Recompute normalized oracles and diff against prior baselines.
4. Label each delta:
- contract-preserving drift (accept with minor release notes), or
- contract-breaking drift (major release + migration notes).
5. Update `tests/fixtures/README.md` manifest and `tests/specs/test_catalog.md` references.
