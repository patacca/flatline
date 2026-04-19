"""Build script for xray layout benchmark corpus.

Parses gcc-flags from C source headers, compiles ELF binaries,
and produces sidecar meta.json files.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def _parse_gcc_flags(first_line: str) -> list[str]:
    """Parse gcc-flags from first line comment.

    Expected format: /* gcc-flags: -O1 -fno-stack-protector ... */
    """
    match = re.search(r"gcc-flags:\s*(.+?)\s*\*/", first_line)
    if not match:
        raise ValueError(f"No gcc-flags found in header: {first_line!r}")
    return match.group(1).split()


def _run_nm(elf_path: Path) -> str:
    """Run nm on ELF and return target_func address."""
    result = subprocess.run(
        ["nm", str(elf_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "T" and parts[2] == "target_func":
            return parts[0]
    raise RuntimeError(f"target_func not found in {elf_path}")


def _build_source(
    source_path: Path,
    out_dir: Path,
    *,
    force: bool = False,
) -> tuple[Path, Path, bool]:
    """Build a single source file into ELF + meta.json.

    Returns:
        Tuple of (elf_path, meta_path, was_built)
    """
    name = source_path.stem
    out_elf = out_dir / f"{name}.elf"
    out_meta = out_dir / f"{name}.meta.json"

    # Idempotency: skip if binary is up to date
    if not force and out_elf.exists():
        if out_elf.stat().st_mtime >= source_path.stat().st_mtime:
            return out_elf, out_meta, False

    # Parse gcc-flags from first line
    first_line = source_path.read_text(encoding="ascii").splitlines()[0]
    gcc_flags = _parse_gcc_flags(first_line)

    # Build gcc command line
    gcc_cmdline = ["gcc"] + gcc_flags + [str(source_path), "-o", str(out_elf)]

    # Compile
    result = subprocess.run(
        gcc_cmdline,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"Error: compilation failed for {source_path.name}",
            file=sys.stderr,
        )
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        sys.exit(1)

    # Extract target_func address from symbol table
    target_addr = _run_nm(out_elf)

    # Write meta.json
    meta = {
        "target_func_addr": target_addr,
        "base_address": "0x0",
        "language_id": "x86:LE:64:default",
        "compiler_spec": "gcc",
        "source_path": str(source_path.resolve()),
        "gcc_cmdline": gcc_cmdline,
    }
    out_meta.write_text(
        json.dumps(meta, indent=2) + "\n",
        encoding="ascii",
    )

    return out_elf, out_meta, True


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build xray layout benchmark corpus",
    )
    parser.add_argument(
        "--source",
        metavar="NAME",
        help="Build specific source file (e.g., 'tiny_branch')",
    )
    args = parser.parse_args(argv)

    # All paths relative to this script's parent directory
    corpus_dir = Path(__file__).parent
    sources_dir = corpus_dir / "sources"
    out_dir = corpus_dir.parent / "out" / "binaries"

    # Ensure output directory exists
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine which sources to build
    if args.source:
        source_path = sources_dir / f"{args.source}.c"
        if not source_path.exists():
            print(
                f"Error: source file not found: {source_path}",
                file=sys.stderr,
            )
            return 1
        sources = [source_path]
    else:
        sources = sorted(sources_dir.glob("*.c"))
        if not sources:
            print("Error: no source files found", file=sys.stderr)
            return 1

    # Build each source
    for source_path in sources:
        elf_path, meta_path, was_built = _build_source(source_path, out_dir)
        status = "Built" if was_built else "Skipped"
        print(f"{status}: {elf_path.name} + {meta_path.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
