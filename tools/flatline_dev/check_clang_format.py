"""Check clang-format compliance for maintained native bridge sources."""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_NATIVE_SOURCE_DIR = _REPO_ROOT / "src" / "flatline" / "native"
_CHECKED_SUFFIXES = (".cpp", ".h")


def _native_source_paths() -> list[Path]:
    return sorted(
        path
        for path in _NATIVE_SOURCE_DIR.iterdir()
        if path.is_file() and path.suffix in _CHECKED_SUFFIXES
    )


def main() -> int:
    """Run clang-format in check mode for all maintained native source files."""
    checked_paths = _native_source_paths()
    if not checked_paths:
        raise RuntimeError(f"No native source files found under {_NATIVE_SOURCE_DIR}")

    command = [
        "clang-format",
        "--dry-run",
        "-Werror",
        *(str(path.relative_to(_REPO_ROOT)) for path in checked_paths),
    ]
    completed = subprocess.run(command, cwd=_REPO_ROOT, check=False)
    return completed.returncode


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
