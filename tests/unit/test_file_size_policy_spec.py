"""Unit tests for the repository file-size policy."""

from __future__ import annotations

from pathlib import Path
import subprocess

MAX_LINES_PER_FILE = 600
EXEMPT_PREFIXES = ("docs/archived/",)
EXEMPT_SUFFIXES = (".hex",)
TEXT_FILENAMES = {
    "AGENTS.md",
    "meson.build",
    "meson_options.txt",
    "mkdocs.yml",
    "pyproject.toml",
}
TEXT_SUFFIXES = {
    ".cpp",
    ".h",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
}


def test_tracked_text_files_respect_line_cap() -> None:
    """U-032: Tracked maintained text files stay within the 600-line cap."""
    repo_root = Path(__file__).resolve().parents[2]
    tracked_files = subprocess.check_output(
        ["git", "ls-files"],
        cwd=repo_root,
        text=True,
    ).splitlines()

    offenders: list[str] = []
    for relative_path in tracked_files:
        if relative_path.startswith(EXEMPT_PREFIXES):
            continue
        if relative_path.endswith(EXEMPT_SUFFIXES):
            continue

        path = Path(relative_path)
        if path.name not in TEXT_FILENAMES and path.suffix not in TEXT_SUFFIXES:
            continue

        line_count = sum(1 for _ in (repo_root / path).open("rb"))
        if line_count > MAX_LINES_PER_FILE:
            offenders.append(f"{relative_path}: {line_count}")

    assert offenders == []
