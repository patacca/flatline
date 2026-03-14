"""Unit tests for initial public release notes and README alignment."""

from __future__ import annotations

from pathlib import Path


def test_u020_initial_public_release_notes_cover_p5_requirements() -> None:
    """U-020: Release-facing notes stay aligned with the P5 public-release gate."""
    repo_root = Path(__file__).resolve().parents[2]
    release_notes = (repo_root / "docs" / "release_notes.md").read_text(encoding="utf-8")
    readme = (repo_root / "README.md").read_text(encoding="utf-8")

    required_release_fragments = (
        "# Initial Public Release Notes",
        "## Contract Guarantees",
        "## Support Tiers",
        "## Known Variant Limits",
        "## Upgrade Policy",
        "Linux x86_64",
        "x86 (32/64), ARM64, RISC-V 64, and MIPS32",
        "best-effort",
        "Thumb",
        "microMIPS",
        "latest-upstream-only",
        "one minor release",
        "runtime_data_dir",
        "CHANGELOG.md",
    )

    for fragment in required_release_fragments:
        assert fragment in release_notes

    assert "docs/release_notes.md" in readme
    assert "P5 initial public release preparation" in readme
