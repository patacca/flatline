"""Regenerate all layout golden JSON files from test fixtures.

Iterates over every fixture in tests._native_fixtures, runs flatline-xray
--layout-dump for each, and writes the resulting JSON to
 tests/fixtures/layout_golden/.

Usage:
    source .venv/bin/activate
    python tools/regenerate_layout_goldens.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"
GOLDEN_DIR = FIXTURE_DIR / "layout_golden"


def _import_fixtures() -> dict:
    # Ensure tests/ is on sys.path so the import works from repo root.
    tests_path = str(REPO_ROOT / "tests")
    if tests_path not in sys.path:
        sys.path.insert(0, tests_path)
    from _native_fixtures import _FIXTURES  # type: ignore[import-not-found]

    return _FIXTURES


def _run_layout_dump(
    *,
    hex_path: Path,
    function_address: int,
    base_address: int,
    language_id: str,
    compiler_spec: str | None,
    out_path: Path,
) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        "-m",
        "flatline.xray",
        "--layout-dump",
        str(hex_path),
        "--function",
        hex(function_address),
        "--base-address",
        hex(base_address),
        "--language-id",
        language_id,
        "--out",
        str(out_path),
    ]
    if compiler_spec is not None:
        cmd.extend(["--compiler-spec", compiler_spec])
    return subprocess.run(cmd, capture_output=True, text=True)


def main() -> int:
    fixtures = _import_fixtures()
    if not fixtures:
        print("No fixtures found.", file=sys.stderr)
        return 1

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    exit_code = 0
    for fixture_id, fixture in fixtures.items():
        hex_path = fixture.hex_path
        out_path = GOLDEN_DIR / f"{fixture_id}__0x{fixture.function_address:x}.json"

        print(f"Generating {out_path.name} ...", end=" ")

        result = _run_layout_dump(
            hex_path=hex_path,
            function_address=fixture.function_address,
            base_address=fixture.base_address,
            language_id=fixture.language_id,
            compiler_spec=fixture.compiler_spec,
            out_path=out_path,
        )

        if result.returncode != 0:
            print("FAILED")
            if result.stdout:
                print(result.stdout, file=sys.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            exit_code = 1
        else:
            print("OK")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
